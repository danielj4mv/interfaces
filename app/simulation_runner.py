"""Build and run per (seccional, semana, servicio) problems using basic.solve_schedule."""

from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy.orm import Session, joinedload

from app.constants import dia_nombre
from app.models import DemandaFila, Empleado, Jornada, Oficina, Seccional, Servicio
from basic import Employee, HourlyPermission, Shift, solve_schedule


@dataclass
class ProblemKey:
    seccional_id: int
    seccional_nombre: str
    semana: int
    servicio_id: int
    servicio_nombre: str


def list_problems(db: Session) -> list[ProblemKey]:
    rows = (
        db.query(
            DemandaFila.seccional_id,
            DemandaFila.semana,
            DemandaFila.servicio_id,
        )
        .distinct()
        .order_by(
            DemandaFila.seccional_id,
            DemandaFila.semana,
            DemandaFila.servicio_id,
        )
        .all()
    )
    seccionales = {s.id: s.nombre for s in db.query(Seccional).all()}
    servicios = {s.id: s.nombre for s in db.query(Servicio).all()}
    return [
        ProblemKey(
            seccional_id=r[0],
            seccional_nombre=seccionales.get(r[0], ""),
            semana=r[1],
            servicio_id=r[2],
            servicio_nombre=servicios.get(r[2], ""),
        )
        for r in rows
    ]


def _employee_display_name(emp: Empleado) -> str:
    return emp.nombre


def build_and_solve(db: Session, key: ProblemKey) -> dict:
    demand_rows = (
        db.query(DemandaFila)
        .filter(
            DemandaFila.seccional_id == key.seccional_id,
            DemandaFila.semana == key.semana,
            DemandaFila.servicio_id == key.servicio_id,
        )
        .all()
    )
    oficina_ids = {r.oficina_id for r in demand_rows}
    oficinas = {
        o.id: o
        for o in db.query(Oficina).filter(Oficina.id.in_(oficina_ids)).all()
    }

    empleados = (
        db.query(Empleado)
        .options(joinedload(Empleado.permisos))
        .filter(
            Empleado.seccional_id == key.seccional_id,
            Empleado.servicio_id == key.servicio_id,
        )
        .all()
    )
    if not empleados:
        raise ValueError(
            f"No hay empleados para {key.seccional_nombre} / {key.servicio_nombre}."
        )

    jornadas_db = (
        db.query(Jornada)
        .options(joinedload(Jornada.oficina))
        .filter(Jornada.oficina_id.in_(oficina_ids))
        .all()
    )
    if not jornadas_db:
        raise ValueError("No hay jornadas para las oficinas de esta demanda.")

    emp_by_id = {e.id: e for e in empleados}
    employees = [
        Employee(
            id=str(e.id),
            weekly_hours=e.horas_semanales,
            rest_day=e.dia_descanso,
            hours_mode=e.modo_horas,
            slack_pct=e.holgura_pct,
        )
        for e in empleados
    ]

    shifts: list[Shift] = []
    for j in jornadas_db:
        dias = tuple(json.loads(j.dias_json))
        shifts.append(
            Shift(
                id=str(j.id),
                office=j.oficina.nombre,
                start=j.inicio,
                end=j.fin,
                break_start=j.break_inicio,
                break_end=j.break_fin,
                days=dias,
            )
        )

    demand: dict[tuple[str, int, str], int] = {}
    for r in demand_rows:
        of_name = oficinas[r.oficina_id].nombre
        demand[(of_name, r.dia, r.hora)] = r.demanda

    full_day: set[tuple[str, int]] = set()
    hourly: list[HourlyPermission] = []
    for e in empleados:
        eid = str(e.id)
        for p in e.permisos:
            if p.tipo == "dia_completo":
                full_day.add((eid, p.dia))
            else:
                hourly.append(
                    HourlyPermission(
                        employee_id=eid,
                        day=p.dia,
                        start=p.hora_inicio or "00:00",
                        end=p.hora_fin or "00:30",
                    )
                )

    schedule_rows, coverage_rows, hours_rows, info = solve_schedule(
        employees=employees,
        shifts=shifts,
        demand=demand,
        full_day_permissions=full_day,
        hourly_permissions=hourly,
    )

    id_to_name = {str(e.id): _employee_display_name(e) for e in empleados}

    schedule_out = []
    for row in schedule_rows:
        item = dict(row)
        eid = str(item.pop("empleado_id"))
        item["empleado"] = id_to_name.get(eid, eid)
        item["dia_nombre"] = dia_nombre(int(item["dia"]))
        schedule_out.append(item)

    coverage_out = []
    for row in coverage_rows:
        item = dict(row)
        item["dia_nombre"] = dia_nombre(int(item["dia"]))
        coverage_out.append(item)

    hours_out = []
    for row in hours_rows:
        item = dict(row)
        eid = str(item.pop("empleado_id"))
        item["empleado"] = id_to_name.get(eid, eid)
        item["dia_descanso_nombre"] = dia_nombre(int(item["dia_descanso"]))
        hours_out.append(item)

    return {
        "seccional": key.seccional_nombre,
        "semana": key.semana,
        "servicio": key.servicio_nombre,
        "status": info.get("status"),
        "objective": info.get("objective"),
        "schedule": schedule_out,
        "coverage": coverage_out,
        "employee_hours": hours_out,
    }
