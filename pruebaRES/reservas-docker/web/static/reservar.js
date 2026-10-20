const $ = (id) => document.getElementById(id);
const A = 6, C = 22, TOTAL = (C - A) * 60;   // escala visual de la franja: 6:00 a 22:00

let info = null;
let datos = { horario: [], cierres: [], ocupados: {} };

const aMin = (t) => { const [h, m] = t.split(':').map(Number); return h * 60 + m; };
const pct = (min) => Math.min(100, Math.max(0, ((min - A * 60) / TOTAL) * 100));

// ---- escala de horas ----
$('horas').innerHTML = Array.from({ length: (C - A) / 2 + 1 }, (_, i) => `<span>${A + i * 2}h</span>`).join('');

// ---- filtros ----
function filtrarEspacios() {
  const cat = $('categoria').value, acc = $('solo_accesibles').checked;
  [...$('espacio').options].forEach((o) => {
    if (!o.value) return;
    const ok = (!cat || o.dataset.categoria === cat) && (!acc || o.dataset.accesible === '1');
    o.hidden = !ok;
    o.disabled = !ok;
  });
  if ($('espacio').selectedOptions[0]?.disabled) {
    $('espacio').value = '';
    cargarEspacio();
  }
}

// ---- espacio seleccionado ----
async function cargarEspacio() {
  const id = $('espacio').value;
  if (!id) {
    info = null;
    $('info').hidden = true;
    $('modulos-caja').hidden = true;
    return dibujar();
  }
  info = await (await fetch(`/api/espacio/${id}`)).json();

  const partes = [`Capacidad: ${info.capacidad} personas.`,
    `Reserva con al menos ${info.anticipacion_dias} días de anticipación, máximo ${info.max_horas} horas.`];
  if (info.accesible) partes.push('Accesible para movilidad reducida' + (info.notas_accesibilidad ? `: ${info.notas_accesibilidad}.` : '.'));
  if (info.recursos.length) partes.push('Recursos: ' + info.recursos.map((r) => `${r.nombre} (${r.cantidad})`).join(', ') + '.');
  $('info').textContent = partes.join(' ');
  $('info').hidden = false;

  const caja = $('modulos');
  caja.innerHTML = '';
  if (info.modulos.length > 1) {
    info.modulos.forEach((m) => {
      const l = document.createElement('label');
      l.className = 'check';
      const i = document.createElement('input');
      i.type = 'checkbox'; i.name = 'modulos'; i.value = m.id;
      i.addEventListener('change', dibujar);
      l.append(i, ` ${m.nombre} (${m.capacidad} personas)`);
      caja.appendChild(l);
    });
  }
  $('modulos-caja').hidden = info.modulos.length <= 1;

  const d = new Date();
  d.setDate(d.getDate() + info.anticipacion_dias);
  $('fecha').min = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  $('hora_inicio').dataset.max = info.max_horas;
  await cargarDisponibilidad();
}

async function cargarDisponibilidad() {
  datos = { horario: [], cierres: [], ocupados: {} };
  if (info && $('fecha').value) {
    const r = await fetch(`/api/disponibilidad?espacio_id=${$('espacio').value}&fecha=${$('fecha').value}`);
    if (r.ok) datos = await r.json();
  }
  dibujar();
}

// ---- dibujo de la franja: una fila por módulo ----
const elegidos = () => {
  const marcados = [...document.querySelectorAll('input[name=modulos]:checked')].map((i) => Number(i.value));
  return marcados.length ? marcados : (info ? info.modulos.map((m) => m.id) : []);
};

function cerrados() {
  const abiertos = datos.horario.map((h) => [aMin(h.apertura), aMin(h.cierre)]).sort((a, b) => a[0] - b[0]);
  const res = [];
  let cur = A * 60;
  if (!$('fecha').value) return res;
  for (const [a, c] of abiertos) { if (a > cur) res.push([cur, a]); cur = Math.max(cur, c); }
  if (cur < C * 60) res.push([cur, C * 60]);
  datos.cierres.forEach((x) => res.push([aMin(x.inicio), aMin(x.fin)]));
  return res;
}

function bloque(ini, fin, clase, titulo) {
  const b = document.createElement('div');
  b.className = 'bloque ' + clase;
  b.style.left = pct(ini) + '%';
  b.style.width = Math.max(0, pct(fin) - pct(ini)) + '%';
  if (titulo) b.title = titulo;
  return b;
}

function dibujar() {
  const cont = $('franjas');
  cont.innerHTML = '';
  const mods = info ? info.modulos : [null];
  const sel = elegidos();
  const ini = $('hora_inicio').value, fin = $('hora_fin').value;
  const hayRango = ini && fin && aMin(fin) > aMin(ini);

  mods.forEach((m) => {
    const fila = document.createElement('div');
    fila.className = 'mod';
    if (m && info.modulos.length > 1) {
      const n = document.createElement('span');
      n.className = 'mod-n';
      n.textContent = m.nombre;
      fila.appendChild(n);
    }
    const franja = document.createElement('div');
    franja.className = 'franja';
    cerrados().forEach(([a, c]) => franja.appendChild(bloque(a, c, 'cerrado')));
    (m && datos.ocupados[m.id] || []).forEach((o) => franja.appendChild(bloque(aMin(o.inicio), aMin(o.fin), 'ocupado', `${o.inicio} - ${o.fin}`)));
    if (hayRango && m && sel.includes(m.id)) franja.appendChild(bloque(aMin(ini), aMin(fin), 'tuyo'));
    fila.appendChild(franja);
    cont.appendChild(fila);
  });
  validar();
}

// ---- validación en el navegador (el servidor vuelve a validar) ----
function validar() {
  let msg = '';
  const ini = $('hora_inicio').value, fin = $('hora_fin').value;
  if (info && ini && fin) {
    const a = aMin(ini), b = aMin(fin);
    const sel = elegidos();
    if (b <= a) msg = 'La hora de fin debe ser posterior a la de inicio.';
    else if (b - a > info.max_horas * 60) msg = `Este espacio permite máximo ${info.max_horas} horas por reserva.`;
    else if (cerrados().some(([x, y]) => a < y && b > x)) msg = 'El espacio está cerrado en parte de ese horario.';
    else if (sel.some((id) => (datos.ocupados[id] || []).some((o) => a < aMin(o.fin) && b > aMin(o.inicio))))
      msg = 'Ese horario se cruza con una reserva existente.';
    else if ($('asistentes').value) {
      const cap = info.modulos.filter((m) => sel.includes(m.id)).reduce((s, m) => s + m.capacidad, 0);
      if (Number($('asistentes').value) > cap) msg = `Lo que elegiste tiene capacidad para ${cap} personas.`;
    }
  }
  $('error-js').textContent = msg;
  $('error-js').hidden = !msg;
}

$('categoria').addEventListener('change', filtrarEspacios);
$('solo_accesibles').addEventListener('change', filtrarEspacios);
$('espacio').addEventListener('change', cargarEspacio);
$('fecha').addEventListener('change', cargarDisponibilidad);
['hora_inicio', 'hora_fin', 'asistentes'].forEach((id) => $(id).addEventListener('input', dibujar));
$('form-reserva').addEventListener('submit', (e) => { validar(); if (!$('error-js').hidden) e.preventDefault(); });
dibujar();
