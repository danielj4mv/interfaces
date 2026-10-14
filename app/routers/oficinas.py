from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Oficina, PermisoLaboral, Seccional
from app.schemas import OficinaCreate, OficinaOut, OficinaUpdate

router = APIRouter(prefix="/api/oficinas", tags=["oficinas"])


def _to_out(oficina: Oficina) -> OficinaOut:
    return OficinaOut(
        id=oficina.id,
        nombre=oficina.nombre,
        seccional_id=oficina.seccional_id,
        seccional_nombre=oficina.seccional.nombre if oficina.seccional else None,
    )


@router.get("", response_model=list[OficinaOut])
def list_oficinas(db: Session = Depends(get_db)):
    rows = db.query(Oficina).order_by(Oficina.id).all()
    return [_to_out(o) for o in rows]


@router.post("", response_model=OficinaOut, status_code=201)
def create_oficina(body: OficinaCreate, db: Session = Depends(get_db)):
    if not db.get(Seccional, body.seccional_id):
        raise HTTPException(status_code=400, detail="Seccional no válida.")
    row = Oficina(nombre=body.nombre, seccional_id=body.seccional_id)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_out(row)


@router.put("/{oficina_id}", response_model=OficinaOut)
def update_oficina(oficina_id: int, body: OficinaUpdate, db: Session = Depends(get_db)):
    row = db.get(Oficina, oficina_id)
    if not row:
        raise HTTPException(status_code=404, detail="Oficina no encontrada.")
    if not db.get(Seccional, body.seccional_id):
        raise HTTPException(status_code=400, detail="Seccional no válida.")
    row.nombre = body.nombre
    row.seccional_id = body.seccional_id
    db.commit()
    db.refresh(row)
    return _to_out(row)


@router.delete("/{oficina_id}", status_code=204)
def delete_oficina(oficina_id: int, db: Session = Depends(get_db)):
    row = db.get(Oficina, oficina_id)
    if not row:
        raise HTTPException(status_code=404, detail="Oficina no encontrada.")
    if db.query(PermisoLaboral).filter(PermisoLaboral.oficina_id == oficina_id).first():
        raise HTTPException(
            status_code=400,
            detail="No se puede eliminar: tiene permisos laborales asociados.",
        )
    db.delete(row)
    db.commit()
