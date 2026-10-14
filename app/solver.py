"""Motor de optimización extraído de wfp.py."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pulp

from app.config_loader import SolverConfig

PENALIZACION_SUBPERSONAL = 5000
PENALIZACION_SOBREPERSONAL = 1
PENALIZACION_FUNCIONARIO_UTILIZADO = 1000
MAX_HORAS_SEMANALES = 40
SOLVER_TIME_LIMIT = 120


def _normalize_hora(valor_hora: Any, fila_excel: int) -> tuple[str | None, str | None]:
    try:
        if hasattr(valor_hora, "strftime"):
            return valor_hora.strftime("%H:%M"), None
        if isinstance(valor_hora, (int, float)):
            minutos_totales = round(float(valor_hora) * 24 * 60)
            horas_enteras = (minutos_totales // 60) % 24
            minutos = minutos_totales % 60
            return f"{horas_enteras:02d}:{minutos:02d}", None
        hora = pd.to_datetime(str(valor_hora).strip(), errors="raise").strftime(
            "%H:%M"
        )
        return hora, None
    except Exception as error:
        return None, (
            f"No se pudo interpretar la hora de la fila {fila_excel}: "
            f"{valor_hora}. Error: {error}"
        )


def load_demanda_from_excel(
    archivo: Path, config: SolverConfig
) -> tuple[dict | None, list[int] | None, list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if not archivo.is_file():
        return None, None, ["No hay archivo de demanda cargado."]

    try:
        df_demanda = pd.read_excel(archivo, sheet_name="Demanda")
    except Exception as e:
        return None, None, [f"No se pudo leer el Excel: {e}"]

    df_demanda.columns = [str(c).strip() for c in df_demanda.columns]
    columnas_requeridas = {"IDOficina", "Semana", "Dia", "Hora", "Requerido"}
    faltantes = columnas_requeridas - set(df_demanda.columns)
    if faltantes:
        return None, None, [
            "Faltan columnas en la hoja Demanda: " + ", ".join(sorted(faltantes))
        ]

    if df_demanda.columns[0] != "IDOficina":
        return None, None, [
            "La primera columna de la hoja Demanda debe llamarse 'IDOficina'."
        ]

    if not config.semanas:
        return None, None, ["Debe configurar al menos una semana."]
    if not config.dias:
        return None, None, ["Debe configurar al menos un día."]
    if not config.jornadas:
        return None, None, ["Debe configurar al menos una jornada."]
    if not config.horas_del_dia:
        return None, None, ["No hay horas del día (revise las jornadas)."]
    if not config.empleados:
        return None, None, ["Debe registrar al menos un empleado."]

    semanas = config.semanas
    dias = config.dias
    horas_del_dia = config.horas_del_dia
    demanda_por_hora: dict[tuple, int] = {}

    for indice, fila in df_demanda.iterrows():
        fila_num = int(indice) + 2
        for col in ("IDOficina", "Semana", "Dia", "Hora", "Requerido"):
            if pd.isna(fila[col]):
                errors.append(f"La fila {fila_num} tiene '{col}' vacío.")
        if errors:
            continue

        id_oficina = int(fila["IDOficina"])
        semana = int(fila["Semana"])
        dia = str(fila["Dia"]).strip()
        hora, err_h = _normalize_hora(fila["Hora"], fila_num)
        if err_h:
            errors.append(err_h)
            continue
        requerido = int(fila["Requerido"])

        if id_oficina < 0:
            errors.append(f"Fila {fila_num}: IDOficina negativo.")
            continue
        if id_oficina not in config.oficinas_registradas:
            errors.append(
                f"Fila {fila_num}: IDOficina {id_oficina} no está registrado en oficinas."
            )
            continue
        if semana not in semanas:
            errors.append(
                f"Fila {fila_num}: Semana {semana} no configurada (válidas: {semanas})."
            )
            continue
        if dia not in dias:
            errors.append(
                f"Fila {fila_num}: Día '{dia}' no válido (válidos: {dias})."
            )
            continue
        if hora not in horas_del_dia:
            errors.append(
                f"Fila {fila_num}: Hora '{hora}' no válida (válidas: {horas_del_dia})."
            )
            continue
        if requerido < 0:
            errors.append(f"Fila {fila_num}: Requerido negativo.")
            continue

        clave = (id_oficina, semana, dia, hora)
        if clave in demanda_por_hora:
            errors.append(
                f"Combinación duplicada: IDOficina={id_oficina}, Semana={semana}, "
                f"Día={dia}, Hora={hora}"
            )
            continue
        demanda_por_hora[clave] = requerido

    if errors:
        return None, None, errors

    oficinas = sorted(df_demanda["IDOficina"].astype(int).unique().tolist())
    if not oficinas:
        return None, None, ["No se encontraron oficinas en IDOficina."]

    oficinas_sin_seccional = [
        o for o in oficinas if o not in config.seccional_por_oficina
    ]
    if oficinas_sin_seccional:
        return None, None, [
            "Oficinas en Excel sin seccional: "
            + ", ".join(str(o) for o in oficinas_sin_seccional)
        ]

    seccionales_sin_funcionarios = sorted(
        {
            config.seccional_por_oficina[o]
            for o in oficinas
            if config.seccional_por_oficina[o]
            not in config.funcionarios_por_seccional
        }
    )
    if seccionales_sin_funcionarios:
        return None, None, [
            "Seccionales sin funcionarios: " + ", ".join(seccionales_sin_funcionarios)
        ]

    funcionarios_desconocidos = sorted(
        {
            emp
            for lista in config.funcionarios_por_seccional.values()
            for emp in lista
            if emp not in config.empleados
        }
    )
    if funcionarios_desconocidos:
        return None, None, [
            "Funcionarios en seccional no listados como empleados: "
            + ", ".join(funcionarios_desconocidos)
        ]

    combinaciones_faltantes = []
    for o in oficinas:
        for s in semanas:
            for d in dias:
                for h in horas_del_dia:
                    if (o, s, d, h) not in demanda_por_hora:
                        combinaciones_faltantes.append((o, s, d, h))

    if combinaciones_faltantes:
        lines = [
            f"  - IDOficina={o}, Semana={s}, Día={d}, Hora={h}"
            for o, s, d, h in combinaciones_faltantes[:50]
        ]
        extra = ""
        if len(combinaciones_faltantes) > 50:
            extra = f"\n  ... y {len(combinaciones_faltantes) - 50} más."
        return None, None, [
            "Faltan combinaciones de demanda:\n" + "\n".join(lines) + extra
        ]

    for datos_permiso in config.permiso_laboral:
        id_oficina_permiso = datos_permiso[0]
        if id_oficina_permiso not in oficinas:
            return None, None, [
                f"Permiso laboral referencia IDOficina {id_oficina_permiso} "
                "que no está en el Excel."
            ]

    return demanda_por_hora, oficinas, warnings


def _build_and_solve(
    config: SolverConfig,
    demanda_por_hora: dict,
    oficinas: list[int],
) -> dict[str, Any]:
    empleados = config.empleados
    semanas = config.semanas
    dias = config.dias
    jornadas = config.jornadas
    horas_del_dia = config.horas_del_dia
    horas_por_jornada = config.horas_por_jornada
    almuerzos_permitidos = config.almuerzos_permitidos
    permiso_laboral = config.permiso_laboral
    pago_hora = config.pago_hora
    seccional_por_oficina = config.seccional_por_oficina
    funcionarios_por_seccional = config.funcionarios_por_seccional

    horas_efectivas_jornada = {
        j: (
            len(horas_por_jornada[j]) - 1
            if j in almuerzos_permitidos
            else len(horas_por_jornada[j])
        )
        for j in jornadas
    }

    warnings: list[str] = []
    diagnostico_capacidad = []

    for seccional, lista_funcionarios in funcionarios_por_seccional.items():
        oficinas_seccional = [
            o for o in oficinas if seccional_por_oficina.get(o) == seccional
        ]
        item = {
            "seccional": seccional,
            "funcionarios": len(lista_funcionarios),
            "oficinas": oficinas_seccional,
        }
        if not oficinas_seccional:
            warnings.append(f"{seccional} no tiene oficinas asociadas en la demanda.")
        capacidad_maxima = len(lista_funcionarios) * MAX_HORAS_SEMANALES
        demanda_total = sum(
            demanda_por_hora[o, s, d, h]
            for o in oficinas_seccional
            for s in semanas
            for d in dias
            for h in horas_del_dia
        )
        item["capacidad_maxima_horas"] = capacidad_maxima
        item["demanda_horas"] = demanda_total
        if demanda_total > capacidad_maxima:
            item["imposible"] = True
            item["faltan_horas"] = demanda_total - capacidad_maxima
            warnings.append(
                f"Seccional {seccional}: demanda ({demanda_total} h) supera "
                f"capacidad ({capacidad_maxima} h)."
            )
        diagnostico_capacidad.append(item)

    prob = pulp.LpProblem("Optimizacion_Personal", pulp.LpMinimize)

    asignado = pulp.LpVariable.dicts(
        "Asig",
        (
            (o, emp, s, d, j)
            for o in oficinas
            for emp in empleados
            for s in semanas
            for d in dias
            for j in jornadas
        ),
        cat="Binary",
    )

    almuerzo = pulp.LpVariable.dicts(
        "Alm",
        (
            (o, emp, s, d, j, h)
            for o in oficinas
            for emp in empleados
            for s in semanas
            for d in dias
            for j in jornadas
            for h in almuerzos_permitidos.get(j, [])
        ),
        cat="Binary",
    )

    sub_personal = pulp.LpVariable.dicts(
        "SubPersonal",
        ((o, s, d, h) for o in oficinas for s in semanas for d in dias for h in horas_del_dia),
        lowBound=0,
        cat="Continuous",
    )

    sobre_personal = pulp.LpVariable.dicts(
        "SobrePersonal",
        ((o, s, d, h) for o in oficinas for s in semanas for d in dias for h in horas_del_dia),
        lowBound=0,
        cat="Continuous",
    )

    funcionario_utilizado = pulp.LpVariable.dicts(
        "FuncionarioUtilizado", empleados, cat="Binary"
    )

    costo_nomina = pulp.lpSum(
        asignado[o, emp, s, d, j]
        * horas_efectivas_jornada[j]
        * pago_hora[emp]
        for o in oficinas
        for emp in empleados
        for s in semanas
        for d in dias
        for j in jornadas
    )

    penalizacion_demanda = pulp.lpSum(
        sub_personal[o, s, d, h] * PENALIZACION_SUBPERSONAL
        + sobre_personal[o, s, d, h] * PENALIZACION_SOBREPERSONAL
        for o in oficinas
        for s in semanas
        for d in dias
        for h in horas_del_dia
    )

    penalizacion_funcionarios = pulp.lpSum(
        funcionario_utilizado[emp] * PENALIZACION_FUNCIONARIO_UTILIZADO
        for emp in empleados
    )

    prob += costo_nomina + penalizacion_demanda + penalizacion_funcionarios

    for o in oficinas:
        seccional_oficina = seccional_por_oficina[o]
        funcionarios_autorizados = set(
            funcionarios_por_seccional.get(seccional_oficina, [])
        )
        for emp in empleados:
            if emp not in funcionarios_autorizados:
                for s in semanas:
                    for d in dias:
                        for j in jornadas:
                            prob += asignado[o, emp, s, d, j] == 0

    for o in oficinas:
        for s in semanas:
            for d in dias:
                for emp in empleados:
                    for j in jornadas:
                        if j in almuerzos_permitidos:
                            prob += (
                                pulp.lpSum(
                                    almuerzo[o, emp, s, d, j, h]
                                    for h in almuerzos_permitidos[j]
                                )
                                == asignado[o, emp, s, d, j]
                            )

                for h in horas_del_dia:
                    empleados_en_turno = []
                    empleados_almorzando = []
                    for emp in empleados:
                        for j in jornadas:
                            horas_de_esta_jornada = horas_por_jornada.get(j, [])
                            if h in horas_de_esta_jornada:
                                empleados_en_turno.append(
                                    asignado[o, emp, s, d, j]
                                )
                            if h in almuerzos_permitidos.get(j, []):
                                empleados_almorzando.append(
                                    almuerzo[o, emp, s, d, j, h]
                                )
                    presencia_real = (
                        pulp.lpSum(empleados_en_turno)
                        - pulp.lpSum(empleados_almorzando)
                    )
                    prob += (
                        presencia_real
                        + sub_personal[o, s, d, h]
                        - sobre_personal[o, s, d, h]
                        == demanda_por_hora[(o, s, d, h)]
                    )

    for s in semanas:
        for d in dias:
            for emp in empleados:
                prob += (
                    pulp.lpSum(
                        asignado[o, emp, s, d, j]
                        for o in oficinas
                        for j in jornadas
                    )
                    <= 1
                )

    for s in semanas:
        for emp in empleados:
            prob += (
                pulp.lpSum(
                    asignado[o, emp, s, d, j] * horas_efectivas_jornada[j]
                    for o in oficinas
                    for d in dias
                    for j in jornadas
                )
                <= MAX_HORAS_SEMANALES
            )

    for emp in empleados:
        for o in oficinas:
            for s in semanas:
                for d in dias:
                    for j in jornadas:
                        prob += asignado[o, emp, s, d, j] <= funcionario_utilizado[emp]

    for indice_semana in range(len(semanas) - 1):
        semana_actual = semanas[indice_semana]
        semana_siguiente = semanas[indice_semana + 1]
        for emp in empleados:
            trabajo_domingo = pulp.lpSum(
                asignado[o, emp, semana_actual, "Domingo", j]
                for o in oficinas
                for j in jornadas
            )
            dias_trabajados_semana_siguiente = pulp.lpSum(
                asignado[o, emp, semana_siguiente, d, j]
                for o in oficinas
                for d in dias
                if d != "Domingo"
                for j in jornadas
            )
            prob += dias_trabajados_semana_siguiente <= 6 - trabajo_domingo

    for datos_permiso, permiso in permiso_laboral.items():
        id_oficina_permiso, emp_permiso, dia_permiso, hora_permiso = datos_permiso
        if permiso == 0:
            for s in semanas:
                for j in jornadas:
                    horas_de_esta_jornada = horas_por_jornada.get(j, [])
                    if hora_permiso in horas_de_esta_jornada:
                        prob += (
                            asignado[
                                id_oficina_permiso,
                                emp_permiso,
                                s,
                                dia_permiso,
                                j,
                            ]
                            == 0
                        )

    for s in semanas:
        for emp in empleados:
            for i in range(len(dias) - 1):
                dia_anterior = dias[i]
                dia_siguiente = dias[i + 1]
                for o_anterior in oficinas:
                    for j_anterior in jornadas:
                        horas_jornada_anterior = horas_por_jornada.get(
                            j_anterior, []
                        )
                        if horas_jornada_anterior:
                            hora_fin_anterior = int(
                                horas_jornada_anterior[-1].split(":")[0]
                            )
                            if hora_fin_anterior >= 16:
                                for o_siguiente in oficinas:
                                    for j_siguiente in jornadas:
                                        horas_jornada_siguiente = horas_por_jornada.get(
                                            j_siguiente, []
                                        )
                                        if horas_jornada_siguiente:
                                            hora_inicio_siguiente = int(
                                                horas_jornada_siguiente[0].split(":")[0]
                                            )
                                            if hora_inicio_siguiente == 8:
                                                prob += (
                                                    asignado[
                                                        o_anterior,
                                                        emp,
                                                        s,
                                                        dia_anterior,
                                                        j_anterior,
                                                    ]
                                                    + asignado[
                                                        o_siguiente,
                                                        emp,
                                                        s,
                                                        dia_siguiente,
                                                        j_siguiente,
                                                    ]
                                                    <= 1
                                                )

    prob.solve(pulp.PULP_CBC_CMD(msg=False, timeLimit=SOLVER_TIME_LIMIT))
    estado_solucion = pulp.LpStatus[prob.status]

    resultado: dict[str, Any] = {
        "estado": estado_solucion,
        "diagnostico_capacidad": diagnostico_capacidad,
        "variables_count": len(prob.variables()),
        "constraints_count": len(prob.constraints),
    }

    causas_infactible = [
        "Demanda superior a la capacidad de la seccional.",
        "Funcionarios asociados a seccionales sin oficinas.",
        "Restricciones de descanso.",
        "Restricciones de permisos.",
        "Máximo de horas semanales insuficiente.",
        "Cantidad insuficiente de funcionarios autorizados.",
    ]

    valor_costo_nomina = pulp.value(costo_nomina)
    valor_penalizacion = pulp.value(penalizacion_demanda)
    valor_objetivo = pulp.value(prob.objective)

    resultado["resumen"] = {
        "costo_nomina": valor_costo_nomina,
        "penalizacion_demanda": valor_penalizacion,
        "valor_objetivo": valor_objetivo,
    }

    if estado_solucion not in ("Optimal", "Feasible"):
        resultado["causas_posibles"] = causas_infactible
        return resultado

    oficinas_result: list[dict] = []
    cumplimiento_demanda: list[dict] = []
    permisos_verificacion: list[dict] = []

    total_horas_quincena = {o: {emp: 0 for emp in empleados} for o in oficinas}

    for o in oficinas:
        oficina_data = {"id": o, "semanas": []}
        for s in semanas:
            semana_data = {"numero": s, "dias": []}
            resumen_semanal = {emp: 0 for emp in empleados}

            for d in dias:
                dia_data = {
                    "nombre": d,
                    "horas": [],
                    "horas_por_empleado": [],
                    "descanso_compensatorio": [],
                }
                resumen_diario = {emp: 0 for emp in empleados}

                for h in horas_del_dia:
                    activos = []
                    almorzando_nombres = []
                    for emp in empleados:
                        for j in jornadas:
                            valor_asignado = asignado[o, emp, s, d, j].varValue
                            horas_de_esta_jornada = horas_por_jornada.get(j, [])
                            if (
                                valor_asignado is not None
                                and valor_asignado > 0.5
                                and h in horas_de_esta_jornada
                            ):
                                horas_almuerzo_jornada = almuerzos_permitidos.get(
                                    j, []
                                )
                                if h in horas_almuerzo_jornada:
                                    valor_almuerzo = almuerzo[
                                        o, emp, s, d, j, h
                                    ].varValue
                                    if (
                                        valor_almuerzo is not None
                                        and valor_almuerzo > 0.5
                                    ):
                                        almorzando_nombres.append(emp)
                                    else:
                                        activos.append(emp)
                                        resumen_diario[emp] += 1
                                        resumen_semanal[emp] += 1
                                        total_horas_quincena[o][emp] += 1
                                else:
                                    activos.append(emp)
                                    resumen_diario[emp] += 1
                                    resumen_semanal[emp] += 1
                                    total_horas_quincena[o][emp] += 1

                    activos.sort()
                    almorzando_nombres.sort()
                    dia_data["horas"].append(
                        {
                            "hora": h,
                            "requerido": demanda_por_hora[(o, s, d, h)],
                            "activos": activos,
                            "almorzando": almorzando_nombres,
                        }
                    )

                for emp in empleados:
                    if resumen_diario[emp] > 0:
                        dia_data["horas_por_empleado"].append(
                            {"empleado": emp, "horas": resumen_diario[emp]}
                        )

                if s == 2 and 1 in semanas:
                    funcionarios_que_trabajaron_domingo = []
                    for emp in empleados:
                        trabajo_domingo_s1 = sum(
                            asignado[od, emp, 1, "Domingo", j].varValue or 0
                            for od in oficinas
                            for j in jornadas
                        )
                        if trabajo_domingo_s1 > 0.5:
                            funcionarios_que_trabajaron_domingo.append(emp)
                    for emp in funcionarios_que_trabajaron_domingo:
                        trabajo_en_dia = sum(
                            asignado[od, emp, s, d, j].varValue or 0
                            for od in oficinas
                            for j in jornadas
                        )
                        if trabajo_en_dia < 0.5:
                            dia_data["descanso_compensatorio"].append(emp)

                semana_data["dias"].append(dia_data)

            semana_data["totales_semana"] = [
                {"empleado": emp, "horas": resumen_semanal[emp]}
                for emp in empleados
                if resumen_semanal[emp] > 0
            ]
            semana_data["total_general"] = sum(resumen_semanal.values())
            oficina_data["semanas"].append(semana_data)

        oficina_data["totales_quincena"] = [
            {"empleado": emp, "horas": total_horas_quincena[o][emp]}
            for emp in empleados
            if total_horas_quincena[o][emp] > 0
        ]
        oficina_data["total_quincena"] = sum(total_horas_quincena[o].values())
        oficinas_result.append(oficina_data)

    for o in oficinas:
        for s in semanas:
            for d in dias:
                for h in horas_del_dia:
                    faltante = sub_personal[o, s, d, h].varValue or 0
                    sobrante = sobre_personal[o, s, d, h].varValue or 0
                    if faltante > 0.0001 or sobrante > 0.0001:
                        cumplimiento_demanda.append(
                            {
                                "oficina": o,
                                "semana": s,
                                "dia": d,
                                "hora": h,
                                "faltante": faltante,
                                "sobrante": sobrante,
                            }
                        )

    for datos_permiso, permiso in permiso_laboral.items():
        id_oficina_permiso, emp_permiso, dia_permiso, hora_permiso = datos_permiso
        if permiso == 0:
            jornadas_afectadas = [
                j
                for j in jornadas
                if hora_permiso in horas_por_jornada.get(j, [])
            ]
            for s in semanas:
                jornadas_asignadas = []
                for j in jornadas_afectadas:
                    v = asignado[
                        id_oficina_permiso, emp_permiso, s, dia_permiso, j
                    ].varValue
                    if v is not None and v > 0.5:
                        jornadas_asignadas.append(j)
                permisos_verificacion.append(
                    {
                        "oficina": id_oficina_permiso,
                        "empleado": emp_permiso,
                        "dia": dia_permiso,
                        "hora": hora_permiso,
                        "semana": s,
                        "respetado": len(jornadas_asignadas) == 0,
                        "jornadas_asignadas": jornadas_asignadas,
                    }
                )

    totales_empleado = [
        {
            "empleado": emp,
            "horas": sum(total_horas_quincena[o][emp] for o in oficinas),
        }
        for emp in empleados
        if sum(total_horas_quincena[o][emp] for o in oficinas) > 0
    ]

    resultado["oficinas"] = oficinas_result
    resultado["cumplimiento_demanda"] = cumplimiento_demanda
    resultado["permisos_verificacion"] = permisos_verificacion
    resultado["totales_empleado"] = totales_empleado
    resultado["demanda_cumplida_total"] = len(cumplimiento_demanda) == 0 or not any(
        c["faltante"] > 0.0001 for c in cumplimiento_demanda
    )

    return resultado


def run_simulation(config: SolverConfig, demanda_path: Path) -> dict[str, Any]:
    demanda, oficinas, load_errors = load_demanda_from_excel(demanda_path, config)
    if load_errors:
        return {"ok": False, "errors": load_errors, "warnings": [], "results": None}

    assert demanda is not None and oficinas is not None
    results = _build_and_solve(config, demanda, oficinas)
    ok = results.get("estado") in ("Optimal", "Feasible")
    return {
        "ok": ok,
        "errors": [] if ok else ["El modelo no encontró una solución factible."],
        "warnings": [],
        "results": results,
    }
