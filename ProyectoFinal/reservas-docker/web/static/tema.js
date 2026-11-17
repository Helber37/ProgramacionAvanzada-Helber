// Preferencia de apariencia guardada únicamente en este navegador.
(() => {
  const boton = document.getElementById('cambiar-tema');
  const icono = document.getElementById('icono-tema');
  const texto = document.getElementById('texto-tema');
  if (!boton) return;
  function actualizar() {
    const oscuro = document.documentElement.dataset.theme === 'oscuro';
    icono.textContent = oscuro ? '☀' : '☾';
    texto.textContent = oscuro ? 'Modo claro' : 'Modo oscuro';
    boton.setAttribute('aria-label', oscuro ? 'Activar modo claro' : 'Activar modo oscuro');
    boton.setAttribute('aria-pressed', String(oscuro));
  }
  boton.addEventListener('click', () => {
    const siguiente = document.documentElement.dataset.theme === 'oscuro' ? 'claro' : 'oscuro';
    document.documentElement.dataset.theme = siguiente;
    try { localStorage.setItem('itm-tema', siguiente); } catch (_) { /* Sin almacenamiento disponible */ }
    actualizar();
  });
  actualizar();
})();
