/* Cálculo en vivo del formulario de operaciones (UX).
   La fuente de verdad es el servidor; esto es solo una vista previa. */
(function () {
  "use strict";

  var form = document.getElementById("form-operacion");
  if (!form) return;

  var DEF_CV  = parseFloat(form.dataset.defaultCv)  || 3;
  var DEF_ALQ = parseFloat(form.dataset.defaultAlq) || 4.5;
  var DATERO_PCT = parseFloat(form.dataset.dateroPct) || 20;
  var CAPTADOR_PCT = parseFloat(form.dataset.captadorPct) || 33;

  // % fijo por situación del Agente Asistente al Ausente (Acta 001/2026).
  // La situación "A" es especial: min(US$100, 10% de la bruta de la punta).
  var AAA_PCT = { B1: 50, B2: 33, B3: 25, C1: 50, C2: 66 };
  var AAA_TOPE_A = 100;
  var AAA_PCT_A = 10;

  var CAPTADORES = {};
  try {
    var elCaptadores = document.getElementById("data-captadores");
    if (elCaptadores) CAPTADORES = JSON.parse(elCaptadores.textContent || "{}");
  } catch (e) { CAPTADORES = {}; }

  // IDs de figuras personalizadas activas (Configuración) — se comportan como
  // el datero, pero con % editable y disponibles en cualquier tipo de operación.
  var FIGURAS_PERSONALIZADAS = [];
  try {
    var elPers = document.getElementById("data-figuras-personalizadas");
    if (elPers) FIGURAS_PERSONALIZADAS = JSON.parse(elPers.textContent || "[]");
  } catch (e) { FIGURAS_PERSONALIZADAS = []; }
  var TIPOS_PERSONALIZADA = FIGURAS_PERSONALIZADAS.map(function (id) { return "personalizada" + id; });

  var ETIQUETA_FIGURA = { datero: "Datero", captador: "Captador de desarrollo", aaa: "AAA" };

  function esPersonalizada(tipoFig) { return tipoFig.indexOf("personalizada") === 0; }

  function checkDe(tipoFig, i) {
    if (esPersonalizada(tipoFig)) {
      var fid = tipoFig.replace("personalizada", "");
      return form.querySelector('.personalizada-check[data-figura-id="' + fid + '"][data-punta="' + i + '"]');
    }
    return form.querySelector("." + tipoFig + '-check[data-punta="' + i + '"]');
  }

  var tipoSelect   = document.getElementById("tipo-select");
  var monedaSelect = document.getElementById("moneda-select");
  var montoVenta   = document.getElementById("monto-venta");
  var duracion     = document.getElementById("duracion-meses");
  var canon        = document.getElementById("canon-mensual");
  var montoTotal   = document.getElementById("monto-total");

  // Enteros (sin centavos, como en Argentina). El símbolo va con espacio irrompible.
  var fmt = new Intl.NumberFormat("es-AR", { minimumFractionDigits: 0, maximumFractionDigits: 0 });

  function tipo() { return tipoSelect.value; }
  function esCV() { return tipo() === "COMPRAVENTA"; }
  function simbolo() {
    if (esCV()) return "US$";
    return monedaSelect.value === "USD" ? "US$" : "$";
  }
  function money(n) { return simbolo() + " " + fmt.format(isFinite(n) ? Math.round(n) : 0); }
  function num(v) {
    if (v === null || v === undefined || v === "") return 0;
    var n = parseFloat(("" + v).replace(",", "."));
    return isFinite(n) ? n : 0;
  }
  function defaultPct() { return esCV() ? DEF_CV : DEF_ALQ; }
  function montoOperacion() { return esCV() ? num(montoVenta.value) : num(montoTotal.value); }

  // ---- Mostrar/ocultar grupos según tipo ----
  function aplicarTipo() {
    var cv = esCV();
    toggle(document.querySelector(".grupo-cv"), cv);
    toggle(document.querySelector(".grupo-alq"), !cv);
    toggle(document.querySelector(".campo-moneda-alq"), !cv);

    // Etiquetas de rol de cada punta
    document.querySelectorAll(".punta__rol").forEach(function (el) {
      el.textContent = cv ? el.dataset.rolCv : el.dataset.rolAlq;
    });
    // requeridos
    montoVenta.required = cv;
    montoTotal.required = !cv;
    recalcular();
  }

  // ---- Total contrato = canon * meses (si el usuario no lo editó) ----
  if (montoTotal) montoTotal.addEventListener("input", function () { montoTotal.dataset.editado = "1"; recalcular(); });
  function sincronizarTotalContrato() {
    if (esCV()) return;
    if (montoTotal.dataset.editado === "1") return;
    var t = num(canon.value) * num(duracion.value);
    montoTotal.value = t ? t : "";
  }

  // ---- Lógica por punta ----
  function generaComision(rep) { return rep === "INFINITY" || rep === "DESARROLLO"; }

  function aplicarPunta(i) {
    var rep = form.querySelector('.rep-select[data-punta="' + i + '"]').value;
    toggle(form.querySelector('.bloque-infinity[data-punta="' + i + '"]'), generaComision(rep));
    toggle(form.querySelector('.campo-desarrollo[data-punta="' + i + '"]'), rep === "DESARROLLO");
    toggle(form.querySelector('.bloque-otra[data-punta="' + i + '"]'), rep === "OTRA_INMOBILIARIA");

    var comtipo = form.querySelector('.comtipo-select[data-punta="' + i + '"]').value;
    toggle(form.querySelector('.campo-porcentaje[data-punta="' + i + '"]'), comtipo === "PORCENTAJE");
    toggle(form.querySelector('.campo-fijo[data-punta="' + i + '"]'), comtipo === "MONTO_FIJO");

    // Figuras adicionales: el bloque general se muestra en cualquier punta que
    // genera comisión (compraventa o alquiler); dentro, la sub-sección del
    // Acta 001/2026 (datero/captador/AAA) solo aplica a compraventa.
    toggle(form.querySelector('.figuras-compraventa[data-punta="' + i + '"]'), generaComision(rep));
    toggle(form.querySelector('.figuras-acta-cv[data-punta="' + i + '"]'), esCV());
    toggle(form.querySelector('.campo-captador[data-punta="' + i + '"]'), rep === "DESARROLLO");

    ["datero", "captador", "aaa"].concat(TIPOS_PERSONALIZADA).forEach(function (tipoFig) {
      var check = checkDe(tipoFig, i);
      var detalle = form.querySelector('.figura-detalle[data-figura="' + tipoFig + '"][data-punta="' + i + '"]');
      toggle(detalle, !!(check && check.checked));
    });
  }

  // ---- Figuras adicionales: cálculo de cada una ----
  function montoAAA(situacion, brutaPunta) {
    if (situacion === "A") return Math.min(AAA_TOPE_A, brutaPunta * (AAA_PCT_A / 100));
    var pct = AAA_PCT[situacion];
    return pct === undefined ? 0 : brutaPunta * (pct / 100);
  }

  function calcularFigura(tipoFig, i, brutaPunta) {
    var check = checkDe(tipoFig, i);
    if (!check || !check.checked) return null;
    var agenteSel = form.querySelector('.figura-agente-select[data-figura="' + tipoFig + '"][data-punta="' + i + '"]');
    var retSel = form.querySelector('.figura-retencion-select[data-figura="' + tipoFig + '"][data-punta="' + i + '"]');
    if (!agenteSel || !agenteSel.value) return null;

    var etiqueta;
    var bruta;
    if (tipoFig === "aaa") {
      var sitSel = form.querySelector('.aaa-situacion-select[data-punta="' + i + '"]');
      if (!sitSel || !sitSel.value) return null;
      bruta = montoAAA(sitSel.value, brutaPunta);
      etiqueta = ETIQUETA_FIGURA.aaa;
    } else if (tipoFig === "datero") {
      bruta = brutaPunta * (DATERO_PCT / 100);
      etiqueta = ETIQUETA_FIGURA.datero;
    } else if (tipoFig === "captador") {
      bruta = brutaPunta * (CAPTADOR_PCT / 100);
      etiqueta = ETIQUETA_FIGURA.captador;
    } else {
      var pctInput = form.querySelector('.figura-pct-input[data-figura="' + tipoFig + '"][data-punta="' + i + '"]');
      var pct = num(pctInput ? pctInput.value : 0);
      if (pct <= 0) return null;
      bruta = brutaPunta * (pct / 100);
      var etiquetaSpan = check.closest(".figura-check") && check.closest(".figura-check").querySelector("strong");
      etiqueta = etiquetaSpan ? etiquetaSpan.textContent : "Figura personalizada";
    }

    var ret = num(retSel ? retSel.value : 30);
    var inmo = bruta * (ret / 100);
    var agente = bruta - inmo;
    var nombre = agenteSel.options[agenteSel.selectedIndex].text;
    return { tipo: tipoFig, etiqueta: etiqueta, nombre: nombre, bruta: bruta, inmo: inmo, agente: agente };
  }

  function renderFiguras(box, figuras) {
    if (!box) return;
    if (!figuras.length) { box.innerHTML = ""; return; }
    box.innerHTML = figuras.map(function (f) {
      return '<div class="figura-fila">' +
        '<span class="figura-fila__nombre">' + f.etiqueta + ': ' + f.nombre + '</span>' +
        '<span class="figura-fila__montos">' +
          '<span><span>Bruta</span>' + money(f.bruta) + '</span>' +
          '<span><span>Inmob.</span>' + money(f.inmo) + '</span>' +
          '<span><span>Neto</span>' + money(f.agente) + '</span>' +
        '</span>' +
      '</div>';
    }).join("");
  }

  function calcularPunta(i) {
    var rep = form.querySelector('.rep-select[data-punta="' + i + '"]').value;
    var calcBox = form.querySelector('.punta__calc[data-punta="' + i + '"]');
    var figurasBox = form.querySelector('.figuras-calc[data-punta="' + i + '"]');
    if (!generaComision(rep)) {
      setOut(calcBox, 0, 0, 0, true);
      if (figurasBox) figurasBox.innerHTML = "";
      return { bruta: 0, inmo: 0, agente: 0 };
    }

    var comtipo = form.querySelector('.comtipo-select[data-punta="' + i + '"]').value;
    var baseInput = form.querySelector('.base-calc[data-punta="' + i + '"]');
    var base = baseInput.value !== "" ? num(baseInput.value) : montoOperacion();
    if (baseInput.value === "") baseInput.placeholder = montoOperacion() ? fmt.format(montoOperacion()) : "";
    var ret = num(form.querySelector('.retencion-select[data-punta="' + i + '"]').value);

    var bruta;
    if (comtipo === "MONTO_FIJO") {
      bruta = num(form.querySelector('.com-fijo[data-punta="' + i + '"]').value);
    } else {
      var pct = num(form.querySelector('.com-porcentaje[data-punta="' + i + '"]').value);
      bruta = base * (pct / 100);
    }

    // Figuras adicionales: se descuentan de la bruta ANTES de la retención
    // del agente principal; cada una deja la suya propia (Acta 001/2026).
    var figurasActivas = [];
    var brutaFiguras = 0;
    var tiposAEvaluar = esCV() ? ["datero", "captador", "aaa"].concat(TIPOS_PERSONALIZADA) : TIPOS_PERSONALIZADA;
    tiposAEvaluar.forEach(function (tipoFig) {
      var f = calcularFigura(tipoFig, i, bruta);
      if (f) { figurasActivas.push(f); brutaFiguras += f.bruta; }
    });

    var brutaPrincipal = bruta - brutaFiguras;
    var inmo = brutaPrincipal * (ret / 100);
    var agente = brutaPrincipal - inmo;

    setOut(calcBox, bruta, inmo, agente, false);
    gestionarMotivo(i, comtipo);
    renderFiguras(figurasBox, figurasActivas);

    var totInmo = inmo, totAgente = agente;
    figurasActivas.forEach(function (f) { totInmo += f.inmo; totAgente += f.agente; });

    return { bruta: bruta, inmo: totInmo, agente: totAgente };
  }

  function gestionarMotivo(i, comtipo) {
    var campoMotivo = form.querySelector('.campo-motivo[data-punta="' + i + '"]');
    var motivo = form.querySelector('.motivo[data-punta="' + i + '"]');
    var pctInput = form.querySelector('.com-porcentaje[data-punta="' + i + '"]');
    var difiere = comtipo === "PORCENTAJE" && pctInput.value !== "" &&
                  Math.abs(num(pctInput.value) - defaultPct()) > 1e-9;
    toggle(campoMotivo, difiere);
    motivo.required = difiere;
  }

  function setOut(box, bruta, inmo, agente, vacio) {
    box.querySelector(".out-bruta").textContent  = vacio ? "—" : money(bruta);
    box.querySelector(".out-inmo").textContent   = vacio ? "—" : money(inmo);
    box.querySelector(".out-agente").textContent = vacio ? "—" : money(agente);
  }

  // ---- Venta de desarrollo: una sola punta (oculta la otra) ----
  function repValor(i) {
    var s = form.querySelector('.rep-select[data-punta="' + i + '"]');
    return s ? s.value : "";
  }
  function gestionarDesarrollo() {
    var dev0 = repValor(0) === "DESARROLLO";
    var dev1 = repValor(1) === "DESARROLLO";
    // Si una punta es desarrollo, la otra se fuerza a Particular y se oculta.
    if (dev0) { var s1 = form.querySelector('.rep-select[data-punta="1"]'); if (s1.value !== "PARTICULAR") s1.value = "PARTICULAR"; }
    if (dev1) { var s0 = form.querySelector('.rep-select[data-punta="0"]'); if (s0.value !== "PARTICULAR") s0.value = "PARTICULAR"; }
    var p0 = form.querySelector('.punta[data-punta="0"]');
    var p1 = form.querySelector('.punta[data-punta="1"]');
    if (p1) p1.classList.toggle("oculto", dev0);
    if (p0) p0.classList.toggle("oculto", dev1);
    var nota = document.getElementById("nota-desarrollo");
    if (nota) nota.classList.toggle("oculto", !(dev0 || dev1));
  }

  function recalcular() {
    sincronizarTotalContrato();
    gestionarDesarrollo();
    var tot = { bruta: 0, inmo: 0, agente: 0 };
    [0, 1].forEach(function (i) {
      aplicarPunta(i);
      var r = calcularPunta(i);
      tot.bruta += r.bruta; tot.inmo += r.inmo; tot.agente += r.agente;
    });
    document.getElementById("tot-bruta").textContent  = money(tot.bruta);
    document.getElementById("tot-inmo").textContent   = money(tot.inmo);
    document.getElementById("tot-agente").textContent = money(tot.agente);
  }

  // ---- Sugerir retención al elegir un agente con título de corredor ----
  // Aplica tanto al agente principal de la punta como al de cada figura.
  form.querySelectorAll(".agente-select, .figura-agente-select").forEach(function (sel) {
    sel.addEventListener("change", function () {
      var opt = sel.options[sel.selectedIndex];
      var sug = opt && opt.dataset.retencion;
      if (!sug) return;
      var i = sel.dataset.punta;
      var retSelector = sel.classList.contains("figura-agente-select")
        ? '.figura-retencion-select[data-figura="' + sel.dataset.figura + '"][data-punta="' + i + '"]'
        : '.retencion-select[data-punta="' + i + '"]';
      var ret = form.querySelector(retSelector);
      if (!ret) return;
      Array.prototype.forEach.call(ret.options, function (o) {
        if (o.value === sug) ret.value = sug;
      });
      recalcular();
    });
  });

  // ---- Captador de desarrollo: autocompleta según lo cargado en Agentes ----
  form.querySelectorAll(".desarrollo-input").forEach(function (input) {
    input.addEventListener("input", function () {
      var i = input.dataset.punta;
      var match = CAPTADORES[input.value.trim().toLowerCase()];
      if (!match) return;
      var check = form.querySelector('.captador-check[data-punta="' + i + '"]');
      var sel = form.querySelector('.figura-agente-select[data-figura="captador"][data-punta="' + i + '"]');
      if (check) check.checked = true;
      if (sel) sel.value = String(match.agenteId);
      recalcular();
    });
  });

  function toggle(el, mostrar) { if (el) el.classList.toggle("oculto", !mostrar); }

  // ---- Listeners globales ----
  tipoSelect.addEventListener("change", aplicarTipo);
  if (monedaSelect) monedaSelect.addEventListener("change", recalcular);
  form.addEventListener("input", recalcular);
  form.addEventListener("change", recalcular);

  // Init
  aplicarTipo();
  recalcular();
})();
