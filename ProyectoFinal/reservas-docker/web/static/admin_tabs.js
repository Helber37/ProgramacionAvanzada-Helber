// Pestañas independientes del panel administrativo ITM.
(() => {
  "use strict";
  const botones = [...document.querySelectorAll("[data-admin-tab]")]; // Pestañas disponibles.
  const paneles = [...document.querySelectorAll(".admin-seccion[role='tabpanel']")]; // Contenido de cada pestaña.
  const permitidas = new Set(botones.map(b => b.dataset.adminTab)); // Identificadores válidos.
  if (!botones.length || !paneles.length) return; // Evita ejecutarse en otras páginas.

  function seleccionar(id, actualizarUrl = false) { // Activa una sola sección.
    if (!permitidas.has(id)) id = "reservas"; // Selección predeterminada.
    botones.forEach(boton => {
      const activa = boton.dataset.adminTab === id; // Comprueba pestaña seleccionada.
      boton.setAttribute("aria-selected", String(activa)); // Estado accesible.
      boton.tabIndex = activa ? 0 : -1; // Navegación con teclado.
    });
    paneles.forEach(panel => { panel.hidden = panel.id !== id; }); // Oculta los demás paneles.
    try { sessionStorage.setItem("itm-admin-tab", id); } catch (_) {} // Conserva la selección.
    if (actualizarUrl && history.replaceState) history.replaceState(null, "", `#${id}`); // Enlace a la pestaña.
  }

  let inicial = location.hash.slice(1); // Prioriza la pestaña indicada en la URL.
  if (!permitidas.has(inicial)) {
    try { inicial = sessionStorage.getItem("itm-admin-tab"); } catch (_) {} // Recupera la última pestaña.
  }
  seleccionar(inicial || "reservas"); // Muestra una sola pestaña al iniciar.
  botones.forEach((boton, indice) => {
    boton.addEventListener("click", () => seleccionar(boton.dataset.adminTab, true)); // Cambio por clic.
    boton.addEventListener("keydown", evento => { // Navegación accesible con flechas.
      if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(evento.key)) return;
      evento.preventDefault(); // Evita desplazamiento horizontal de la página.
      let destino = indice;
      if (evento.key === "ArrowRight") destino = (indice + 1) % botones.length;
      if (evento.key === "ArrowLeft") destino = (indice - 1 + botones.length) % botones.length;
      if (evento.key === "Home") destino = 0;
      if (evento.key === "End") destino = botones.length - 1;
      botones[destino].focus(); // Coloca el foco en la pestaña.
      seleccionar(botones[destino].dataset.adminTab, true); // Muestra su contenido.
    });
  });
  window.addEventListener("hashchange", () => { // Admite enlaces directos a secciones.
    const id = location.hash.slice(1);
    if (permitidas.has(id)) seleccionar(id);
  });
})();
