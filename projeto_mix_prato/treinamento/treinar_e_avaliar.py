import csv, io, json, os, re, time, warnings
from pathlib import Path
from urllib.request import urlopen
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
import pandas as pd
from PIL import Image
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.dummy import DummyRegressor, DummyClassifier
from sklearn.metrics import mean_absolute_error, f1_score, precision_score, recall_score, accuracy_score, confusion_matrix
import joblib

BASE = "https://storage.googleapis.com/nutrition5k_dataset/nutrition5k_dataset/"
ROOT = Path('/content/nutrition5k') if Path('/content').exists() else Path.cwd() / 'nutrition5k'
RAW, IMAGES, OUT = ROOT/'raw', ROOT/'images', ROOT/'resultados'
for folder in [RAW, IMAGES, OUT]: folder.mkdir(parents=True, exist_ok=True)
SEED = 42
# Execute com amostras pequenas para CPU. Aumente caso tenha tempo e internet.
N_TREINO_POS = 150
N_TREINO_NEG = 150
N_TESTE = 100
N_WORKERS = 12
CHICKEN = {'chicken','chicken thighs','chicken breast','grilled chicken','roast chicken'}
print('Arquivos:', ROOT.resolve())
print('Grupos exatos de frango:', sorted(CHICKEN))


def baixar(url, destino):
    if destino.exists() and destino.stat().st_size > 100:
        return destino
    for tentativa in range(3):
        try:
            with urlopen(url, timeout=45) as r:
                data = r.read()
            destino.parent.mkdir(parents=True, exist_ok=True)
            tmp = destino.with_name(destino.name + '.tmp')
            tmp.write_bytes(data)
            tmp.replace(destino)
            return destino
        except Exception as exc:
            if tentativa == 2:
                raise RuntimeError(f'Não foi possível baixar {url}: {exc}') from exc
            time.sleep(1 + tentativa)

paths = ['metadata/dish_metadata_cafe1.csv','metadata/dish_metadata_cafe2.csv',
         'dish_ids/splits/depth_train_ids.txt','dish_ids/splits/depth_test_ids.txt']
for path in paths:
    out = RAW / path.split('/')[-1]
    baixar(BASE + path, out)
    print('Disponível:', out.name, '| bytes:', out.stat().st_size)

def extrair_registros(path):
    result = []
    with path.open(encoding='utf-8', newline='') as f:
        for row in csv.reader(f):
            # Formato verificado: 6 campos fixos seguidos de blocos de 7.
            try:
                dish_id, total_mass = row[0], float(row[2])
                if total_mass <= 0 or not dish_id.startswith('dish_'): continue
                meat = 0.0
                names = []
                for i in range(6, len(row)-6, 7):
                    name = row[i+1].strip().lower()
                    grams = float(row[i+2])
                    names.append(name)
                    if name in CHICKEN: meat += grams
                # Ignore misturas com frango no nome que não estão na lista exata.
                if any('chicken' in x and x not in CHICKEN for x in names): continue
                if meat > total_mass * 1.01: continue
                result.append({'dish_id':dish_id,'massa_total_g':total_mass,
                               'frango_real_g':meat,'frango_presente':int(meat>0),
                               'ingredientes':', '.join(names)})
            except (ValueError, IndexError): continue
    return result

records = extrair_registros(RAW/'dish_metadata_cafe1.csv') + extrair_registros(RAW/'dish_metadata_cafe2.csv')
df = pd.DataFrame(records).drop_duplicates('dish_id').set_index('dish_id')
train_ids = set((RAW/'depth_train_ids.txt').read_text().splitlines())
test_ids = set((RAW/'depth_test_ids.txt').read_text().splitlines())
assert train_ids.isdisjoint(test_ids), 'Divisões oficiais se sobrepõem; abortando.'
print('Pratos com metadados:', len(df), '| IDs oficiais de treino:',len(train_ids),'| teste:',len(test_ids))


# Amostragem: treino com proporção equilibrada de frango/não frango, teste aleatório
# na proporção natural. Isso ajuda a aprender com poucos exemplos, mas a distribuição
# de treino fica artificial; probabilidades e médias não devem ser usadas como prevalência real.
rng = np.random.default_rng(SEED)
train_df = df.loc[df.index.intersection(train_ids)].sort_index()
test_df = df.loc[df.index.intersection(test_ids)].sort_index()
def pick(index, n):
    index = list(index)
    return list(rng.choice(index, min(n,len(index)), replace=False))
train_selected = pick(train_df[train_df.frango_presente==1].index, N_TREINO_POS) + pick(train_df[train_df.frango_presente==0].index, N_TREINO_NEG)
test_selected = pick(test_df.index, N_TESTE)
print('Solicitados treino:',len(train_selected),'teste:',len(test_selected))
print('No treino: positivos',sum(df.loc[train_selected].frango_presente),'negativos',len(train_selected)-sum(df.loc[train_selected].frango_presente))
print('No teste natural: positivos',sum(df.loc[test_selected].frango_presente),'negativos',len(test_selected)-sum(df.loc[test_selected].frango_presente))

def image_file(dish_id): return IMAGES/(dish_id+'.png')
def obtain(dish_id):
    try:
        file = image_file(dish_id)
        baixar(BASE+'imagery/realsense_overhead/'+dish_id+'/rgb.png',file)
        with Image.open(file) as im: im.verify()
        return dish_id, None
    except Exception as exc: return dish_id, str(exc)

all_ids = train_selected + test_selected
failed = []
with ThreadPoolExecutor(max_workers=N_WORKERS) as pool:
    futures = [pool.submit(obtain,dish_id) for dish_id in all_ids]
    for number, future in enumerate(as_completed(futures),1):
        dish_id, error = future.result()
        if error: failed.append((dish_id,error))
        if number%50==0 or number==len(all_ids): print(f'Imagens verificadas: {number}/{len(all_ids)}; falhas: {len(failed)}')
if failed: print('Exemplos de falhas:',failed[:3])
failed_ids = {x[0] for x in failed}
train_selected = [x for x in train_selected if x not in failed_ids]
test_selected = [x for x in test_selected if x not in failed_ids]
if len(train_selected)<30 or len(test_selected)<10:
    raise RuntimeError('Imagens insuficientes; verifique o acesso à internet e execute novamente.')


# Uma miniatura de 16x16 e histogramas de cor são uma representação simples da foto;
# não são um detector nem segmentação. A massa total vem da balança.
def features(id):
    with Image.open(image_file(id)) as im:
        im = im.convert('RGB')
        mini = np.asarray(im.resize((16,16)), dtype=np.float32).reshape(-1)/255
        pix = np.asarray(im.resize((64,64)), dtype=np.uint8)
        hist = np.concatenate([np.histogram(pix[:,:,j],bins=16,range=(0,256),density=True)[0] for j in range(3)]).astype('float32')
    return np.concatenate([mini, hist, [df.loc[id,'massa_total_g']/1000]])
X_train = np.stack([features(x) for x in train_selected])
X_test  = np.stack([features(x) for x in test_selected])
y_train_g = df.loc[train_selected,'frango_real_g'].to_numpy()
y_test_g  = df.loc[test_selected,'frango_real_g'].to_numpy()
m_train = df.loc[train_selected,'massa_total_g'].to_numpy()
m_test = df.loc[test_selected,'massa_total_g'].to_numpy()
y_train_presence = (y_train_g>0).astype(int)
y_test_presence = (y_test_g>0).astype(int)
if len(np.unique(y_train_presence))<2:
    raise RuntimeError('Amostra de treino contém apenas uma classe; aumente a amostra.')
print('Características:',X_train.shape[1], '| treino:',len(X_train),'| teste:',len(X_test))


# Dois modelos separados: presença (classificação) e fração (regressão).
# A fração estimada multiplicada pelo peso total vira gramas estimadas de frango.
classifier = RandomForestClassifier(n_estimators=120, min_samples_leaf=2, max_features='sqrt', class_weight='balanced', n_jobs=-1, random_state=SEED)
regressor = RandomForestRegressor(n_estimators=120, min_samples_leaf=3, max_features=0.5, n_jobs=-1, random_state=SEED)
classifier.fit(X_train, y_train_presence)
regressor.fit(X_train, y_train_g/m_train)
pred_presence = classifier.predict(X_test)
pred_fraction = np.clip(regressor.predict(X_test),0,1)
pred_grams = pred_fraction*m_test
# Baselines: classe mais frequente do treino e fração média no treino.
base_class = DummyClassifier(strategy='most_frequent').fit(X_train,y_train_presence).predict(X_test)
base_frac = DummyRegressor(strategy='mean').fit(X_train,y_train_g/m_train).predict(X_test)
base_g = base_frac*m_test
base_zero = np.zeros_like(y_test_g)

metrics = {'treino':len(X_train),'teste':len(X_test),'positivos_treino':int(y_train_presence.sum()),'positivos_teste':int(y_test_presence.sum()),
           'modelo_acuracia':float(accuracy_score(y_test_presence,pred_presence)),
           'modelo_precisao_frango':float(precision_score(y_test_presence,pred_presence,zero_division=0)),
           'modelo_recall_frango':float(recall_score(y_test_presence,pred_presence,zero_division=0)),
           'modelo_f1_frango':float(f1_score(y_test_presence,pred_presence,zero_division=0)),
           'baseline_acuracia':float(accuracy_score(y_test_presence,base_class)),
           'mae_modelo_g':float(mean_absolute_error(y_test_g,pred_grams)),
           'mae_media_treino_g':float(mean_absolute_error(y_test_g,base_g)),
           'mae_sempre_zero_g':float(mean_absolute_error(y_test_g,base_zero)),
           'mae_modelo_fracao_percentual_pontos':float(mean_absolute_error(y_test_g/m_test,pred_fraction)*100)}
if y_test_presence.sum():
    metrics['mae_modelo_entre_pratos_com_frango_g'] = float(mean_absolute_error(y_test_g[y_test_presence==1],pred_grams[y_test_presence==1]))
    metrics['mae_zero_entre_pratos_com_frango_g'] = float(mean_absolute_error(y_test_g[y_test_presence==1],base_zero[y_test_presence==1]))
print('Indicadores — teste oficial separado (valores menores de MAE são melhores):')
for k,v in metrics.items(): print(f'{k}: {v:.3f}' if isinstance(v,float) else f'{k}: {v}')
print('Matriz de confusão: linhas real 0/1; colunas previsão 0/1')
print(confusion_matrix(y_test_presence,pred_presence,labels=[0,1]))
print('Aviso: métricas refletem este subconjunto de teste, não uma performance garantida no restaurante.')


results = df.loc[test_selected,['massa_total_g','frango_real_g','frango_presente','ingredientes']].copy()
results['previsao_frango_presente'] = pred_presence
results['probabilidade_frango_modelo'] = classifier.predict_proba(X_test)[:,list(classifier.classes_).index(1)]
results['frango_previsto_g'] = pred_grams
results['fracao_real'] = y_test_g/m_test
results['fracao_prevista'] = pred_fraction
results['erro_absoluto_g'] = np.abs(pred_grams-y_test_g)
results.to_csv(OUT/'previsoes_teste.csv', encoding='utf-8-sig')
(OUT/'metricas.json').write_text(json.dumps(metrics,indent=2,ensure_ascii=False),encoding='utf-8')
joblib.dump({'classificador':classifier,'regressor':regressor,'categorias_exatas':sorted(CHICKEN),'features':'16x16 RGB + histogramas RGB + massa total/1000'},OUT/'modelo_frango.joblib')
print('Arquivos exportados para:',OUT)
print(results[['massa_total_g','frango_real_g','frango_previsto_g','frango_presente','previsao_frango_presente']].head(10).round(1).to_string())


# Mostra pratos de teste que o modelo não viu, inclusive acertos e erros.
show = results.sample(min(6,len(results)),random_state=SEED)
fig, axes = plt.subplots(2,3,figsize=(12,8))
for ax, (id,row) in zip(axes.flat,show.iterrows()):
    with Image.open(image_file(id)) as im: ax.imshow(im.convert('RGB'))
    ax.set_title(f"Real: {row.frango_real_g:.0f} g | Massa estimada: {row.frango_previsto_g:.0f} g\nFrango: real {'sim' if row.frango_presente else 'não'} / previsão {'sim' if row.previsao_frango_presente else 'não'} ({row.probabilidade_frango_modelo:.0%})",fontsize=8)
    ax.axis('off')
for ax in axes.flat[len(show):]: ax.axis('off')
fig.suptitle('Teste: classificação e massa usam modelos independentes; podem divergir',fontsize=12)
fig.tight_layout()
fig.savefig(OUT/'exemplos_teste.png',dpi=150,bbox_inches='tight')
plt.show()


# Opcional, após executar as células anteriores: predição de foto nova.
# No Colab, rode: from google.colab import files; enviados = files.upload()
# Depois chame: analisar_foto(next(iter(enviados)), 600)  # 600 = peso líquido real em gramas
# Em seu computador, use o caminho de uma foto: analisar_foto('/caminho/foto.jpg', 600)
def analisar_foto(caminho, massa_total_g):
    massa_total_g = float(massa_total_g)
    if massa_total_g <= 0:
        raise ValueError('A massa líquida de alimento deve ser positiva.')
    with Image.open(caminho) as im:
        im = im.convert('RGB')
        mini = np.asarray(im.resize((16,16)), dtype=np.float32).reshape(-1)/255
        pix = np.asarray(im.resize((64,64)),dtype=np.uint8)
        hist = np.concatenate([np.histogram(pix[:,:,j], bins=16,range=(0,256),density=True)[0] for j in range(3)]).astype('float32')
    X = np.concatenate([mini,hist,[massa_total_g/1000]])[None,:]
    presence = bool(classifier.predict(X)[0])
    probability = float(classifier.predict_proba(X)[0, list(classifier.classes_).index(1)])
    fraction = float(np.clip(regressor.predict(X)[0],0,1))
    print(f"Classificação estimada de presença: {'sim' if presence else 'não'} (pontuação {probability:.1%})")
    print(f'Massa estimada de frango: {fraction*massa_total_g:.1f} g; proporção {100*fraction:.1f}%')
    print('Classificação de presença e estimativa de massa são modelos diferentes e podem divergir. A pontuação não é probabilidade calibrada. Não é uma medição. Teste com pratos do Bovinu’S antes de qualquer uso real.')
    plt.imshow(im); plt.axis('off'); plt.show()
