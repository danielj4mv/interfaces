from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Seccional, Servicio
from app.schemas import ServicioCreate, ServicioOut, ServicioUpdate

router = APIRouter(prefix="/api/servicios", tags=["servicios"])


def _to_out(s: Servicio) -> ServicioOut:
    return ServicioOut(
        id=s.id,
        nombre=s.nombre,
        seccional_id=s.seccional_id,
        seccional_nombre=s.seccional.nombre if s.seccional else None,
    )


@router.get("", response_model=list[ServicioOut])
def list_servicios(db: Session = Depends(get_db)):
    rows = (
        db.query(Servicio)
        .options(joinedload(Servicio.seccional))
        .order_by(Servicio.nombre)
        .all()
    )
    return [_to_out(s) for s in rows]


@router.post("", response_model=ServicioOut, status_code=201)
def create_servicio(body: ServicioCreate, db: Session = Depends(get_db)):
    if not db.get(Seccional, body.seccional_id):
        raise HTTPException(status_code=400, detail="Seccional no válida.")
    dup = (
        db.query(Servicio)
        .filter(
            Servicio.seccional_id == body.seccional_id,
            Servicio.nombre == body.nombre,
        )
        .first()
    )
    if dup:
        raise HTTPException(
            status_code=400,
            detail="Ya existe un servicio con ese nombre en la seccional.",
        )
    row = Servicio(nombre=body.nombre, seccional_id=body.seccional_id)
    db.add(row)
    db.commit()
    db.refresh(row)
    row = (
        db.query(Servicio)
        .options(joinedload(Servicio.seccional))
        .filter(Servicio.id == row.id)
        .one()
    )
    return _to_out(row)


@router.put("/{servicio_id}", response_model=ServicioOut)
def update_servicio(
    servicio_id: int, body: ServicioUpdate, db: Session = Depends(get_db)
):
    row = db.get(Servicio, servicio_id)
    if not row:
        raise HTTPException(status_code=404, detail="Servicio no encontrado.")
    if not db.get(Seccional, body.seccional_id):
        raise HTTPException(status_code=400, detail="Seccional no válida.")
    dup = (
        db.query(Servicio)
        .filter(
            Servicio.seccional_id == body.seccional_id,
            Servicio.nombre == body.nombre,
            Servicio.id != servicio_id,
        )
        .first()
    )
    if dup:
        raise HTTPException(
            status_code=400,
            detail="Ya existe un servicio con ese nombre en la seccional.",
        )
    row.nombre = body.nombre
    row.seccional_id = body.seccional_id
    db.commit()
    row = (
        db.query(Servicio)
        .options(joinedload(Servicio.seccional))
        .filter(Servicio.id == servicio_id)
        .one()
    )
    return _to_out(row)


@router.delete("/{servicio_id}", status_code=204)
def delete_servicio(servicio_id: int, db: Session = Depends(get_db)):
    row = db.get(Servicio, servicio_id)
    if not row:
        raise HTTPException(status_code=404, detail="Servicio no encontrado.")
    db.delete(row)
    db.commit()
