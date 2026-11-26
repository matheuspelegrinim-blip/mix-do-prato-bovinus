const examples = [{"id": "dish_1560444931", "foto": "examples/dish_1560444931.png", "massa_total_g": 200.0, "frango_real_g": 0.0, "presenca": false, "massa_estimada_g": 23.036506777652136, "fracao": 0.11518253388826068}, {"id": "dish_1561405389", "foto": "examples/dish_1561405389.png", "massa_total_g": 223.0, "frango_real_g": 101.810661, "presenca": true, "massa_estimada_g": 42.8067444839271, "fracao": 0.19195849544361926}, {"id": "dish_1561574428", "foto": "examples/dish_1561574428.png", "massa_total_g": 172.0, "frango_real_g": 0.0, "presenca": true, "massa_estimada_g": 48.631070513613, "fracao": 0.28273878205588954}, {"id": "dish_1565638550", "foto": "examples/dish_1565638550.png", "massa_total_g": 215.0, "frango_real_g": 41.06776, "presenca": true, "massa_estimada_g": 46.589160307272, "fracao": 0.21669376887103256}];
const $ = id => document.getElementById(id);
let selected = null, selectedFile = null;
const fmt = n => new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 }).format(n);
function showPreview(src) {
  $('preview').src = src; $('preview').hidden = false; $('image-tag').hidden = false; $('empty').hidden = true;
  $('results').hidden = true; $('placeholder').hidden = false; $('error').textContent = '';
}
function selectSample(s, button) {
  selected = s; selectedFile = null; $('photo').value = ''; $('mass').value = s.massa_total_g; $('mass').readOnly = true;
  document.querySelectorAll('.sample').forEach(x => x.classList.remove('active'));
  button.classList.add('active'); showPreview(s.foto);
}
examples.forEach((s, i) => {
  const b = document.createElement('button'); b.className = 'sample'; b.type = 'button'; b.setAttribute('aria-label', `Selecionar exemplo ${i + 1}`);
  const img = document.createElement('img'); img.src = s.foto; img.alt = `Foto do prato de teste ${i + 1}`; b.appendChild(img);
  b.addEventListener('click', () => selectSample(s,b)); $('samples').appendChild(b);
});
$('photo').addEventListener('change', event => {
  const file = event.target.files[0]; if (!file) return;
  if (!['image/jpeg','image/png'].includes(file.type) || file.size > 6*1024*1024) { $('error').textContent = 'Selecione uma imagem JPG ou PNG de até 6 MB.'; event.target.value = ''; return; }
  selected = null; selectedFile = file; $('mass').readOnly = false; $('mass').value = '';
  document.querySelectorAll('.sample').forEach(x => x.classList.remove('active'));
  const reader = new FileReader();
  reader.onload = () => showPreview(reader.result);
  reader.onerror = () => { $('error').textContent = 'Não foi possível ler a foto.'; };
  reader.readAsDataURL(file);
});
$('mass').addEventListener('input', () => { $('results').hidden = true; $('placeholder').hidden = false; $('error').textContent = ''; });
$('analyze').addEventListener('click', async () => {
  $('error').textContent = '';
  const mass = Number($('mass').value);
  if (!selected && !selectedFile) { $('error').textContent = 'Selecione um prato ou envie uma foto para começar.'; return; }
  if (!Number.isFinite(mass) || mass <= 0 || mass > 10000) { $('error').textContent = 'Informe o peso da comida entre 0 e 10.000 g.'; return; }
  $('analyze').disabled = true; $('analyze').textContent = 'Analisando…';
  try {
    if (!selected && typeof window.analyzeImage !== 'function') throw new Error('A análise de fotos enviadas está indisponível. Use um dos exemplos.');
    const data = selected || await window.analyzeImage(selectedFile, mass);
    $('estimate').textContent = fmt(data.massa_estimada_g);
    $('presence').textContent = data.presenca ? 'Indica presença' : 'Não indica presença';
    $('proportion').textContent = `${fmt(data.fracao * 100)}% do peso`;
    if (selected) { $('reference').textContent = `Referência real: ${fmt(selected.frango_real_g)} g`; $('reference').hidden = false; }
    else $('reference').hidden = true;
    $('placeholder').hidden = true; $('results').hidden = false;
  } catch (err) { $('error').textContent = err.message || 'Erro ao analisar a imagem.'; }
  finally { $('analyze').disabled = false; $('analyze').innerHTML = 'Analisar prato <span>✦</span>'; }
});
