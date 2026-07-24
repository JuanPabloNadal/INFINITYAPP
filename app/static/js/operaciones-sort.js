/* Ordenamiento client-side de la tabla de Operaciones.
   Clic en un encabezado ordena por esa columna; un segundo clic invierte el
   orden. No recarga la página ni pisa los filtros aplicados: solo reordena
   las filas ya presentes en el DOM. */
(function () {
  "use strict";

  var tabla = document.querySelector(".tabla-wrap table.tabla");
  if (!tabla || !tabla.tHead || !tabla.tBodies.length) return;

  var ths = [].slice.call(tabla.tHead.querySelectorAll("th[data-sort-key]"));
  var tbody = tabla.tBodies[0];
  if (!ths.length) return;

  var estado = { key: null, dir: 1 };

  function indiceColumna(th) {
    return [].indexOf.call(th.parentNode.children, th);
  }

  function valorDeFila(tr, colIndex) {
    var td = tr.children[colIndex];
    if (!td) return "";
    var v = td.getAttribute("data-sort");
    return v !== null ? v : td.textContent.trim();
  }

  function comparar(a, b, tipo) {
    if (tipo === "number") {
      return parseFloat(a || "0") - parseFloat(b || "0");
    }
    if (tipo === "date") {
      return a < b ? -1 : a > b ? 1 : 0;
    }
    return a.localeCompare(b, "es");
  }

  function marcarActivo(thActivo, dir) {
    ths.forEach(function (th) {
      th.classList.remove("activo");
      var ico = th.querySelector(".sort-ico");
      if (ico) ico.textContent = "↕";
      th.removeAttribute("aria-sort");
    });
    thActivo.classList.add("activo");
    var icoActivo = thActivo.querySelector(".sort-ico");
    if (icoActivo) icoActivo.textContent = dir === 1 ? "↑" : "↓";
    thActivo.setAttribute("aria-sort", dir === 1 ? "ascending" : "descending");
  }

  function ordenarPor(th) {
    var key = th.dataset.sortKey;
    var tipo = th.dataset.sortType || "text";
    var colIndex = indiceColumna(th);

    var dir;
    if (estado.key === key) {
      dir = estado.dir * -1;
    } else {
      dir = th.dataset.sortDefault === "desc" ? -1 : 1;
    }
    estado = { key: key, dir: dir };

    var filas = [].slice.call(tbody.rows);
    filas.sort(function (ra, rb) {
      return comparar(valorDeFila(ra, colIndex), valorDeFila(rb, colIndex), tipo) * dir;
    });
    filas.forEach(function (tr) { tbody.appendChild(tr); });
    marcarActivo(th, dir);
  }

  ths.forEach(function (th) {
    var texto = th.textContent.trim();
    th.textContent = "";
    th.classList.add("th-sortable");
    th.setAttribute("tabindex", "0");
    th.setAttribute("role", "button");
    th.setAttribute("aria-label", "Ordenar por " + texto);

    var span = document.createElement("span");
    span.textContent = texto;
    var ico = document.createElement("span");
    ico.className = "sort-ico";
    ico.setAttribute("aria-hidden", "true");
    ico.textContent = "↕";

    th.appendChild(span);
    th.appendChild(ico);

    th.addEventListener("click", function () { ordenarPor(th); });
    th.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        ordenarPor(th);
      }
    });
  });
})();
