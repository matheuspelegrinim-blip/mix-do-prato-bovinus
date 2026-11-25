"""Protótipo local de análise de pratos. Executar: python app.py."""
import base64
import csv
import io
import json
import math
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import joblib
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

ROOT = Path(__file__).resolve().parent
MODEL = joblib.load(ROOT / 'model' / 'modelo_frango.joblib')
EXAMPLE_IDS = ('dish_1561405389', 'dish_1565638550', 'dish_1561574428', 'dish_1560444931')
MAX_BYTES = 9 * 1024 * 1024

def features(image, mass):
    image = ImageOps.exif_transpose(image).convert('RGB')
    small = np.asarray(image.resize((16, 16)), dtype=np.float32).reshape(-1) / 255
    pixels = np.asarray(image.resize((64, 64)), dtype=np.uint8)
    hist = np.concatenate([np.histogram(pixels[:, :, j], bins=16, range=(0, 256), density=True)[0] for j in range(3)]).astype('float32')
    return np.concatenate([small, hist, [mass / 1000]])[None, :]

def predict(image, mass):
    if not math.isfinite(mass) or mass <= 0 or mass > 10000:
        raise ValueError('Informe o peso da comida entre 0 e 10.000 g.')
    x = features(image, mass)
    classif = MODEL['classificador']
    regression = MODEL['regressor']
    presence = bool(classif.predict(x)[0])
    score = float(classif.predict_proba(x)[0, list(classif.classes_).index(1)])
    fraction = float(np.clip(regression.predict(x)[0], 0, 1))
    return {'presenca': presence, 'pontuacao': score, 'massa_estimada_g': fraction * mass, 'fracao': fraction}

def samples():
    with (ROOT / 'data' / 'previsoes_teste.csv').open(encoding='utf-8-sig', newline='') as handle:
        by_id = {row['dish_id']: row for row in csv.DictReader(handle)}
    result = []
    for dish_id in EXAMPLE_IDS:
        row = by_id[dish_id]
        result.append({'id': dish_id, 'foto': f'/examples/{dish_id}.png', 'massa_total_g': float(row['massa_total_g']),
                       'frango_real_g': float(row['frango_real_g']), 'ingredientes': row['ingredientes']})
    return result

class Handler(BaseHTTPRequestHandler):
    def reply(self, code, body, ctype='text/plain; charset=utf-8'):
        self.send_response(code); self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body))); self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff'); self.end_headers(); self.wfile.write(body)

    def json_reply(self, code, payload):
        self.reply(code, json.dumps(payload, ensure_ascii=False).encode('utf-8'), 'application/json; charset=utf-8')

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/api/samples': return self.json_reply(200, samples())
        static = {'/': ('assets/index.html', 'text/html; charset=utf-8'), '/assets/style.css': ('assets/style.css', 'text/css; charset=utf-8'),
                  '/assets/main.js': ('assets/main.js', 'text/javascript; charset=utf-8')}
        if path in static:
            file, kind = static[path]
            return self.reply(200, (ROOT / file).read_bytes(), kind)
        if path.startswith('/examples/'):
            name = path.removeprefix('/examples/')
            if name in {f'{x}.png' for x in EXAMPLE_IDS}:
                return self.reply(200, (ROOT / 'examples' / name).read_bytes(), 'image/png')
        self.json_reply(404, {'erro': 'Não encontrado.'})

    def do_POST(self):
        if urlparse(self.path).path != '/api/predict': return self.json_reply(404, {'erro': 'Não encontrado.'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if length <= 0 or length > MAX_BYTES: raise ValueError('A imagem deve ter no máximo 6 MB.')
            data = json.loads(self.rfile.read(length))
            mass = float(data.get('massa_total_g', 0))
            if 'sample_id' in data:
                dish_id = data['sample_id']
                if dish_id not in EXAMPLE_IDS: raise ValueError('Exemplo inválido.')
                raw = (ROOT / 'examples' / f'{dish_id}.png').read_bytes()
            else:
                raw = base64.b64decode(data.get('foto_base64', ''), validate=True)
                if len(raw) > 6 * 1024 * 1024: raise ValueError('A imagem deve ter no máximo 6 MB.')
            with Image.open(io.BytesIO(raw)) as image:
                if image.width * image.height > 25_000_000: raise ValueError('A imagem é grande demais.')
                result = predict(image, mass)
            self.json_reply(200, result)
        except (ValueError, TypeError, KeyError, UnidentifiedImageError, OSError, json.JSONDecodeError) as exc:
            self.json_reply(400, {'erro': str(exc) or 'Não foi possível analisar esta imagem.'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', '8000'))
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    print(f'Abra http://127.0.0.1:{port}  |  Para encerrar, pressione Ctrl+C', flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: server.server_close()
