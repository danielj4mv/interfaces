from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Empleado, Oficina, Seccional
from app.schemas import SeccionalCreate, SeccionalOut, SeccionalUpdate

router = APIRouter(prefix="/api/seccionales", tags=["seccionales"])


@router.get("", response_model=list[SeccionalOut])
def list_seccionales(db: Session = Depends(get_db)):
    return db.query(Seccional).order_by(Seccional.nombre).all()


@router.post("", response_model=SeccionalOut, status_code=201)
def create_seccional(body: SeccionalCreate, db: Session = Depends(get_db)):
    existing = db.query(Seccional).filter(Seccional.nombre == body.nombre).first()
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe una seccional con ese nombre.")
    row = Seccional(nombre=body.nombre)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.put("/{seccional_id}", response_model=SeccionalOut)
def update_seccional(
    seccional_id: int, body: SeccionalUpdate, db: Session = Depends(get_db)
):
    row = db.get(Seccional, seccional_id)
    if not row:
        raise HTTPException(status_code=404, detail="Seccional no encontrada.")
    dup = (
        db.query(Seccional)
        .filter(Seccional.nombre == body.nombre, Seccional.id != seccional_id)
        .first()
    )
    if dup:
        raise HTTPException(status_code=400, detail="Ya existe una seccional con ese nombre.")
    row.nombre = body.nombre
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{seccional_id}", status_code=204)
def delete_seccional(seccional_id: int, db: Session = Depends(get_db)):
    row = db.get(Seccional, seccional_id)
    if not row:
        raise HTTPException(status_code=404, detail="Seccional no encontrada.")
    if db.query(Oficina).filter(Oficina.seccional_id == seccional_id).first():
        raise HTTPException(
            status_code=400,
            detail="No se puede eliminar: tiene oficinas asociadas.",
        )
    if db.query(Empleado).filter(Empleado.seccional_id == seccional_id).first():
        raise HTTPException(
            status_code=400,
            detail="No se puede eliminar: tiene empleados asociados.",
        )
    db.delete(row)
    db.commit()
