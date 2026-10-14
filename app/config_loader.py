import json
from dataclasses import dataclass

from sqlalchemy.orm import Session, joinedload

from app.models import Dia, Empleado, Jornada, Oficina, Semana, Seccional


@dataclass
class SolverConfig:
    empleados: list[str]
    seccional_por_oficina: dict[int, str]
    funcionarios_por_seccional: dict[str, list[str]]
    semanas: list[int]
    dias: list[str]
    jornadas: list[str]
    horas_del_dia: list[str]
    horas_por_jornada: dict[str, list[str]]
    almuerzos_permitidos: dict[str, list[str]]
    permiso_laboral: dict[tuple, int]
    pago_hora: dict[str, float]
    oficinas_registradas: set[int]
    seccionales: dict[int, str]


def load_solver_config(db: Session) -> SolverConfig:
    seccionales = {s.id: s.nombre for s in db.query(Seccional).all()}
    oficinas = db.query(Oficina).all()
    seccional_por_oficina = {
        o.id: seccionales[o.seccional_id] for o in oficinas
    }
    oficinas_registradas = set(seccional_por_oficina.keys())

    empleados_rows = (
        db.query(Empleado)
        .options(joinedload(Empleado.permisos))
        .all()
    )
    empleados = [e.nombre for e in empleados_rows]
    pago_hora = {e.nombre: float(e.pago_hora) for e in empleados_rows}

    funcionarios_por_seccional: dict[str, list[str]] = {}
    for e in empleados_rows:
        sec_nombre = seccionales[e.seccional_id]
        funcionarios_por_seccional.setdefault(sec_nombre, []).append(e.nombre)

    permiso_laboral: dict[tuple, int] = {}
    for e in empleados_rows:
        for p in e.permisos:
            permiso_laboral[(p.oficina_id, e.nombre, p.dia, p.hora)] = 0

    semanas = [s.numero for s in db.query(Semana).order_by(Semana.numero).all()]
    dias = [
        d.nombre
        for d in db.query(Dia).filter(Dia.activo.is_(True)).order_by(Dia.orden).all()
    ]

    jornadas_rows = db.query(Jornada).order_by(Jornada.nombre).all()
    jornadas = [j.nombre for j in jornadas_rows]
    horas_por_jornada = {
        j.nombre: json.loads(j.horas_json) for j in jornadas_rows
    }
    almuerzos_permitidos = {
        j.nombre: json.loads(j.almuerzos_json)
        for j in jornadas_rows
        if json.loads(j.almuerzos_json)
    }

    horas_set: set[str] = set()
    for horas in horas_por_jornada.values():
        horas_set.update(horas)

    def hora_key(h: str) -> tuple[int, int]:
        parts = h.split(":")
        return (int(parts[0]), int(parts[1]))

    horas_del_dia = sorted(horas_set, key=hora_key)

    return SolverConfig(
        empleados=empleados,
        seccional_por_oficina=seccional_por_oficina,
        funcionarios_por_seccional=funcionarios_por_seccional,
        semanas=semanas,
        dias=dias,
        jornadas=jornadas,
        horas_del_dia=horas_del_dia,
        horas_por_jornada=horas_por_jornada,
        almuerzos_permitidos=almuerzos_permitidos,
        permiso_laboral=permiso_laboral,
        pago_hora=pago_hora,
        oficinas_registradas=oficinas_registradas,
        seccionales=seccionales,
    )