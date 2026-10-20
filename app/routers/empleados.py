from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Empleado, PermisoLaboral, Servicio, Seccional
from app.schemas import (
    EmpleadoCreate,
    EmpleadoOut,
    EmpleadoUpdate,
    PermisoLaboralOut,
)
from app.time_utils import normalize_hhmm

router = APIRouter(prefix="/api/empleados", tags=["empleados"])


def _validate_servicio_seccional(
    db: Session, seccional_id: int, servicio_id: int
) -> None:
    servicio = db.get(Servicio, servicio_id)
    if not servicio:
        raise HTTPException(status_code=400, detail="Servicio no válido.")
    if servicio.seccional_id != seccional_id:
        raise HTTPException(
            status_code=400,
            detail="El servicio no pertenece a la seccional del empleado.",
        )


def _validate_permisos(permisos: list) -> None:
    for p in permisos:
        if p.tipo == "horas":
            hi = normalize_hhmm(p.hora_inicio or "")
            hf = normalize_hhmm(p.hora_fin or "")
            if not hi or not hf:
                raise HTTPException(
                    status_code=400,
                    detail="Permiso por horas: hora_inicio y hora_fin inválidas.",
                )


def _to_out(emp: Empleado) -> EmpleadoOut:
    return EmpleadoOut(
        id=emp.id,
        nombre=emp.nombre,
        seccional_id=emp.seccional_id,
        servicio_id=emp.servicio_id,
        horas_semanales=emp.horas_semanales,
        dia_descanso=emp.dia_descanso,
        modo_horas=emp.modo_horas,
        holgura_pct=emp.holgura_pct,
        seccional_nombre=emp.seccional.nombre if emp.seccional else None,
        servicio_nombre=emp.servicio.nombre if emp.servicio else None,
        permisos=[
            PermisoLaboralOut(
                id=p.id,
                tipo=p.tipo,
                dia=p.dia,
                hora_inicio=p.hora_inicio,
                hora_fin=p.hora_fin,
            )
            for p in emp.permisos
        ],
    )


def _apply_permisos(row: Empleado, permisos: list) -> None:
    row.permisos.clear()
    for p in permisos:
        hi = normalize_hhmm(p.hora_inicio or "") if p.tipo == "horas" else None
        hf = normalize_hhmm(p.hora_fin or "") if p.tipo == "horas" else None
        row.permisos.append(
            PermisoLaboral(
                tipo=p.tipo,
                dia=p.dia,
                hora_inicio=hi,
                hora_fin=hf,
            )
        )


@router.get("", response_model=list[EmpleadoOut])
def list_empleados(db: Session = Depends(get_db)):
    rows = (
        db.query(Empleado)
        .options(
            joinedload(Empleado.seccional),
            joinedload(Empleado.servicio),
            joinedload(Empleado.permisos),
        )
        .order_by(Empleado.nombre)
        .all()
    )
    return [_to_out(e) for e in rows]


@router.post("", response_model=EmpleadoOut, status_code=201)
def create_empleado(body: EmpleadoCreate, db: Session = Depends(get_db)):
    if not db.get(Seccional, body.seccional_id):
        raise HTTPException(status_code=400, detail="Seccional no válida.")
    _validate_servicio_seccional(db, body.seccional_id, body.servicio_id)
    _validate_permisos(body.permisos)
    holgura = body.holgura_pct if body.modo_horas == "flexible" else 0.0
    row = Empleado(
        nombre=body.nombre,
        seccional_id=body.seccional_id,
        servicio_id=body.servicio_id,
        horas_semanales=body.horas_semanales,
        dia_descanso=body.dia_descanso,
        modo_horas=body.modo_horas,
        holgura_pct=holgura,
    )
    _apply_permisos(row, body.permisos)
    db.add(row)
    db.commit()
    row = (
        db.query(Empleado)
        .options(
            joinedload(Empleado.seccional),
            joinedload(Empleado.servicio),
            joinedload(Empleado.permisos),
        )
        .filter(Empleado.id == row.id)
        .one()
    )
    return _to_out(row)


@router.put("/{empleado_id}", response_model=EmpleadoOut)
def update_empleado(
    empleado_id: int, body: EmpleadoUpdate, db: Session = Depends(get_db)
):
    row = (
        db.query(Empleado)
        .options(joinedload(Empleado.permisos))
        .filter(Empleado.id == empleado_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Empleado no encontrado.")
    if not db.get(Seccional, body.seccional_id):
        raise HTTPException(status_code=400, detail="Seccional no válida.")
    _validate_servicio_seccional(db, body.seccional_id, body.servicio_id)
    _validate_permisos(body.permisos)
    holgura = body.holgura_pct if body.modo_horas == "flexible" else 0.0
    row.nombre = body.nombre
    row.seccional_id = body.seccional_id
    row.servicio_id = body.servicio_id
    row.horas_semanales = body.horas_semanales
    row.dia_descanso = body.dia_descanso
    row.modo_horas = body.modo_horas
    row.holgura_pct = holgura
    _apply_permisos(row, body.permisos)
    db.commit()
    row = (
        db.query(Empleado)
        .options(
            joinedload(Empleado.seccional),
            joinedload(Empleado.servicio),
            joinedload(Empleado.permisos),
        )
        .filter(Empleado.id == empleado_id)
        .one()
    )
    return _to_out(row)


@router.delete("/{empleado_id}", status_code=204)
def delete_empleado(empleado_id: int, db: Session = Depends(get_db)):
    row = db.get(Empleado, empleado_id)
    if not row:
        raise HTTPException(status_code=404, detail="Empleado no encontrado.")
    db.delete(row)
    db.commit()
