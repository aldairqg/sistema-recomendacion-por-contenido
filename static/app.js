const $ = id => document.getElementById(id);
const format = (n, digits = 3) => Number(n).toLocaleString('es-PE', {maximumFractionDigits: digits, minimumFractionDigits: digits});
const escapeHTML = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let stats, seed, result, selected = 0, searchTimer, searchVersion = 0, requestVersion = 0;
const status = (message, error = false) => { $('status').textContent = message; $('status').classList.toggle('error', error); };
async function api(path, params = {}) {
  const response = await fetch(path + '?' + new URLSearchParams(params));
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || 'No se pudo completar la consulta.');
  return body;
}
function choose(track) {
  requestVersion++;
  searchVersion++;
  seed = track;
  result = null;
  $('search-results').replaceChildren();
  $('search').value = '';
  $('seed').innerHTML = `<div class="seed-kicker">CANCIÓN DE REFERENCIA</div><div class="seed-art" aria-hidden="true"></div><h3>${escapeHTML(track.name)}</h3><p>${escapeHTML(track.artists.replaceAll(';', ', '))}</p><div>${track.genres.map(g => `<span class="genre">${escapeHTML(g)}</span>`).join('')}</div>`;
  $('recommend').disabled = false;
  $('comparison').hidden = true;
  $('recommendations').innerHTML = '<p class="empty">Pulsa «Encontrar canciones» para explorar este sonido.</p>';
  $('result-caption').textContent = 'Nueva canción seleccionada. Lista para comparar.';
  status('Canción seleccionada. Puedes ajustar los pesos antes de recomendar.');
}
function weights() { return Object.fromEntries(stats.features.map(f => [f.key, Number($('weight-' + f.key).value)])); }
async function recommend() {
  if (!seed) return;
  const version = ++requestVersion;
  $('recommend').disabled = true;
  $('comparison').hidden = true;
  $('recommendations').innerHTML = '<p class="empty">Comparando vectores de audio…</p>';
  status('Calculando similitudes con el catálogo…');
  try {
    const data = await api('/api/recommend', {id: seed.id, count: $('count').value, weights: JSON.stringify(weights())});
    if (version !== requestVersion) return;
    result = data;
    selected = 0;
    renderResults();
    if (result.recommendations.length) compare(0);
    status(`Comparación completa · ${format(result.compared, 0)} candidatos · solo características de audio.`);
  } catch (error) {
    if (version !== requestVersion) return;
    result = null;
    $('recommendations').innerHTML = '<p class="empty">No se pudo calcular el ranking. Revisa los pesos e inténtalo de nuevo.</p>';
    status(error.message, true);
  } finally {
    if (version === requestVersion) $('recommend').disabled = false;
  }
}
function renderResults() {
  $('result-count').textContent = 'TOP ' + result.recommendations.length;
  $('result-caption').textContent = 'Selecciona un resultado para ver su explicación.';
  $('recommendations').innerHTML = result.recommendations.map((track, i) => `<button class="track ${i === selected ? 'selected' : ''}" data-index="${i}" aria-pressed="${i === selected}" aria-label="Comparar ${escapeHTML(track.name)} de ${escapeHTML(track.artists)}; coseno ${format(track.score)}"><span class="rank">${String(i+1).padStart(2,'0')}</span><span class="cover" style="--hue:${[90,270,30,170,210,320][i%6]}" aria-hidden="true">♫</span><span class="track-text"><span class="track-name">${escapeHTML(track.name)}</span><span class="track-artist">${escapeHTML(track.artists.replaceAll(';', ', '))}</span><span class="track-tags">Cercanía en: ${escapeHTML(track.closest.slice(0,2).join(' · '))}</span></span><span class="score">${format(track.score)}</span><span class="arrow" aria-hidden="true">↗</span></button>`).join('') || '<p class="empty">No hay candidatos válidos con esta configuración.</p>';
}
function compare(index) {
  selected = index;
  document.querySelectorAll('.track').forEach((node, i) => {node.classList.toggle('selected', i === index); node.setAttribute('aria-pressed', String(i === index));});
  const track = result.recommendations[index];
  $('comparison').hidden = false;
  $('legend').innerHTML = `<span>${escapeHTML(result.seed.name)} · base</span><span>${escapeHTML(track.name)} · recomendada</span>`;
  $('comparison-title').textContent = track.name;
  $('comparison-reason').textContent = `Los atributos activos con menor diferencia estandarizada son ${track.closest.join(', ').toLowerCase()}. Los nueve aportes ponderados determinan el resultado.`;
  renderRadar(result.seed, track);
  $('bars').innerHTML = track.explanation.map(f => {
    // Las barras muestran proximidad visual; las unidades originales están a la derecha.
    const display = value => f.key === 'tempo' ? Math.min(1, Math.max(0, value / 250)) : f.key === 'loudness' ? Math.min(1, Math.max(0, (value + 60) / 66)) : value;
    return `<div class="bar-row"><span>${escapeHTML(f.label)}</span><div class="bar-pair"><div class="bar" style="width:${display(f.seed_raw)*100}%"></div><div class="bar purple" style="width:${display(f.candidate_raw)*100}%"></div></div><span class="bar-values">${format(f.seed_raw, f.key === 'tempo' || f.key === 'loudness' ? 1 : 2)} / ${format(f.candidate_raw, f.key === 'tempo' || f.key === 'loudness' ? 1 : 2)}${f.key === 'tempo' ? ' BPM' : f.key === 'loudness' ? ' dB' : ''}</span></div>`;
  }).join('') + '<p class="footnote">Base / recomendada. Barras: atributos 0–1; tempo 0–250 BPM; sonoridad −60–6 dB. Valores fuera del rango se recortan solo en el dibujo.</p>';
  $('math-body').innerHTML = track.explanation.map(f => `<tr><td>${escapeHTML(f.label)}</td><td>${format(f.seed_raw)}</td><td>${format(f.candidate_raw)}</td><td>${format(f.seed_z)}</td><td>${format(f.candidate_z)}</td><td>${format(f.weight,1)}</td><td>${format(f.contribution,6)}</td></tr>`).join('');
  $('math-total').textContent = format(track.score,6);
}
function renderRadar(base, candidate) {
  const features = stats.features.slice(0,7), cx = 220, cy = 170, radius = 110;
  const point = (i, value) => {const angle = -Math.PI/2 + i * Math.PI*2/features.length; return [cx+Math.cos(angle)*radius*value,cy+Math.sin(angle)*radius*value];};
  const polygon = (values, color) => `<polygon points="${values.map((v,i) => point(i,v).join(',')).join(' ')}" fill="${color}" fill-opacity=".10" stroke="${color}" stroke-width="2"/>`;
  let svg = '<svg viewBox="0 0 440 340" role="img" aria-label="Comparación de siete características: verde es la base y violeta la recomendada. Valores exactos en las barras y tabla.">';
  for (const level of [.25,.5,.75,1]) svg += `<polygon points="${features.map((_,i) => point(i,level).join(',')).join(' ')}" fill="none" stroke="#334032" stroke-width="1"/>`;
  features.forEach((feature,i) => {const end = point(i,1), label = point(i,1.25); svg += `<line x1="${cx}" y1="${cy}" x2="${end[0]}" y2="${end[1]}" stroke="#2d362c"/><text x="${label[0]}" y="${label[1]}" text-anchor="${label[0] < 210 ? 'end' : label[0] > 230 ? 'start' : 'middle'}" dominant-baseline="middle" fill="#9eada1" font-size="10">${escapeHTML(feature.label === 'Presencia de público' ? 'Público' : feature.label)}</text>`;});
  svg += polygon(features.map(f => base.values[f.key]), '#c2f970');
  svg += polygon(features.map(f => candidate.values[f.key]), '#b6a0ec');
  $('radar').innerHTML = svg + '</svg>';
}
$('search').addEventListener('input', () => {
  clearTimeout(searchTimer);
  const query = $('search').value.trim(), version = ++searchVersion;
  if (query.length < 2) { $('search-results').replaceChildren(); return; }
  searchTimer = setTimeout(async () => {
    try {
      const tracks = await api('/api/search', {q: query});
      if (version !== searchVersion) return;
      $('search-results').replaceChildren();
      if (!tracks.length) { $('search-results').innerHTML = '<p class="empty">Sin coincidencias. Prueba otro título o artista.</p>'; return; }
      tracks.forEach(track => {const button = document.createElement('button');button.className = 'search-hit';button.innerHTML = `${escapeHTML(track.name)}<span>${escapeHTML(track.artists)}</span>`;button.addEventListener('click', () => choose(track));$('search-results').append(button);});
    } catch (error) { if (version === searchVersion) status(error.message, true); }
  }, 220);
});
$('recommendations').addEventListener('click', event => {const target = event.target.closest('[data-index]');if (target && result) compare(Number(target.dataset.index));});
$('recommend').addEventListener('click', recommend);
$('reset').addEventListener('click', () => {stats.features.forEach(f => {$('weight-'+f.key).value = 1;$('output-'+f.key).textContent = '1.0';});status('Pesos restablecidos. Pulsa «Encontrar canciones» para recalcular.');});
$('count').addEventListener('change', () => status('Cantidad modificada. Pulsa «Encontrar canciones» para recalcular.'));
document.querySelectorAll('.nav').forEach(button => button.addEventListener('click', () => {document.querySelectorAll('.nav').forEach(b => {b.classList.toggle('active', b === button);b.setAttribute('aria-pressed', String(b === button));});$('explore-view').hidden = button.dataset.view !== 'explore';$('learn-view').hidden = button.dataset.view !== 'learn';}));
async function init() {
  try {
    stats = await api('/api/stats');
    $('track-stat').textContent = format(stats.tracks,0);
    $('genre-stat').textContent = format(stats.genres,0);
    $('cleaning-text').textContent = `${format(stats.rows,0)} filas originales → ${format(stats.tracks,0)} canciones. Se descartan ${stats.invalid_rows} filas sin identidad o título/artista y ${format(stats.duplicate_ids,0)} repeticiones de ID. Se imputan ${stats.imputed_values} valores numéricos.`;
    $('sliders').innerHTML = stats.features.map(f => `<div class="slider-row"><label for="weight-${f.key}">${escapeHTML(f.label)}<output id="output-${f.key}" for="weight-${f.key}">1.0</output></label><input id="weight-${f.key}" type="range" min="0" max="3" step="0.1" value="1"></div>`).join('');
    stats.features.forEach(f => $('weight-'+f.key).addEventListener('input', event => {$('output-'+f.key).textContent = Number(event.target.value).toFixed(1);status('Pesos modificados. Pulsa «Encontrar canciones» para aplicar los cambios.');}));
    const tracks = await api('/api/search', {q:'Blinding Lights'});
    const initial = tracks.find(t => t.artists === 'The Weeknd') || tracks[0];
    if (initial) {choose(initial);await recommend();} else status('Catálogo listo. Busca una canción para comenzar.');
  } catch(error) {status('No se pudo cargar el catálogo: ' + error.message, true);}
}
init();
