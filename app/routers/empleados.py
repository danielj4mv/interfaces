from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Empleado, Oficina, PermisoLaboral, Seccional
from app.schemas import EmpleadoCreate, EmpleadoOut, EmpleadoUpdate, PermisoLaboralOut

router = APIRouter(prefix="/api/empleados", tags=["empleados"])


def _validate_permisos(db: Session, seccional_id: int, permisos: list) -> None:
    for p in permisos:
        oficina = db.get(Oficina, p.oficina_id)
        if not oficina:
            raise HTTPException(
                status_code=400,
                detail=f"Oficina {p.oficina_id} no existe para permiso laboral.",
            )
        if oficina.seccional_id != seccional_id:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"La oficina {p.oficina_id} no pertenece a la seccional del empleado."
                ),
            )


def _to_out(emp: Empleado) -> EmpleadoOut:
    return EmpleadoOut(
        id=emp.id,
        nombre=emp.nombre,
        pago_hora=emp.pago_hora,
        seccional_id=emp.seccional_id,
        seccional_nombre=emp.seccional.nombre if emp.seccional else None,
        permisos=[
            PermisoLaboralOut(
                id=p.id,
                oficina_id=p.oficina_id,
                dia=p.dia,
                hora=p.hora,
            )
            for p in emp.permisos
        ],
    )


@router.get("", response_model=list[EmpleadoOut])
def list_empleados(db: Session = Depends(get_db)):
    rows = (
        db.query(Empleado)
        .options(joinedload(Empleado.seccional), joinedload(Empleado.permisos))
        .order_by(Empleado.nombre)
        .all()
    )
    return [_to_out(e) for e in rows]


@router.post("", response_model=EmpleadoOut, status_code=201)
def create_empleado(body: EmpleadoCreate, db: Session = Depends(get_db)):
    if not db.get(Seccional, body.seccional_id):
        raise HTTPException(status_code=400, detail="Seccional no válida.")
    _validate_permisos(db, body.seccional_id, body.permisos)
    row = Empleado(
        nombre=body.nombre,
        pago_hora=body.pago_hora,
        seccional_id=body.seccional_id,
    )
    for p in body.permisos:
        row.permisos.append(
            PermisoLaboral(
                oficina_id=p.oficina_id,
                dia=p.dia,
                hora=p.hora,
            )
        )
    db.add(row)
    db.commit()
    db.refresh(row)
    row = (
        db.query(Empleado)
        .options(joinedload(Empleado.seccional), joinedload(Empleado.permisos))
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
    _validate_permisos(db, body.seccional_id, body.permisos)
    row.nombre = body.nombre
    row.pago_hora = body.pago_hora
    row.seccional_id = body.seccional_id
    row.permisos.clear()
    for p in body.permisos:
        row.permisos.append(
            PermisoLaboral(
                oficina_id=p.oficina_id,
                dia=p.dia,
                hora=p.hora,
            )
        )
    db.commit()
    row = (
        db.query(Empleado)
        .options(joinedload(Empleado.seccional), joinedload(Empleado.permisos))
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
