const $ = id => document.getElementById(id);
let selected = null, photoBase64 = null, examples = [];
const fmt = n => new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 }).format(n);

function showPreview(src) {
  $('preview').src = src; $('preview').hidden = false; $('image-tag').hidden = false; $('empty').hidden = true;
  $('results').hidden = true; $('placeholder').hidden = false; $('error').textContent = '';
}
function selectSample(s, button) {
  selected = s; photoBase64 = null; $('photo').value = ''; $('mass').value = s.massa_total_g;
  document.querySelectorAll('.sample').forEach(x => x.classList.remove('active'));
  button.classList.add('active'); showPreview(s.foto);
}
async function loadSamples() {
  try {
    const response = await fetch('/api/samples'); if (!response.ok) throw Error();
    examples = await response.json();
    examples.forEach((s, i) => {
      const b = document.createElement('button'); b.className = 'sample'; b.type = 'button'; b.setAttribute('aria-label', `Selecionar exemplo ${i + 1}`);
      const img = document.createElement('img'); img.src = s.foto; img.alt = `Foto do prato de teste ${i + 1}`; b.appendChild(img);
      b.addEventListener('click', () => selectSample(s,b)); $('samples').appendChild(b);
    });
  } catch (_) { $('error').textContent = 'Não foi possível carregar os exemplos. Você pode enviar uma foto.'; }
}
$('photo').addEventListener('change', async event => {
  const file = event.target.files[0]; if (!file) return;
  if (!['image/jpeg','image/png'].includes(file.type) || file.size > 6*1024*1024) { $('error').textContent = 'Selecione uma imagem JPG ou PNG de até 6 MB.'; event.target.value = ''; return; }
  selected = null; document.querySelectorAll('.sample').forEach(x => x.classList.remove('active'));
  const reader = new FileReader();
  reader.onload = () => { photoBase64 = reader.result.split(',')[1]; showPreview(reader.result); };
  reader.onerror = () => { $('error').textContent = 'Não foi possível ler a foto.'; };
  reader.readAsDataURL(file);
});
$('mass').addEventListener('input', () => { $('results').hidden = true; $('placeholder').hidden = false; $('error').textContent = ''; });
$('analyze').addEventListener('click', async () => {
  $('error').textContent = '';
  const mass = Number($('mass').value);
  if (!selected && !photoBase64) { $('error').textContent = 'Selecione um prato ou envie uma foto para começar.'; return; }
  if (!Number.isFinite(mass) || mass <= 0 || mass > 10000) { $('error').textContent = 'Informe o peso da comida entre 0 e 10.000 g.'; return; }
  const body = {massa_total_g: mass}; if (selected) body.sample_id = selected.id; else body.foto_base64 = photoBase64;
  $('analyze').disabled = true; $('analyze').textContent = 'Analisando…';
  try {
    const response = await fetch('/api/predict', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
    const data = await response.json(); if (!response.ok) throw new Error(data.erro || 'Não foi possível analisar.');
    $('estimate').textContent = fmt(data.massa_estimada_g);
    $('presence').textContent = data.presenca ? 'Indica presença' : 'Não indica presença';
    $('proportion').textContent = `${fmt(data.fracao * 100)}% do peso`;
    if (selected && Math.abs(mass - selected.massa_total_g) < 0.001) {
      $('reference').textContent = `Referência real: ${fmt(selected.frango_real_g)} g`; $('reference').hidden = false;
    } else $('reference').hidden = true;
    $('placeholder').hidden = true; $('results').hidden = false;
  } catch (err) { $('error').textContent = err.message || 'Erro ao analisar a imagem.'; }
  finally { $('analyze').disabled = false; $('analyze').innerHTML = 'Analisar prato <span>✦</span>'; }
});
loadSamples();
