const state = {
  seccionales: [],
  oficinas: [],
  servicios: [],
  empleados: [],
  jornadas: [],
  demandaOffset: 0,
  demandaPageSize: 200,
  demandaTotal: 0,
  simResults: {},
  modal: { onSave: null },
};

const DIAS_SEMANA = [
  { num: 1, nombre: "Lunes", corto: "Lun" },
  { num: 2, nombre: "Martes", corto: "Mar" },
  { num: 3, nombre: "Miércoles", corto: "Mié" },
  { num: 4, nombre: "Jueves", corto: "Jue" },
  { num: 5, nombre: "Viernes", corto: "Vie" },
  { num: 6, nombre: "Sábado", corto: "Sáb" },
  { num: 7, nombre: "Domingo", corto: "Dom" },
];

const SLOTS_30 = [];
for (let h = 0; h < 24; h++) {
  SLOTS_30.push(`${String(h).padStart(2, "0")}:00`);
  SLOTS_30.push(`${String(h).padStart(2, "0")}:30`);
}

function diaNombre(num) {
  const d = DIAS_SEMANA.find((x) => x.num === num);
  return d ? d.nombre : String(num);
}

function diaCorto(num) {
  const d = DIAS_SEMANA.find((x) => x.num === num);
  return d ? d.corto : String(num);
}

function modoHorasNombre(modo) {
  if (modo === "fixed") return "Fijo";
  if (modo === "flexible") return "Flexible";
  return modo;
}

function showGlobalError(msg) {
  const el = document.getElementById("global-error");
  if (!msg) {
    el.style.display = "none";
    el.textContent = "";
    return;
  }
  el.style.display = "block";
  el.textContent = msg;
}

async function api(path, options = {}) {
  const res = await fetch(path, options);
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = data.detail;
    const msg = Array.isArray(detail)
      ? detail.map((d) => d.msg || JSON.stringify(d)).join("; ")
      : detail || res.statusText;
    throw new Error(msg);
  }
  return data;
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function tableActionsHtml(editBtnClass, delBtnClass, id) {
  return `<div class="table-actions">
        <button type="button" class="secondary ${editBtnClass}" data-id="${id}">Editar</button>
        <button type="button" class="danger ${delBtnClass}" data-id="${id}">Eliminar</button>
      </div>`;
}

document.querySelectorAll("nav button[data-panel]").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll("nav button").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    const id = btn.dataset.panel;
    document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
    document.getElementById(`panel-${id}`).classList.add("active");
    if (id === "demanda") loadDemandaTable();
  });
});

const overlay = document.getElementById("modal-overlay");
const modalEl = overlay.querySelector(".modal");
const modalTitle = document.getElementById("modal-title");
const modalBody = document.getElementById("modal-body");

function openModal(title, bodyHtml, onSave, options = {}) {
  modalTitle.textContent = title;
  modalBody.innerHTML = bodyHtml;
  modalEl.classList.toggle("modal-wide", !!options.wide);
  overlay.classList.add("open");
  overlay.setAttribute("aria-hidden", "false");
  state.modal.onSave = onSave;
}

function closeModal() {
  overlay.classList.remove("open");
  overlay.setAttribute("aria-hidden", "true");
  modalEl.classList.remove("modal-wide");
  state.modal.onSave = null;
}

document.getElementById("modal-cancel").addEventListener("click", closeModal);
document.getElementById("modal-save").addEventListener("click", async () => {
  try {
    if (state.modal.onSave) await state.modal.onSave();
    closeModal();
    showGlobalError(null);
  } catch (e) {
    showGlobalError(e.message);
  }
});
overlay.addEventListener("click", (e) => {
  if (e.target === overlay) closeModal();
});

function seccionalOptions(selected) {
  return state.seccionales
    .map(
      (s) =>
        `<option value="${s.id}" ${s.id === selected ? "selected" : ""}>${escapeHtml(s.nombre)}</option>`
    )
    .join("");
}

function servicioOptions(seccionalId, selected) {
  return state.servicios
    .filter((s) => s.seccional_id === seccionalId)
    .map(
      (s) =>
        `<option value="${s.id}" ${s.id === selected ? "selected" : ""}>${escapeHtml(s.nombre)}</option>`
    )
    .join("");
}

function oficinaOptions(selected) {
  return state.oficinas
    .map(
      (o) =>
        `<option value="${o.id}" ${o.id === selected ? "selected" : ""}>${escapeHtml(o.nombre)} (${escapeHtml(o.seccional_nombre || "")})</option>`
    )
    .join("");
}

// --- Seccionales ---
async function loadSeccionales() {
  state.seccionales = await api("/api/seccionales");
  const tbody = document.getElementById("tbody-seccionales");
  tbody.innerHTML = state.seccionales
    .map(
      (s) => `
    <tr>
      <td>${s.id}</td>
      <td>${escapeHtml(s.nombre)}</td>
      <td>${tableActionsHtml("btn-edit-seccional", "btn-del-seccional", s.id)}</td>
    </tr>`
    )
    .join("");
  tbody.querySelectorAll(".btn-edit-seccional").forEach((b) =>
    b.addEventListener("click", () => editSeccional(+b.dataset.id))
  );
  tbody.querySelectorAll(".btn-del-seccional").forEach((b) =>
    b.addEventListener("click", () => deleteSeccional(+b.dataset.id))
  );
}

document.getElementById("btn-new-seccional").addEventListener("click", () => {
  openModal(
    "Nueva seccional",
    `<label>Nombre</label><input id="f-nombre" type="text" />`,
    async () => {
      await api("/api/seccionales", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nombre: document.getElementById("f-nombre").value.trim() }),
      });
      await loadSeccionales();
    }
  );
});

function editSeccional(id) {
  const row = state.seccionales.find((s) => s.id === id);
  openModal(
    "Editar seccional",
    `<label>Nombre</label><input id="f-nombre" type="text" value="${escapeHtml(row.nombre)}" />`,
    async () => {
      await api(`/api/seccionales/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nombre: document.getElementById("f-nombre").value.trim() }),
      });
      await loadSeccionales();
      await loadOficinas();
      await loadServicios();
      await loadEmpleados();
    }
  );
}

async function deleteSeccional(id) {
  if (!confirm("¿Eliminar esta seccional?")) return;
  try {
    await api(`/api/seccionales/${id}`, { method: "DELETE" });
    await loadSeccionales();
  } catch (e) {
    showGlobalError(e.message);
  }
}

// --- Oficinas ---
async function loadOficinas() {
  state.oficinas = await api("/api/oficinas");
  const tbody = document.getElementById("tbody-oficinas");
  tbody.innerHTML = state.oficinas
    .map(
      (o) => `
    <tr>
      <td>${o.id}</td>
      <td>${escapeHtml(o.nombre)}</td>
      <td>${escapeHtml(o.seccional_nombre || "")}</td>
      <td>${tableActionsHtml("btn-edit-oficina", "btn-del-oficina", o.id)}</td>
    </tr>`
    )
    .join("");
  tbody.querySelectorAll(".btn-edit-oficina").forEach((b) =>
    b.addEventListener("click", () => editOficina(+b.dataset.id))
  );
  tbody.querySelectorAll(".btn-del-oficina").forEach((b) =>
    b.addEventListener("click", () => deleteOficina(+b.dataset.id))
  );
}

document.getElementById("btn-new-oficina").addEventListener("click", () => {
  openModal(
    "Nueva oficina",
    `<label>Nombre</label><input id="f-nombre" type="text" />
     <label>Seccional</label><select id="f-seccional">${seccionalOptions(null)}</select>`,
    async () => {
      await api("/api/oficinas", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nombre: document.getElementById("f-nombre").value.trim(),
          seccional_id: +document.getElementById("f-seccional").value,
        }),
      });
      await loadOficinas();
    }
  );
});

function editOficina(id) {
  const row = state.oficinas.find((o) => o.id === id);
  openModal(
    "Editar oficina",
    `<label>Nombre</label><input id="f-nombre" type="text" value="${escapeHtml(row.nombre)}" />
     <label>Seccional</label><select id="f-seccional">${seccionalOptions(row.seccional_id)}</select>`,
    async () => {
      await api(`/api/oficinas/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nombre: document.getElementById("f-nombre").value.trim(),
          seccional_id: +document.getElementById("f-seccional").value,
        }),
      });
      await loadOficinas();
      await loadJornadas();
    }
  );
}

async function deleteOficina(id) {
  if (!confirm("¿Eliminar esta oficina?")) return;
  try {
    await api(`/api/oficinas/${id}`, { method: "DELETE" });
    await loadOficinas();
  } catch (e) {
    showGlobalError(e.message);
  }
}

// --- Servicios ---
async function loadServicios() {
  state.servicios = await api("/api/servicios");
  const tbody = document.getElementById("tbody-servicios");
  tbody.innerHTML = state.servicios
    .map(
      (s) => `
    <tr>
      <td>${s.id}</td>
      <td>${escapeHtml(s.nombre)}</td>
      <td>${escapeHtml(s.seccional_nombre || "")}</td>
      <td>${tableActionsHtml("btn-edit-servicio", "btn-del-servicio", s.id)}</td>
    </tr>`
    )
    .join("");
  tbody.querySelectorAll(".btn-edit-servicio").forEach((b) =>
    b.addEventListener("click", () => editServicio(+b.dataset.id))
  );
  tbody.querySelectorAll(".btn-del-servicio").forEach((b) =>
    b.addEventListener("click", () => deleteServicio(+b.dataset.id))
  );
}

document.getElementById("btn-new-servicio").addEventListener("click", () => {
  openModal(
    "Nuevo servicio",
    `<label>Nombre</label><input id="f-nombre" type="text" />
     <label>Seccional</label><select id="f-seccional">${seccionalOptions(state.seccionales[0]?.id)}</select>`,
    async () => {
      await api("/api/servicios", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nombre: document.getElementById("f-nombre").value.trim(),
          seccional_id: +document.getElementById("f-seccional").value,
        }),
      });
      await loadServicios();
    }
  );
});

function editServicio(id) {
  const row = state.servicios.find((s) => s.id === id);
  openModal(
    "Editar servicio",
    `<label>Nombre</label><input id="f-nombre" type="text" value="${escapeHtml(row.nombre)}" />
     <label>Seccional</label><select id="f-seccional">${seccionalOptions(row.seccional_id)}</select>`,
    async () => {
      await api(`/api/servicios/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nombre: document.getElementById("f-nombre").value.trim(),
          seccional_id: +document.getElementById("f-seccional").value,
        }),
      });
      await loadServicios();
      await loadEmpleados();
    }
  );
}

async function deleteServicio(id) {
  if (!confirm("¿Eliminar este servicio?")) return;
  try {
    await api(`/api/servicios/${id}`, { method: "DELETE" });
    await loadServicios();
  } catch (e) {
    showGlobalError(e.message);
  }
}

// --- Empleados ---
let permisosDraft = [];

function renderPermisosEditor() {
  const container = document.getElementById("permisos-container");
  if (!container) return;
  const diaOpts = DIAS_SEMANA.map((d) => `<option value="${d.num}">${d.nombre}</option>`).join("");
  const horaOpts = SLOTS_30.map((h) => `<option value="${h}">${h}</option>`).join("");

  container.innerHTML = permisosDraft
    .map(
      (p, i) => `
    <div class="permiso-row" data-i="${i}">
      <select class="p-tipo">
        <option value="dia_completo" ${p.tipo === "dia_completo" ? "selected" : ""}>Día completo</option>
        <option value="horas" ${p.tipo === "horas" ? "selected" : ""}>Por horas</option>
      </select>
      <select class="p-dia">${diaOpts}</select>
      <select class="p-ini" ${p.tipo === "dia_completo" ? "disabled" : ""}>${horaOpts}</select>
      <select class="p-fin" ${p.tipo === "dia_completo" ? "disabled" : ""}>${horaOpts}</select>
      <button type="button" class="danger p-del">Eliminar</button>
    </div>`
    )
    .join("");

  container.querySelectorAll(".permiso-row").forEach((row) => {
    const i = +row.dataset.i;
    row.querySelector(".p-dia").value = String(permisosDraft[i].dia);
    if (permisosDraft[i].hora_inicio) row.querySelector(".p-ini").value = permisosDraft[i].hora_inicio;
    if (permisosDraft[i].hora_fin) row.querySelector(".p-fin").value = permisosDraft[i].hora_fin;
    row.querySelector(".p-tipo").addEventListener("change", (e) => {
      const horas = e.target.value === "horas";
      row.querySelector(".p-ini").disabled = !horas;
      row.querySelector(".p-fin").disabled = !horas;
    });
    row.querySelector(".p-del").addEventListener("click", () => {
      permisosDraft.splice(i, 1);
      renderPermisosEditor();
    });
  });
}

function collectPermisos() {
  const rows = document.querySelectorAll("#permisos-container .permiso-row");
  return [...rows].map((row) => {
    const tipo = row.querySelector(".p-tipo").value;
    const base = {
      tipo,
      dia: +row.querySelector(".p-dia").value,
    };
    if (tipo === "horas") {
      base.hora_inicio = row.querySelector(".p-ini").value;
      base.hora_fin = row.querySelector(".p-fin").value;
    }
    return base;
  });
}

function bindEmpleadoModalServicios() {
  const secEl = document.getElementById("f-seccional");
  const srvEl = document.getElementById("f-servicio");
  const refresh = () => {
    const secId = +secEl.value;
    srvEl.innerHTML = servicioOptions(secId, +srvEl.value || null);
    if (!srvEl.value && srvEl.options.length) srvEl.selectedIndex = 0;
  };
  secEl.addEventListener("change", refresh);
  refresh();
  const modoEl = document.getElementById("f-modo");
  const holguraWrap = document.getElementById("holgura-wrap");
  modoEl.addEventListener("change", () => {
    holguraWrap.style.display = modoEl.value === "flexible" ? "block" : "none";
  });
}

function empleadoModalHtml(row) {
  const descOpts = DIAS_SEMANA.map(
    (d) => `<option value="${d.num}" ${row && row.dia_descanso === d.num ? "selected" : ""}>${d.nombre}</option>`
  ).join("");
  const secId = row ? row.seccional_id : state.seccionales[0]?.id;
  const modo = row ? row.modo_horas : "fixed";
  const holguraPct = row ? Math.round(row.holgura_pct * 100) : 0;
  return `
    <label>Nombre</label><input id="f-nombre" type="text" value="${row ? escapeHtml(row.nombre) : ""}" />
    <label>Horas semanales</label><input id="f-horas" type="number" step="0.5" min="0.5" value="${row ? row.horas_semanales : 40}" />
    <label>Día de descanso</label><select id="f-descanso">${descOpts}</select>
    <label>Modo de horas</label>
    <select id="f-modo">
      <option value="fixed" ${modo === "fixed" ? "selected" : ""}>Fijo</option>
      <option value="flexible" ${modo === "flexible" ? "selected" : ""}>Flexible</option>
    </select>
    <div id="holgura-wrap" style="display:${modo === "flexible" ? "block" : "none"}">
      <label>Holgura (%)</label><input id="f-holgura" type="number" min="0" step="1" value="${holguraPct}" />
    </div>
    <label>Seccional</label><select id="f-seccional">${seccionalOptions(secId)}</select>
    <label>Servicio</label><select id="f-servicio"></select>
    <label>Permisos</label>
    <div id="permisos-container"></div>
    <button type="button" class="secondary" id="btn-add-permiso">Agregar permiso</button>`;
}

function readEmpleadoBody() {
  const modo = document.getElementById("f-modo").value;
  const holgura = modo === "flexible" ? +document.getElementById("f-holgura").value / 100 : 0;
  return {
    nombre: document.getElementById("f-nombre").value.trim(),
    horas_semanales: +document.getElementById("f-horas").value,
    dia_descanso: +document.getElementById("f-descanso").value,
    modo_horas: modo,
    holgura_pct: holgura,
    seccional_id: +document.getElementById("f-seccional").value,
    servicio_id: +document.getElementById("f-servicio").value,
    permisos: collectPermisos(),
  };
}

async function loadEmpleados() {
  state.empleados = await api("/api/empleados");
  const tbody = document.getElementById("tbody-empleados");
  tbody.innerHTML = state.empleados
    .map(
      (e) => `
    <tr>
      <td>${e.id}</td>
      <td>${escapeHtml(e.nombre)}</td>
      <td>${e.horas_semanales}</td>
      <td>${diaNombre(e.dia_descanso)}</td>
      <td>${modoHorasNombre(e.modo_horas)}${e.modo_horas === "flexible" ? ` (+${Math.round(e.holgura_pct * 100)}%)` : ""}</td>
      <td>${escapeHtml(e.seccional_nombre || "")}</td>
      <td>${escapeHtml(e.servicio_nombre || "")}</td>
      <td>${e.permisos.length}</td>
      <td>${tableActionsHtml("btn-edit-empleado", "btn-del-empleado", e.id)}</td>
    </tr>`
    )
    .join("");
  tbody.querySelectorAll(".btn-edit-empleado").forEach((b) =>
    b.addEventListener("click", () => editEmpleado(+b.dataset.id))
  );
  tbody.querySelectorAll(".btn-del-empleado").forEach((b) =>
    b.addEventListener("click", () => deleteEmpleado(+b.dataset.id))
  );
}

document.getElementById("btn-new-empleado").addEventListener("click", () => {
  permisosDraft = [];
  openModal("Nuevo empleado", empleadoModalHtml(null), async () => {
    await api("/api/empleados", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(readEmpleadoBody()),
    });
    await loadEmpleados();
  });
  setTimeout(() => {
    bindEmpleadoModalServicios();
    if (state.empleados.length) {
      const srv = document.getElementById("f-servicio");
      const sec = +document.getElementById("f-seccional").value;
      srv.innerHTML = servicioOptions(sec, null);
    }
    renderPermisosEditor();
    document.getElementById("btn-add-permiso").addEventListener("click", () => {
      permisosDraft.push({ tipo: "dia_completo", dia: 1 });
      renderPermisosEditor();
    });
  }, 0);
});

function editEmpleado(id) {
  const row = state.empleados.find((e) => e.id === id);
  permisosDraft = row.permisos.map((p) => ({
    tipo: p.tipo,
    dia: p.dia,
    hora_inicio: p.hora_inicio,
    hora_fin: p.hora_fin,
  }));
  openModal("Editar empleado", empleadoModalHtml(row), async () => {
    await api(`/api/empleados/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(readEmpleadoBody()),
    });
    await loadEmpleados();
  });
  setTimeout(() => {
    bindEmpleadoModalServicios();
    document.getElementById("f-servicio").value = String(row.servicio_id);
    renderPermisosEditor();
    document.getElementById("btn-add-permiso").addEventListener("click", () => {
      permisosDraft.push({ tipo: "dia_completo", dia: 1 });
      renderPermisosEditor();
    });
  }, 0);
}

async function deleteEmpleado(id) {
  if (!confirm("¿Eliminar este empleado?")) return;
  try {
    await api(`/api/empleados/${id}`, { method: "DELETE" });
    await loadEmpleados();
  } catch (e) {
    showGlobalError(e.message);
  }
}

// --- Jornadas ---
function jornadaDiasTogglesHtml(selectedDays) {
  const set = new Set(selectedDays || []);
  return `<div class="dias-grid">${DIAS_SEMANA
    .map(
      (d) => `
    <div class="dia-toggle-row">
      <label class="toggle" title="${d.nombre}">
        <input type="checkbox" class="toggle-jornada-dia" data-dia="${d.num}" ${set.has(d.num) ? "checked" : ""} />
        <span class="toggle-slider"></span>
      </label>
      <span class="dia-name">${d.nombre}</span>
    </div>`
    )
    .join("")}</div>`;
}

function timeSelectOptions(id, value) {
  const opts = SLOTS_30.concat(["24:00"])
    .map((t) => `<option value="${t}" ${t === value ? "selected" : ""}>${t}</option>`)
    .join("");
  return `<select id="${id}">${opts}</select>`;
}

function jornadaFormHtml(row) {
  const ini = row ? row.inicio : "08:00";
  const fin = row ? row.fin : "17:00";
  const bi = row?.break_inicio || "";
  const bf = row?.break_fin || "";
  return `
    <label>Oficina</label><select id="f-oficina">${oficinaOptions(row ? row.oficina_id : null)}</select>
    <label>Inicio</label>${timeSelectOptions("f-inicio", ini)}
    <label>Fin</label>${timeSelectOptions("f-fin", fin)}
    <label>Inicio descanso (opcional)</label>
    <select id="f-break-ini"><option value="">—</option>${SLOTS_30.map((t) => `<option value="${t}" ${t === bi ? "selected" : ""}>${t}</option>`).join("")}</select>
    <label>Fin descanso (opcional)</label>
    <select id="f-break-fin"><option value="">—</option>${SLOTS_30.map((t) => `<option value="${t}" ${t === bf ? "selected" : ""}>${t}</option>`).join("")}</select>
    <label>Días que aplica</label>
    ${jornadaDiasTogglesHtml(row ? row.dias : [1, 2, 3, 4, 5, 6])}`;
}

function readJornadaBody() {
  const dias = [];
  document.querySelectorAll(".toggle-jornada-dia:checked").forEach((el) => {
    dias.push(+el.dataset.dia);
  });
  if (!dias.length) throw new Error("Seleccione al menos un día.");
  const bi = document.getElementById("f-break-ini").value;
  const bf = document.getElementById("f-break-fin").value;
  return {
    oficina_id: +document.getElementById("f-oficina").value,
    inicio: document.getElementById("f-inicio").value,
    fin: document.getElementById("f-fin").value,
    break_inicio: bi || null,
    break_fin: bf || null,
    dias,
  };
}

function formatJornadaDias(dias) {
  return dias.map((d) => diaNombre(d)).join(", ");
}

async function loadJornadas() {
  state.jornadas = await api("/api/jornadas");
  const tbody = document.getElementById("tbody-jornadas");
  tbody.innerHTML = state.jornadas
    .map((j) => {
      const brk =
        j.break_inicio && j.break_fin ? `${j.break_inicio}–${j.break_fin}` : "—";
      return `
    <tr>
      <td>${j.id}</td>
      <td>${escapeHtml(j.oficina_nombre || "")}</td>
      <td>${escapeHtml(j.seccional_nombre || "")}</td>
      <td>${j.inicio}–${j.fin}</td>
      <td>${brk}</td>
      <td>${formatJornadaDias(j.dias)}</td>
      <td>${tableActionsHtml("btn-edit-jornada", "btn-del-jornada", j.id)}</td>
    </tr>`;
    })
    .join("");
  tbody.querySelectorAll(".btn-edit-jornada").forEach((b) =>
    b.addEventListener("click", () => editJornada(+b.dataset.id))
  );
  tbody.querySelectorAll(".btn-del-jornada").forEach((b) =>
    b.addEventListener("click", () => deleteJornada(+b.dataset.id))
  );
}

document.getElementById("btn-new-jornada").addEventListener("click", () => {
  openModal(
    "Nueva jornada",
    jornadaFormHtml(null),
    async () => {
      await api("/api/jornadas", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(readJornadaBody()),
      });
      await loadJornadas();
    },
    { wide: true }
  );
});

function editJornada(id) {
  const row = state.jornadas.find((j) => j.id === id);
  openModal(
    "Editar jornada",
    jornadaFormHtml(row),
    async () => {
      await api(`/api/jornadas/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(readJornadaBody()),
      });
      await loadJornadas();
    },
    { wide: true }
  );
}

async function deleteJornada(id) {
  if (!confirm("¿Eliminar jornada?")) return;
  try {
    await api(`/api/jornadas/${id}`, { method: "DELETE" });
    await loadJornadas();
  } catch (e) {
    showGlobalError(e.message);
  }
}

// --- Demanda ---
const DEMANDA_COLS = ["Seccional", "Oficina", "Servicio", "Semana", "Dia", "Hora", "Demanda"];

function normalizeHeader(h) {
  return String(h || "").trim().toLowerCase().replace(/\s+/g, "");
}

function parseExcelDemanda(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = new Uint8Array(e.target.result);
        const wb = XLSX.read(data, { type: "array" });
        const sheet = wb.Sheets[wb.SheetNames[0]];
        const rows = XLSX.utils.sheet_to_json(sheet, { defval: "" });
        if (!rows.length) {
          reject(new Error("El archivo no tiene filas."));
          return;
        }
        const keys = Object.keys(rows[0]);
        const keyMap = {};
        keys.forEach((k) => {
          const n = normalizeHeader(k);
          if (n === "seccional") keyMap.seccional = k;
          if (n === "oficina") keyMap.oficina = k;
          if (n === "servicio") keyMap.servicio = k;
          if (n === "semana") keyMap.semana = k;
          if (n === "dia" || n === "día") keyMap.dia = k;
          if (n === "hora") keyMap.hora = k;
          if (n === "demanda" || n === "requerido") keyMap.demanda = k;
        });
        const missing = DEMANDA_COLS.filter((c) => {
          const n = normalizeHeader(c);
          if (n === "dia" || n === "día") return !keyMap.dia;
          if (n === "demanda") return !keyMap.demanda;
          return !keyMap[n];
        });
        if (missing.length) {
          reject(new Error(`Faltan columnas: ${missing.join(", ")}`));
          return;
        }
        const filas = rows.map((row) => {
          let hora = row[keyMap.hora];
          if (typeof hora === "number" && hora < 1) {
            const mins = Math.round(hora * 24 * 60);
            const hh = Math.floor(mins / 60) % 24;
            const mm = mins % 60;
            hora = `${String(hh).padStart(2, "0")}:${String(mm).padStart(2, "0")}`;
          } else if (hora instanceof Date) {
            hora = `${String(hora.getHours()).padStart(2, "0")}:${String(hora.getMinutes()).padStart(2, "0")}`;
          } else {
            hora = String(hora).trim();
          }
          return {
            seccional: String(row[keyMap.seccional]).trim(),
            oficina: String(row[keyMap.oficina]).trim(),
            servicio: String(row[keyMap.servicio]).trim(),
            semana: parseInt(row[keyMap.semana], 10),
            dia: row[keyMap.dia],
            hora,
            demanda: parseInt(row[keyMap.demanda], 10),
          };
        });
        resolve(filas);
      } catch (err) {
        reject(err);
      }
    };
    reader.onerror = () => reject(new Error("No se pudo leer el archivo."));
    reader.readAsArrayBuffer(file);
  });
}

async function loadDemandaTable() {
  const data = await api(
    `/api/demanda?offset=${state.demandaOffset}&limit=${state.demandaPageSize}`
  );
  state.demandaTotal = data.total;
  const tbody = document.getElementById("tbody-demanda");
  tbody.innerHTML = data.filas
    .map(
      (f) => `
    <tr>
      <td>${escapeHtml(f.seccional)}</td>
      <td>${escapeHtml(f.oficina)}</td>
      <td>${escapeHtml(f.servicio)}</td>
      <td>${f.semana}</td>
      <td>${diaNombre(f.dia)}</td>
      <td>${f.hora}</td>
      <td>${f.demanda}</td>
    </tr>`
    )
    .join("");
  document.getElementById("demanda-total").textContent = `Total: ${data.total} filas`;
  const from = data.total ? state.demandaOffset + 1 : 0;
  const to = Math.min(state.demandaOffset + data.filas.length, data.total);
  document.getElementById("demanda-page-info").textContent =
    data.total ? `${from}–${to} de ${data.total}` : "Sin datos";
  document.getElementById("btn-demanda-prev").disabled = state.demandaOffset <= 0;
  document.getElementById("btn-demanda-next").disabled =
    state.demandaOffset + state.demandaPageSize >= data.total;
  const st = document.getElementById("demanda-status");
  st.innerHTML = data.total
    ? `<p><strong>${data.total}</strong> registros de demanda en base de datos.</p>`
    : "<p>No hay demanda cargada.</p>";
}

document.getElementById("btn-demanda-prev").addEventListener("click", async () => {
  state.demandaOffset = Math.max(0, state.demandaOffset - state.demandaPageSize);
  await loadDemandaTable();
});

document.getElementById("btn-demanda-next").addEventListener("click", async () => {
  state.demandaOffset += state.demandaPageSize;
  await loadDemandaTable();
});

document.getElementById("form-demanda").addEventListener("submit", async (e) => {
  e.preventDefault();
  const file = document.getElementById("file-demanda").files[0];
  if (!file) return;
  const errEl = document.getElementById("demanda-errors");
  errEl.style.display = "none";
  try {
    const filas = await parseExcelDemanda(file);
    const result = await api("/api/demanda", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filas }),
    });
    if (result.errors && result.errors.length) {
      errEl.style.display = "block";
      errEl.innerHTML = `<strong>Errores de validación</strong><ul>${result.errors
        .slice(0, 100)
        .map((x) => `<li>${escapeHtml(x)}</li>`)
        .join("")}</ul>`;
      if (result.errors.length > 100) {
        errEl.innerHTML += `<p class="hint">… y ${result.errors.length - 100} más.</p>`;
      }
      return;
    }
    showGlobalError(null);
    state.demandaOffset = 0;
    await loadDemandaTable();
    alert(`Demanda guardada: ${result.count} filas.`);
  } catch (err) {
    showGlobalError(err.message);
  }
});

// --- Simulación SSE ---
function simKey(seccional, semana, servicio) {
  return `${seccional}|${semana}|${servicio}`;
}

function ensureSimNode(tree, seccional, semana, servicio) {
  if (!tree[seccional]) tree[seccional] = {};
  if (!tree[seccional][semana]) tree[seccional][semana] = {};
  if (!tree[seccional][semana][servicio]) {
    tree[seccional][semana][servicio] = {
      employee_hours: [],
      offices: {},
    };
  }
  return tree[seccional][semana][servicio];
}

const coverageCharts = [];
const coverageSeriesById = new Map();
let coverageChartSeq = 0;

function destroyCoverageCharts() {
  coverageCharts.splice(0).forEach((chart) => chart.destroy());
  coverageSeriesById.clear();
  coverageChartSeq = 0;
}

function parseSlotMinutes(hhmm) {
  const [h, m] = String(hhmm).split(":").map((n) => parseInt(n, 10));
  return h * 60 + m;
}

function formatMinutes(mins) {
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

function buildCoverageTimeline(coverage) {
  const byKey = new Map();
  let minMin = Infinity;
  let maxMin = -Infinity;
  const days = new Set();
  coverage.forEach((row) => {
    const dia = Number(row.dia);
    const mins = parseSlotMinutes(row.slot_inicio);
    if (!Number.isFinite(dia) || !Number.isFinite(mins)) return;
    days.add(dia);
    if (mins < minMin) minMin = mins;
    if (mins > maxMin) maxMin = mins;
    byKey.set(`${dia}|${mins}`, row);
  });

  const labels = [];
  const demanda = [];
  const asignados = [];
  const titles = [];
  [...days]
    .sort((a, b) => a - b)
    .forEach((dia, dayIndex) => {
      if (dayIndex > 0) {
        labels.push(null);
        demanda.push(null);
        asignados.push(null);
        titles.push("");
      }
      for (let mins = minMin; mins <= maxMin; mins += 30) {
        const row = byKey.get(`${dia}|${mins}`);
        const hora = formatMinutes(mins);
        labels.push([diaCorto(dia), hora]);
        demanda.push(row ? Number(row.demanda) : 0);
        asignados.push(row ? Number(row.asignados) : 0);
        titles.push(`${diaNombre(dia)} ${hora}`);
      }
    });
  return { labels, demanda, asignados, titles };
}

function coverageDayGroups(labels) {
  const groups = [];
  let start = null;
  labels.forEach((label, index) => {
    if (!Array.isArray(label)) {
      if (start != null) groups.push({ start, end: index - 1, day: labels[start][0] });
      start = null;
      return;
    }
    if (start == null) start = index;
  });
  if (start != null) groups.push({ start, end: labels.length - 1, day: labels[start][0] });
  return groups;
}

const coverageTimelinePlugin = {
  id: "coverageTimeline",
  beforeDatasetsDraw(chart) {
    const { ctx, chartArea, scales } = chart;
    if (!chartArea) return;
    const x = scales.x;
    const labels = chart.data.labels || [];
    const groups = coverageDayGroups(labels);
    if (!groups.length) return;
    const slot = Math.abs(x.getPixelForValue(1) - x.getPixelForValue(0)) || 0;
    ctx.save();
    groups.forEach((group, index) => {
      if (index % 2 === 0) return;
      const left = x.getPixelForValue(group.start) - slot / 2;
      const right = x.getPixelForValue(group.end) + slot / 2;
      ctx.fillStyle = "rgba(15, 23, 42, 0.045)";
      //ctx.fillRect(left, chartArea.top, right - left, chartArea.bottom - chartArea.top);
    });
    ctx.restore();
  },
  afterDraw(chart) {
    const { ctx, chartArea, scales } = chart;
    if (!chartArea) return;
    const x = scales.x;
    const labels = chart.data.labels || [];
    const groups = coverageDayGroups(labels);
    if (!groups.length) return;
    const slot = Math.abs(x.getPixelForValue(1) - x.getPixelForValue(0)) || 0;
    const dayWidth = (chartArea.right - chartArea.left) / groups.length;
    const showHours = dayWidth >= 150;
    ctx.save();
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    groups.forEach((group) => {
      const left = x.getPixelForValue(group.start) - slot / 2;
      const right = x.getPixelForValue(group.end) + slot / 2;
      ctx.font = "600 12px Roboto, sans-serif";
      ctx.fillStyle = "#0f172a";
      //ctx.fillText(group.day, (left + right) / 2, chartArea.bottom + (showHours ? 16 : 4));
      if (!showHours) return;
      ctx.font = "11px Roboto, sans-serif";
      ctx.fillStyle = "#64748b";
      /*for (let index = group.start; index <= group.end; index += 1) {
        const label = labels[index];
        if (!Array.isArray(label)) continue;
        const time = label[1];
        if (time !== "08:00" && time !== "12:00" && time !== "16:00") continue;
        ctx.fillText(time, x.getPixelForValue(index), chartArea.bottom + 2);
      }*/
    });
    ctx.restore();
  },
};

function createCoverageChart(canvas, series) {
  const chart = new Chart(canvas, {
    type: "line",
    data: {
      labels: series.labels,
      datasets: [
        {
          label: "Demanda",
          data: series.demanda,
          borderColor: "#dc2626",
          backgroundColor: "#dc2626",
          borderWidth: 1,
          pointRadius: 1,
          pointHoverRadius: 2,
          pointHoverBackgroundColor: "#dc2626",
          tension: 0,
          spanGaps: false,
        },
        {
          label: "Asignados",
          data: series.asignados,
          borderColor: "#111111",
          backgroundColor: "#111111",
          borderWidth: 1,
          pointRadius: 1,
          pointHoverRadius: 2,
          pointHoverBackgroundColor: "#111111",
          tension: 0,
          spanGaps: false,
        },
      ],
    },
    plugins: [coverageTimelinePlugin],
    options: {
      responsive: true,
      maintainAspectRatio: false,
      layout: { padding: { bottom: 32 } },
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: {
          position: "top",
          labels: { boxWidth: 28, boxHeight: 3, color: "#0f172a" },
        },
        tooltip: {
          callbacks: {
            title(items) {
              const idx = items[0] && items[0].dataIndex;
              return series.titles[idx] || "";
            },
          },
        },
      },
      scales: {
        x: {
          ticks: { display: true },
          /*grid: {
            color(ctx) {
              const label = series.labels[ctx.index];
              const prev = series.labels[ctx.index - 1];
              if (!Array.isArray(label)) return "rgba(15, 23, 42, 0.2)";
              if (!Array.isArray(prev) || prev[0] !== label[0]) return "rgba(15, 23, 42, 0.2)";
              if (label[1] === "12:00") return "rgba(148, 163, 184, 0.35)";
              return "transparent";
            },
          },*/
          border: { display: false },
        },
        y: {
          beginAtZero: true,
          ticks: { precision: 0, color: "#334155" },
          title: { display: true, text: "Personas", color: "#334155" },
          grid: { color: "rgba(148, 163, 184, 0.28)" },
        },
      },
    },
  });
  coverageCharts.push(chart);
}

function mountCoverageCanvas(canvas) {
  if (canvas.dataset.chartReady === "1" || canvas.offsetParent === null) return;
  const series = coverageSeriesById.get(canvas.id);
  if (!series || typeof Chart === "undefined") return;
  canvas.dataset.chartReady = "1";
  createCoverageChart(canvas, series);
}

function mountVisibleCoverageCharts(root) {
  (root || document).querySelectorAll("canvas.coverage-canvas").forEach(mountCoverageCanvas);
}

function renderSimOutput() {
  destroyCoverageCharts();
  const out = document.getElementById("sim-output");
  let html = "";
  const tree = state.simResults;
  const seccionales = Object.keys(tree).sort();
  if (!seccionales.length) {
    out.innerHTML = "";
    return;
  }
  seccionales.forEach((sec) => {
    html += `<details open class="sim-block"><summary><strong>Seccional:</strong> ${escapeHtml(sec)}</summary>`;
    const semanas = Object.keys(tree[sec]).sort((a, b) => +a - +b);
    semanas.forEach((sem) => {
      html += `<details open><summary><strong>Semana</strong> ${sem}</summary>`;
      const servicios = Object.keys(tree[sec][sem]).sort();
      servicios.forEach((srv) => {
        const node = tree[sec][sem][srv];
        html += `<details open><summary><strong>Servicio:</strong> ${escapeHtml(srv)}`;
        if (node.status) html += ` <span class="hint">(${escapeHtml(node.status)})</span>`;
        html += `</summary>`;

        if (node.employee_hours && node.employee_hours.length) {
          html += `<h4>Horas por empleado</h4><table><thead><tr>
            <th>Empleado</th><th>Modo</th><th>Solicitadas</th><th>Objetivo</th><th>Asignadas</th><th>Descanso</th>
          </tr></thead><tbody>`;
          node.employee_hours.forEach((h) => {
            html += `<tr>
              <td>${escapeHtml(h.empleado)}</td>
              <td>${escapeHtml(modoHorasNombre(h.modo_horas))}</td>
              <td>${h.horas_solicitadas_min}–${h.horas_solicitadas_max}</td>
              <td>${h.horas_objetivo_min}–${h.horas_objetivo_max}</td>
              <td>${h.horas_asignadas_efectivas}</td>
              <td>${escapeHtml(h.dia_descanso_nombre || diaNombre(h.dia_descanso))}</td>
            </tr>`;
          });
          html += `</tbody></table>`;
        }

        const oficinas = Object.keys(node.offices).sort();
        oficinas.forEach((of) => {
          const block = node.offices[of];
          html += `<details><summary><strong>Oficina:</strong> ${escapeHtml(of)}</summary>`;
          if (block.schedule && block.schedule.length) {
            html += `<h4>Horario</h4><table><thead><tr>
              <th>Empleado</th><th>Día</th><th>Inicio</th><th>Fin</th><th>Descanso</th><th>Horas efectivas</th>
            </tr></thead><tbody>`;
            block.schedule.forEach((r) => {
              const brk =
                r.inicio_descanso && r.fin_descanso
                  ? `${r.inicio_descanso}–${r.fin_descanso}`
                  : "—";
              html += `<tr>
                <td>${escapeHtml(r.empleado)}</td>
                <td>${escapeHtml(r.dia_nombre || diaNombre(r.dia))}</td>
                <td>${r.inicio}</td><td>${r.fin}</td><td>${brk}</td>
                <td>${r.horas_efectivas_contabilizadas}</td>
              </tr>`;
            });
            html += `</tbody></table>`;
          }
          if (block.coverage && block.coverage.length) {
            const chartId = `coverage-chart-${coverageChartSeq++}`;
            coverageSeriesById.set(chartId, buildCoverageTimeline(block.coverage));
            html += `<h4>Cobertura</h4><div class="coverage-chart"><canvas id="${chartId}" class="coverage-canvas"></canvas></div>`;
          }
          html += `</details>`;
        });
        html += `</details>`;
      });
      html += `</details>`;
    });
    html += `</details>`;
  });
  out.innerHTML = html;
  mountVisibleCoverageCharts(out);
}

document.getElementById("sim-output").addEventListener(
  "toggle",
  (event) => {
    const details = event.target;
    if (!(details instanceof HTMLDetailsElement) || !details.open) return;
    requestAnimationFrame(() => mountVisibleCoverageCharts(details));
  },
  true
);

function ingestSimResult(payload) {
  const node = ensureSimNode(
    state.simResults,
    payload.seccional,
    payload.semana,
    payload.servicio
  );
  node.status = payload.status;
  node.employee_hours = payload.employee_hours || [];
  (payload.schedule || []).forEach((row) => {
    const of = row.oficina;
    if (!node.offices[of]) node.offices[of] = { schedule: [], coverage: [] };
    node.offices[of].schedule.push(row);
  });
  (payload.coverage || []).forEach((row) => {
    const of = row.oficina;
    if (!node.offices[of]) node.offices[of] = { schedule: [], coverage: [] };
    node.offices[of].coverage.push(row);
  });
  renderSimOutput();
}

let simRunning = false;

document.getElementById("btn-run-sim").addEventListener("click", async () => {
  if (simRunning) return;
  simRunning = true;
  const btn = document.getElementById("btn-run-sim");
  const progress = document.getElementById("sim-progress");
  btn.disabled = true;
  state.simResults = {};
  document.getElementById("sim-output").innerHTML = "";
  showGlobalError(null);
  progress.textContent = "Iniciando…";

  try {
    const res = await fetch("/api/simulacion/stream");
    if (!res.ok) throw new Error(res.statusText);
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop();
      for (const chunk of parts) {
        const lines = chunk.split("\n");
        let event = "message";
        let dataLine = "";
        lines.forEach((line) => {
          if (line.startsWith("event: ")) event = line.slice(7);
          if (line.startsWith("data: ")) dataLine = line.slice(6);
        });
        if (!dataLine) continue;
        const data = JSON.parse(dataLine);
        if (event === "progress") {
          progress.textContent = `Resolviendo ${data.index} de ${data.total}: ${data.seccional}, semana ${data.semana}, ${data.servicio}`;
        } else if (event === "result") {
          ingestSimResult(data);
        } else if (event === "error") {
          if (data.message && !data.seccional) {
            showGlobalError(data.message);
          } else {
            const msg = `${data.seccional} / semana ${data.semana} / ${data.servicio}: ${data.message}`;
            const out = document.getElementById("sim-output");
            out.insertAdjacentHTML(
              "afterbegin",
              `<div class="warning-banner">${escapeHtml(msg)}</div>`
            );
          }
        } else if (event === "done") {
          progress.textContent = `Completado: ${data.ok} ok, ${data.failed} con error (total ${data.total}).`;
        }
      }
    }
  } catch (e) {
    showGlobalError(e.message);
    progress.textContent = "";
  } finally {
    simRunning = false;
    btn.disabled = false;
  }
});

async function init() {
  try {
    await loadSeccionales();
    await loadOficinas();
    await loadServicios();
    await loadEmpleados();
    await loadJornadas();
    await loadDemandaTable();
  } catch (e) {
    showGlobalError(e.message);
  }
}

init();
