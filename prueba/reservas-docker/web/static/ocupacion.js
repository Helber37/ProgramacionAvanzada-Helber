// Panel de ocupación: datos globales de PostgreSQL consultados cada cinco segundos por WSGI.
(() => {
  const $ = id => document.getElementById(id); // Localiza los componentes del panel.
  if (!$('ocupacion-lista')) return; // Evita ejecutarse fuera del panel.
  let cargando = false; // Impide solicitudes simultáneas.
  const escapar = v => String(v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); // Escapa texto de la base de datos.
  // Formatea etiquetas de horas para la interfaz, sin cambiar los cálculos de la API.
  const hora12 = valor => {
    const [h, m = 0] = String(valor).split(':').map(Number);
    return `${h % 12 || 12}:${String(m).padStart(2, '0')} ${h < 12 ? 'a. m.' : 'p. m.'}`;
  };
  const porcentaje = (n, total) => total ? Math.round(n * 100 / total) : 0; // Evita divisiones entre cero.
  function grafica(id, datos, clave, unidad) { // Construye las barras con el estilo original.
    const max = Math.max(1, ...datos.map(d => Number(d.cantidad) || 0)); // Altura máxima relativa.
    $(id).innerHTML = datos.map(d => {
      const valor = Number(d.cantidad) || 0; // Cantidad para cada intervalo.
      const altura = valor ? Math.max(4, valor * 100 / max) : 0; // Porcentaje visual de la barra.
      return `<div class="oc-barra-item" title="${valor} ${unidad}"><span class="oc-barra-valor">${valor}</span><div class="oc-barra-pista"><div class="oc-barra-relleno" style="height:${altura}%"></div></div><small>${escapar(d[clave])}</small></div>`;
    }).join(''); // Actualiza el gráfico sin recargar la página.
  }
  async function actualizar() { // Consulta ocupación y estadísticas en horario de Colombia.
    if (cargando || document.hidden) return; // No acumula solicitudes.
    cargando = true;
    try {
      const respuesta = await fetch('/api/ocupacion', {cache:'no-store'}); // API Flask compatible con Gunicorn WSGI.
      if (!respuesta.ok) throw new Error(`HTTP ${respuesta.status}`); // Detecta errores de servidor.
      const datos = await respuesta.json(); // Recibe datos globales, sin filtrar por usuario.
      const total = Number(datos.total_modulos) || 0;
      const ocupados = Number(datos.ocupados) || 0;
      const pct = porcentaje(ocupados, total);
      $('ocupacion-pct').textContent = `${pct}%`;
      $('ocupacion-anillo').style.setProperty('--avance', `${pct}%`);
      $('ocupacion-modulos').textContent = `${ocupados} de ${total} módulos`;
      $('ocupacion-espacios').textContent = `${datos.espacios_en_uso} de ${datos.total_espacios}`;
      $('ocupacion-hoy').textContent = datos.reservas_hoy;
      const fecha = (datos.fecha || '').split('-').reverse().join('/'); // Convierte AAAA-MM-DD a DD/MM/AAAA.
      $('ocupacion-actualizado').textContent = `Actualizado: ${fecha} · ${hora12(datos.actualizado)} (Colombia) · cada 5 s`;
      // Cada segmento representa un módulo real; su estado cambia al iniciar o terminar una reserva.
      $('ocupacion-lista').innerHTML = (datos.espacios || []).map(e => {
        const modulos = e.modulos || []; // Lista de módulos obtenida de PostgreSQL.
        const cantidad = modulos.filter(m => m.estado === 'ocupado').length; // Solo ocupados ahora.
        const total = modulos.length; // Total de módulos del espacio.
        const segmentos = modulos.map(m => {
          const ocupado = m.estado === 'ocupado'; // Una reserva futura no ocupa el módulo todavía.
          const estado = ocupado ? 'Ocupado ahora' : 'Disponible ahora';
          return `<span class="oc-modulo-segmento ${ocupado ? 'esta-ocupado' : 'esta-libre'}" title="${escapar(m.nombre)}: ${estado}" aria-label="${escapar(m.nombre)}: ${estado}"></span>`;
        }).join('');
        return `<div class="oc-espacio"><div class="oc-espacio-titulo"><strong>${escapar(e.nombre)}</strong><small>${cantidad}/${total} ocupados ahora</small></div><div class="oc-barra-modulos" role="group" aria-label="${escapar(e.nombre)}: ${cantidad} de ${total} módulos ocupados">${segmentos || '<small>Sin módulos</small>'}</div>${total > 1 ? `<div class="oc-modulo-etiquetas">${modulos.map(m => `<small title="${escapar(m.nombre)}">${escapar(m.nombre)}</small>`).join('')}</div>` : ''}</div>`;
      }).join('') || '<p class="nota">No hay espacios activos.</p>';
      // La gráfica de hoy incluye reservas programadas; no equivale a la ocupación actual.
      const horas = (datos.horas || []).filter(d => Number(d.hora) >= 6 && Number(d.hora) <= 21);
      grafica('ocupacion-horas', horas.map(d => ({...d, etiqueta: hora12(`${d.hora}:00`)})), 'etiqueta', 'módulos reservados');
      const maximo = Math.max(0, ...horas.map(d => Number(d.cantidad) || 0));
      const pico = horas.find(d => Number(d.cantidad) === maximo);
      $('ocupacion-hora-pico').textContent = maximo && pico
        ? `Mayor ocupación programada: ${String(pico.hora).padStart(2, '0')}:00 · ${maximo} ${maximo === 1 ? 'módulo' : 'módulos'}`
        : 'No hay módulos reservados para hoy.';
      grafica('ocupacion-semana', datos.proximos || [], 'fecha', 'reservas confirmadas');
    } catch (error) {
      $('ocupacion-actualizado').textContent = 'No se pudo actualizar · reintentando cada 5 s';
      console.error('Panel de ocupación:', error); // Ayuda a diagnosticar errores de la API.
    } finally { cargando = false; } // Habilita la siguiente consulta.
  }
  actualizar(); // Primera consulta al abrir.
  setInterval(actualizar, 5000); // Refresca sin WebSocket, compatible con WSGI.
  window.addEventListener('pageshow', actualizar); // Refresca al volver a la página.
  window.addEventListener('focus', actualizar); // Refresca al volver a la pestaña.
  document.addEventListener('visibilitychange', () => {if (!document.hidden) actualizar();});
})();
