const state = {
  seccionales: [],
  oficinas: [],
  empleados: [],
  semanas: [],
  dias: [],
  jornadas: [],
  modal: { type: null, id: null },
};

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

// --- Navigation ---
document.querySelectorAll("nav button[data-panel]").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll("nav button").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    const id = btn.dataset.panel;
    document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
    document.getElementById(`panel-${id}`).classList.add("active");
    if (id === "demanda") loadDemandaStatus();
    if (id === "configuracion") loadConfiguracion();
  });
});

// --- Modal ---
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
  state.modal = { type: null, id: null };
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

// --- Seccionales ---
async function loadSeccionales() {
  state.seccionales = await api("/api/seccionales");
  const tbody = document.getElementById("tbody-seccionales");
  tbody.innerHTML = state.seccionales
    .map(
      (s) => `
    <tr>
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
      const nombre = document.getElementById("f-nombre").value.trim();
      await api("/api/seccionales", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nombre }),
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
      const nombre = document.getElementById("f-nombre").value.trim();
      await api(`/api/seccionales/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nombre }),
      });
      await loadSeccionales();
      await loadOficinas();
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
      <td><strong>${o.id}</strong></td>
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

function seccionalOptions(selected) {
  return state.seccionales
    .map(
      (s) =>
        `<option value="${s.id}" ${s.id === selected ? "selected" : ""}>${escapeHtml(s.nombre)}</option>`
    )
    .join("");
}

document.getElementById("btn-new-oficina").addEventListener("click", () => {
  openModal(
    "Nueva oficina",
    `<label>Nombre</label><input id="f-nombre" type="text" />
     <label>Seccional</label><select id="f-seccional">${seccionalOptions()}</select>`,
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
    `<p class="hint">ID (para Excel): <strong>${row.id}</strong></p>
     <label>Nombre</label><input id="f-nombre" type="text" value="${escapeHtml(row.nombre)}" />
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

// --- Empleados ---
let permisosDraft = [];

function renderPermisosEditor() {
  const container = document.getElementById("permisos-container");
  if (!container) return;
  const seccionalId = +document.getElementById("f-seccional").value;
  const oficinasSec = state.oficinas.filter((o) => o.seccional_id === seccionalId);
  const diaOpts = diasActivos()
    .map((d) => `<option value="${escapeHtml(d.nombre)}">${escapeHtml(d.nombre)}</option>`)
    .join("");
  const horaSet = new Set();
  state.jornadas.forEach((j) => j.horas.forEach((h) => horaSet.add(h)));
  const horaOpts = [...horaSet].sort().map((h) => `<option value="${h}">${h}</option>`).join("");

  container.innerHTML = permisosDraft
    .map(
      (p, i) => `
    <div class="permiso-row" data-i="${i}">
      <select class="p-oficina">${oficinasSec.map((o) => `<option value="${o.id}" ${o.id === p.oficina_id ? "selected" : ""}>${escapeHtml(o.nombre)}</option>`).join("")}</select>
      <select class="p-dia">${diaOpts}</select>
      <select class="p-hora">${horaOpts}</select>
      <button type="button" class="danger p-del">Eliminar</button>
    </div>`
    )
    .join("");

  container.querySelectorAll(".permiso-row").forEach((row) => {
    const i = +row.dataset.i;
    row.querySelector(".p-dia").value = permisosDraft[i].dia;
    row.querySelector(".p-hora").value = permisosDraft[i].hora;
    row.querySelector(".p-del").addEventListener("click", () => {
      permisosDraft.splice(i, 1);
      renderPermisosEditor();
    });
  });
}

function collectPermisos() {
  const rows = document.querySelectorAll("#permisos-container .permiso-row");
  return [...rows].map((row) => ({
    oficina_id: +row.querySelector(".p-oficina").value,
    dia: row.querySelector(".p-dia").value,
    hora: row.querySelector(".p-hora").value,
  }));
}

async function loadEmpleados() {
  state.empleados = await api("/api/empleados");
  const tbody = document.getElementById("tbody-empleados");
  tbody.innerHTML = state.empleados
    .map(
      (e) => `
    <tr>
      <td>${escapeHtml(e.nombre)}</td>
      <td>${e.pago_hora}</td>
      <td>${escapeHtml(e.seccional_nombre || "")}</td>
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

function empleadoModalHtml(row) {
  return `
    <label>Nombre</label><input id="f-nombre" type="text" value="${row ? escapeHtml(row.nombre) : ""}" />
    <label>Pago por hora</label><input id="f-pago" type="number" step="0.01" min="0.01" value="${row ? row.pago_hora : ""}" />
    <label>Seccional</label><select id="f-seccional">${seccionalOptions(row ? row.seccional_id : null)}</select>
    <label>Permisos (no puede trabajar)</label>
    <div id="permisos-container"></div>
    <button type="button" class="secondary" id="btn-add-permiso">Agregar permiso</button>`;
}

document.getElementById("btn-new-empleado").addEventListener("click", () => {
  permisosDraft = [];
  openModal("Nuevo empleado", empleadoModalHtml(null), async () => {
    await api("/api/empleados", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        nombre: document.getElementById("f-nombre").value.trim(),
        pago_hora: +document.getElementById("f-pago").value,
        seccional_id: +document.getElementById("f-seccional").value,
        permisos: collectPermisos(),
      }),
    });
    await loadEmpleados();
  });
  setTimeout(() => {
    renderPermisosEditor();
    document.getElementById("f-seccional").addEventListener("change", renderPermisosEditor);
    document.getElementById("btn-add-permiso").addEventListener("click", () => {
      const sec = +document.getElementById("f-seccional").value;
      const of = state.oficinas.find((o) => o.seccional_id === sec);
      permisosDraft.push({
        oficina_id: of ? of.id : (state.oficinas[0]?.id || 1),
        dia: diasActivos()[0]?.nombre || "Lunes",
        hora: "08:00",
      });
      renderPermisosEditor();
    });
  }, 0);
});

function editEmpleado(id) {
  const row = state.empleados.find((e) => e.id === id);
  permisosDraft = row.permisos.map((p) => ({
    oficina_id: p.oficina_id,
    dia: p.dia,
    hora: p.hora,
  }));
  openModal("Editar empleado", empleadoModalHtml(row), async () => {
    await api(`/api/empleados/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        nombre: document.getElementById("f-nombre").value.trim(),
        pago_hora: +document.getElementById("f-pago").value,
        seccional_id: +document.getElementById("f-seccional").value,
        permisos: collectPermisos(),
      }),
    });
    await loadEmpleados();
  });
  setTimeout(() => {
    renderPermisosEditor();
    document.getElementById("f-seccional").addEventListener("change", renderPermisosEditor);
    document.getElementById("btn-add-permiso").addEventListener("click", () => {
      const sec = +document.getElementById("f-seccional").value;
      const of = state.oficinas.find((o) => o.seccional_id === sec);
      permisosDraft.push({
        oficina_id: of ? of.id : row.seccional_id,
        dia: diasActivos()[0]?.nombre || "Lunes",
        hora: "08:00",
      });
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
const HORAS_24 = Array.from({ length: 24 }, (_, i) => `${String(i).padStart(2, "0")}:00`);

const DIAS_SEMANA_ORDEN = [
  "Lunes",
  "Martes",
  "Miercoles",
  "Jueves",
  "Viernes",
  "Sabado",
  "Domingo",
];

function diasActivos() {
  return state.dias.filter((d) => d.activo !== false);
}

function semanasCantidadActual() {
  if (!state.semanas.length) return 1;
  const nums = state.semanas.map((s) => s.numero).sort((a, b) => a - b);
  const max = nums[nums.length - 1];
  const consecutivas =
    nums.length === max && nums.every((n, i) => n === i + 1);
  return consecutivas ? max : max;
}

function renderSemanasUi() {
  const cantidad = semanasCantidadActual();
  const input = document.getElementById("input-semanas-cantidad");
  if (input && !input.dataset.userEditing) {
    input.value = cantidad;
  }
}

function renderDiasToggles() {
  const sorted = [...state.dias].sort((a, b) => a.orden - b.orden);
  const byName = new Map(sorted.map((d) => [d.nombre, d]));
  const container = document.getElementById("dias-toggles");
  container.innerHTML = DIAS_SEMANA_ORDEN
    .map((nombre) => {
      const d = byName.get(nombre);
      if (!d) {
        return `<div class="dia-toggle-row inactive"><span class="hint">—</span><span class="dia-name">${escapeHtml(nombre)}</span></div>`;
      }
      const on = d.activo !== false;
      return `
      <div class="dia-toggle-row ${on ? "" : "inactive"}">
        <label class="toggle" title="Día activo en planificación">
          <input type="checkbox" class="toggle-dia" data-id="${d.id}" ${on ? "checked" : ""} />
          <span class="toggle-slider"></span>
        </label>
        <span class="dia-name">${escapeHtml(d.nombre)}</span>
      </div>`;
    })
    .join("");

  container.querySelectorAll(".toggle-dia").forEach((el) => {
    el.addEventListener("change", async () => {
      const id = +el.dataset.id;
      const activo = el.checked;
      try {
        await api(`/api/dias/${id}/activo`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ activo }),
        });
        const d = state.dias.find((x) => x.id === id);
        if (d) d.activo = activo;
        el.closest(".dia-toggle-row").classList.toggle("inactive", !activo);
      } catch (e) {
        el.checked = !activo;
        showGlobalError(e.message);
      }
    });
  });
}

const DEFAULT_JORNADA_HORAS = [
  "08:00",
  "09:00",
  "10:00",
  "11:00",
  "12:00",
  "13:00",
  "14:00",
  "15:00",
];

function jornadaHorasGridHtml(horasSet) {
  return HORAS_24
    .map(
      (hora) => `
    <div class="hour-cell">
      <span class="hour-label">${hora}</span>
      <label class="toggle toggle-compact" title="Hora de jornada">
        <input type="checkbox" class="toggle-hora-jornada" data-hora="${hora}" ${horasSet.has(hora) ? "checked" : ""} />
        <span class="toggle-slider"></span>
      </label>
    </div>`
    )
    .join("");
}

function jornadaAlmuerzoGridHtml(selectedHoras, almSet) {
  if (!selectedHoras.length) {
    return "";
  }
  return selectedHoras
    .map(
      (hora) => `
    <div class="hour-cell">
      <span class="hour-label">${hora}</span>
      <label class="toggle toggle-compact" title="Hora de almuerzo">
        <input type="checkbox" class="toggle-hora-almuerzo" data-hora="${hora}" ${almSet.has(hora) ? "checked" : ""} />
        <span class="toggle-slider alm"></span>
      </label>
    </div>`
    )
    .join("");
}

function getHorasJornadaFromModal() {
  const horas = [];
  document.querySelectorAll("#jornada-horas-grid .toggle-hora-jornada:checked").forEach((el) => {
    horas.push(el.dataset.hora);
  });
  horas.sort();
  return horas;
}

function getAlmuerzoSelectionFromModal() {
  const set = new Set();
  document.querySelectorAll("#jornada-almuerzos-grid .toggle-hora-almuerzo:checked").forEach((el) => {
    set.add(el.dataset.hora);
  });
  return set;
}

function refreshJornadaAlmuerzoGrid() {
  const selected = getHorasJornadaFromModal();
  const almSet = getAlmuerzoSelectionFromModal();
  const filteredAlm = new Set(selected.filter((h) => almSet.has(h)));
  const grid = document.getElementById("jornada-almuerzos-grid");
  const hint = document.getElementById("jornada-almuerzo-hint");
  if (!grid || !hint) return;
  if (!selected.length) {
    grid.innerHTML = "";
    hint.style.display = "block";
    return;
  }
  hint.style.display = "none";
  grid.innerHTML = jornadaAlmuerzoGridHtml(selected, filteredAlm);
}

function bindJornadaModalForm() {
  document.querySelectorAll("#jornada-horas-grid .toggle-hora-jornada").forEach((el) => {
    el.addEventListener("change", () => refreshJornadaAlmuerzoGrid());
  });
  refreshJornadaAlmuerzoGrid();
}

function readJornadaFromModal() {
  const nombre = document.getElementById("f-jornada-nombre").value.trim();
  const horas = getHorasJornadaFromModal();
  const almuerzos = [];
  document.querySelectorAll("#jornada-almuerzos-grid .toggle-hora-almuerzo:checked").forEach((el) => {
    almuerzos.push(el.dataset.hora);
  });
  almuerzos.sort();
  return { nombre, horas, almuerzos };
}

function jornadaFormHtml(row) {
  const horasSet = new Set(row ? row.horas : DEFAULT_JORNADA_HORAS);
  const almSet = new Set(row ? row.almuerzos : ["12:00", "13:00", "14:00"]);
  const nombre = row ? row.nombre : `Jornada${state.jornadas.length + 1}`;
  const selected = HORAS_24.filter((h) => horasSet.has(h));
  return `
    <label for="f-jornada-nombre">Nombre</label>
    <input id="f-jornada-nombre" type="text" value="${escapeHtml(nombre)}" />
    <label>Horas de jornada</label>
    <div id="jornada-horas-grid" class="hours-grid hours-grid-modal">${jornadaHorasGridHtml(horasSet)}</div>
    <label>Horas de almuerzo</label>
    <p class="hint" id="jornada-almuerzo-hint" style="${selected.length ? "display:none" : ""}">Active al menos una hora de jornada para configurar el almuerzo.</p>
    <div id="jornada-almuerzos-grid" class="hours-grid hours-grid-modal">${jornadaAlmuerzoGridHtml(selected, almSet)}</div>`;
}

function renderJornadasTable() {
  const tbodyJ = document.getElementById("tbody-jornadas");
  tbodyJ.innerHTML = state.jornadas
    .map(
      (j) => `
    <tr>
      <td>${escapeHtml(j.nombre)}</td>
      <td>${j.horas.join(", ")}</td>
      <td>${j.almuerzos.length ? j.almuerzos.join(", ") : "—"}</td>
      <td>${tableActionsHtml("btn-edit-jornada", "btn-del-jornada", j.id)}</td>
    </tr>`
    )
    .join("");
  tbodyJ.querySelectorAll(".btn-edit-jornada").forEach((b) =>
    b.addEventListener("click", () => editJornada(+b.dataset.id))
  );
  tbodyJ.querySelectorAll(".btn-del-jornada").forEach((b) =>
    b.addEventListener("click", () => deleteJornada(+b.dataset.id))
  );
}

function openJornadaModal(title, row, onSubmit) {
  openModal(title, jornadaFormHtml(row), async () => {
    const { nombre, horas, almuerzos } = readJornadaFromModal();
    if (!nombre) throw new Error("El nombre es obligatorio.");
    if (!horas.length) throw new Error("La jornada debe tener al menos una hora activa.");
    await onSubmit({ nombre, horas, almuerzos });
    await loadJornadasPanel();
  }, { wide: true });
  setTimeout(() => bindJornadaModalForm(), 0);
}

function editJornada(id) {
  const row = state.jornadas.find((j) => j.id === id);
  openJornadaModal("Editar jornada", row, (body) =>
    api(`/api/jornadas/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
  );
}

async function loadJornadasPanel() {
  state.semanas = await api("/api/semanas");
  state.dias = await api("/api/dias");
  state.jornadas = await api("/api/jornadas");
  renderSemanasUi();
  renderDiasToggles();
  renderJornadasTable();
}

const inputSemanasCantidad = document.getElementById("input-semanas-cantidad");
inputSemanasCantidad.addEventListener("focus", () => {
  inputSemanasCantidad.dataset.userEditing = "1";
});
inputSemanasCantidad.addEventListener("blur", () => {
  delete inputSemanasCantidad.dataset.userEditing;
});

document.getElementById("btn-apply-semanas").addEventListener("click", async () => {
  const n = +inputSemanasCantidad.value;
  if (!n || n < 1) {
    showGlobalError("Indique un número de semanas válido (mínimo 1).");
    return;
  }
  try {
    showGlobalError(null);
    state.semanas = await api("/api/semanas/sync", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cantidad: n }),
    });
    delete inputSemanasCantidad.dataset.userEditing;
    renderSemanasUi();
  } catch (e) {
    showGlobalError(e.message);
  }
});

document.getElementById("btn-new-jornada").addEventListener("click", () => {
  openJornadaModal("Nueva jornada", null, (body) =>
    api("/api/jornadas", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
  );
});

async function deleteJornada(id) {
  if (!confirm("¿Eliminar jornada?")) return;
  try {
    await api(`/api/jornadas/${id}`, { method: "DELETE" });
    await loadJornadasPanel();
  } catch (e) {
    showGlobalError(e.message);
  }
}

// --- Configuración avanzada ---
function readIntField(id, label, min, max) {
  const raw = document.getElementById(id).value;
  const value = Number(raw);
  if (!Number.isInteger(value)) {
    throw new Error(`${label} debe ser un número entero.`);
  }
  if (value < min || value > max) {
    throw new Error(`${label} debe estar entre ${min} y ${max}.`);
  }
  return value;
}

function fillConfiguracionForm(cfg) {
  document.getElementById("cfg-penalizacion-subpersonal").value = cfg.penalizacion_subpersonal;
  document.getElementById("cfg-penalizacion-sobrepersonal").value = cfg.penalizacion_sobrepersonal;
  document.getElementById("cfg-penalizacion-funcionario").value = cfg.penalizacion_funcionario_utilizado;
  document.getElementById("cfg-max-horas-semanales").value = cfg.max_horas_semanales;
  document.getElementById("cfg-solver-time-limit").value = cfg.solver_time_limit;
}

async function loadConfiguracion() {
  const cfg = await api("/api/configuracion");
  fillConfiguracionForm(cfg);
  const status = document.getElementById("config-save-status");
  if (status) status.textContent = "";
}

document.getElementById("form-configuracion").addEventListener("submit", async (e) => {
  e.preventDefault();
  const status = document.getElementById("config-save-status");
  status.textContent = "";
  try {
    const body = {
      penalizacion_subpersonal: readIntField(
        "cfg-penalizacion-subpersonal",
        "Penalización por personal insuficiente",
        0,
        1_000_000_000
      ),
      penalizacion_sobrepersonal: readIntField(
        "cfg-penalizacion-sobrepersonal",
        "Penalización por personal de más",
        0,
        1_000_000_000
      ),
      penalizacion_funcionario_utilizado: readIntField(
        "cfg-penalizacion-funcionario",
        "Penalización por funcionario utilizado",
        0,
        1_000_000_000
      ),
      max_horas_semanales: readIntField(
        "cfg-max-horas-semanales",
        "Máximo de horas semanales",
        1,
        168
      ),
      solver_time_limit: readIntField(
        "cfg-solver-time-limit",
        "Tiempo máximo de cálculo",
        1,
        86400
      ),
    };
    const saved = await api("/api/configuracion", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    fillConfiguracionForm(saved);
    showGlobalError(null);
    status.textContent = "Cambios guardados.";
  } catch (err) {
    showGlobalError(err.message);
  }
});

// --- Demanda ---
async function loadDemandaStatus() {
  const st = await api("/api/demanda/status");
  const el = document.getElementById("demanda-status");
  if (!st.has_file) {
    el.innerHTML = "<p>No hay archivo cargado.</p>";
    return;
  }
  el.innerHTML = `<p><strong>Archivo:</strong> ${escapeHtml(st.filename)}</p>
    <p><strong>Subido:</strong> ${st.uploaded_at ? new Date(st.uploaded_at).toLocaleString() : ""}</p>`;
}

document.getElementById("form-demanda").addEventListener("submit", async (e) => {
  e.preventDefault();
  const file = document.getElementById("file-demanda").files[0];
  if (!file) return;
  const fd = new FormData();
  fd.append("file", file);
  try {
    await fetch("/api/demanda/upload", { method: "POST", body: fd }).then(async (res) => {
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Error al subir");
      return data;
    });
    showGlobalError(null);
    await loadDemandaStatus();
    alert("Archivo cargado correctamente.");
  } catch (err) {
    showGlobalError(err.message);
  }
});

// --- Simulación ---
function renderSimResults(data) {
  const out = document.getElementById("sim-output");
  let html = "";

  if (data.errors && data.errors.length) {
    html += `<div class="error-banner"><strong>Errores de validación / ejecución</strong><ul>${data.errors.map((e) => `<li>${escapeHtml(e)}</li>`).join("")}</ul></div>`;
  }
  if (data.warnings && data.warnings.length) {
    html += `<div class="warning-banner"><ul>${data.warnings.map((w) => `<li>${escapeHtml(w)}</li>`).join("")}</ul></div>`;
  }

  const r = data.results;
  if (!r) {
    out.innerHTML = html;
    return;
  }

  html += `<div class="card"><p><strong>Estado del solver:</strong> ${escapeHtml(r.estado)}</p>`;
  if (r.resumen) {
    const res = r.resumen;
    html += `<p>Costo nómina: ${res.costo_nomina != null ? "$" + res.costo_nomina.toFixed(2) : "—"}</p>`;
    html += `<p>Penalización demanda: ${res.penalizacion_demanda != null ? "$" + res.penalizacion_demanda.toFixed(2) : "—"}</p>`;
    html += `<p>Función objetivo: ${res.valor_objetivo != null ? "$" + res.valor_objetivo.toFixed(2) : "—"}</p>`;
  }
  html += `</div>`;

  if (r.diagnostico_capacidad && r.diagnostico_capacidad.length) {
    html += `<details open><summary>Diagnóstico de capacidad</summary><table><thead><tr><th>Seccional</th><th>Funcionarios</th><th>Oficinas</th><th>Capacidad (h)</th><th>Demanda (h)</th></tr></thead><tbody>`;
    r.diagnostico_capacidad.forEach((d) => {
      html += `<tr><td>${escapeHtml(d.seccional)}</td><td>${d.funcionarios}</td><td>${(d.oficinas || []).join(", ")}</td><td>${d.capacidad_maxima_horas}</td><td>${d.demanda_horas}</td></tr>`;
    });
    html += `</tbody></table></details>`;
  }

  if (r.causas_posibles) {
    html += `<div class="warning-banner"><strong>Posibles causas</strong><ul>${r.causas_posibles.map((c) => `<li>${escapeHtml(c)}</li>`).join("")}</ul></div>`;
  }

  if (r.oficinas) {
    html += `<details open><summary>Resultados por oficina</summary>`;
    r.oficinas.forEach((of) => {
      html += `<details><summary>Oficina ${of.id}</summary>`;
      of.semanas.forEach((sem) => {
        html += `<details><summary>Semana ${sem.numero}</summary>`;
        sem.dias.forEach((dia) => {
          html += `<details><summary>${escapeHtml(dia.nombre)}</summary>`;
          html += `<table><thead><tr><th>Hora</th><th>Requerido</th><th>Activos</th><th>Almorzando</th></tr></thead><tbody>`;
          dia.horas.forEach((h) => {
            html += `<tr><td>${h.hora}</td><td>${h.requerido}</td><td>${escapeHtml((h.activos || []).join(", "))}</td><td>${escapeHtml((h.almorzando || []).join(", "))}</td></tr>`;
          });
          html += `</tbody></table>`;
          if (dia.horas_por_empleado.length) {
            html += `<p><strong>Horas en el día:</strong></p><ul>${dia.horas_por_empleado.map((x) => `<li>${escapeHtml(x.empleado)}: ${x.horas} h</li>`).join("")}</ul>`;
          }
          if (dia.descanso_compensatorio && dia.descanso_compensatorio.length) {
            html += `<p><strong>Descanso compensatorio:</strong> ${dia.descanso_compensatorio.map(escapeHtml).join(", ")}</p>`;
          }
          html += `</details>`;
        });
        if (sem.totales_semana && sem.totales_semana.length) {
          html += `<p><strong>Total semana:</strong> ${sem.total_general} h</p><ul>${sem.totales_semana.map((t) => `<li>${escapeHtml(t.empleado)}: ${t.horas} h</li>`).join("")}</ul>`;
        }
        html += `</details>`;
      });
      if (of.totales_quincena && of.totales_quincena.length) {
        html += `<p><strong>Total quincena oficina:</strong> ${of.total_quincena} h</p>`;
      }
      html += `</details>`;
    });
    html += `</details>`;
  }

  if (r.cumplimiento_demanda && r.cumplimiento_demanda.length) {
    html += `<details><summary>Cumplimiento de demanda (desviaciones)</summary><table><thead><tr><th>Oficina</th><th>Semana</th><th>Día</th><th>Hora</th><th>Faltante</th><th>Sobrante</th></tr></thead><tbody>`;
    r.cumplimiento_demanda.forEach((c) => {
      html += `<tr><td>${c.oficina}</td><td>${c.semana}</td><td>${escapeHtml(c.dia)}</td><td>${c.hora}</td><td>${c.faltante}</td><td>${c.sobrante}</td></tr>`;
    });
    html += `</tbody></table></details>`;
  } else if (r.estado === "Optimal" || r.estado === "Feasible") {
    html += `<div class="success-banner">La demanda mínima se cumple en todas las oficinas y horas.</div>`;
  }

  if (r.totales_empleado && r.totales_empleado.length) {
    html += `<details><summary>Total horas por empleado (todas las oficinas)</summary><ul>${r.totales_empleado.map((t) => `<li>${escapeHtml(t.empleado)}: ${t.horas} h</li>`).join("")}</ul></details>`;
  }

  out.innerHTML = html;
}

document.getElementById("btn-run-sim").addEventListener("click", async () => {
  const loading = document.getElementById("sim-loading");
  loading.style.display = "inline";
  document.getElementById("sim-output").innerHTML = "";
  showGlobalError(null);
  try {
    const data = await api("/api/simulacion/ejecutar", { method: "POST" });
    renderSimResults(data);
  } catch (e) {
    showGlobalError(e.message);
  } finally {
    loading.style.display = "none";
  }
});

// --- Init ---
async function init() {
  try {
    await loadSeccionales();
    await loadOficinas();
    await loadEmpleados();
    await loadJornadasPanel();
    await loadConfiguracion();
    await loadDemandaStatus();
  } catch (e) {
    showGlobalError(e.message);
  }
}

init();
