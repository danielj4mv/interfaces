import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Dia, Jornada, Semana
from app.schemas import (
    DiaActivoUpdate,
    DiaCreate,
    DiaOut,
    DiaUpdate,
    JornadaCreate,
    JornadaOut,
    JornadaUpdate,
    SemanaCreate,
    SemanaOut,
    SemanasSync,
)

router = APIRouter(prefix="/api", tags=["jornadas"])


def _jornada_out(j: Jornada) -> JornadaOut:
    return JornadaOut(
        id=j.id,
        nombre=j.nombre,
        horas=json.loads(j.horas_json),
        almuerzos=json.loads(j.almuerzos_json),
    )


def _validate_jornada_horas(horas: list[str], almuerzos: list[str]) -> None:
    if not horas:
        raise HTTPException(status_code=400, detail="La jornada debe tener al menos una hora.")
    for h in almuerzos:
        if h not in horas:
            raise HTTPException(
                status_code=400,
                detail=f"La hora de almuerzo '{h}' no está en las horas de la jornada.",
            )


# --- Semanas ---
@router.get("/semanas", response_model=list[SemanaOut])
def list_semanas(db: Session = Depends(get_db)):
    return db.query(Semana).order_by(Semana.numero).all()


@router.post("/semanas", response_model=SemanaOut, status_code=201)
def create_semana(body: SemanaCreate, db: Session = Depends(get_db)):
    if db.query(Semana).filter(Semana.numero == body.numero).first():
        raise HTTPException(status_code=400, detail="Ese número de semana ya existe.")
    row = Semana(numero=body.numero)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/semanas/{semana_id}", status_code=204)
def delete_semana(semana_id: int, db: Session = Depends(get_db)):
    row = db.get(Semana, semana_id)
    if not row:
        raise HTTPException(status_code=404, detail="Semana no encontrada.")
    db.delete(row)
    db.commit()


@router.put("/semanas/sync", response_model=list[SemanaOut])
def sync_semanas(body: SemanasSync, db: Session = Depends(get_db)):
    existing = {s.numero: s for s in db.query(Semana).all()}
    for n in range(1, body.cantidad + 1):
        if n not in existing:
            db.add(Semana(numero=n))
    for numero, row in list(existing.items()):
        if numero > body.cantidad:
            db.delete(row)
    db.commit()
    return db.query(Semana).order_by(Semana.numero).all()


# --- Días ---
@router.get("/dias", response_model=list[DiaOut])
def list_dias(db: Session = Depends(get_db)):
    return db.query(Dia).order_by(Dia.orden).all()


@router.post("/dias", response_model=DiaOut, status_code=201)
def create_dia(body: DiaCreate, db: Session = Depends(get_db)):
    if db.query(Dia).filter(Dia.nombre == body.nombre).first():
        raise HTTPException(status_code=400, detail="Ya existe un día con ese nombre.")
    row = Dia(nombre=body.nombre, orden=body.orden)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/dias/{dia_id}/activo", response_model=DiaOut)
def set_dia_activo(dia_id: int, body: DiaActivoUpdate, db: Session = Depends(get_db)):
    row = db.get(Dia, dia_id)
    if not row:
        raise HTTPException(status_code=404, detail="Día no encontrado.")
    row.activo = body.activo
    db.commit()
    db.refresh(row)
    return row


@router.put("/dias/{dia_id}", response_model=DiaOut)
def update_dia(dia_id: int, body: DiaUpdate, db: Session = Depends(get_db)):
    row = db.get(Dia, dia_id)
    if not row:
        raise HTTPException(status_code=404, detail="Día no encontrado.")
    dup = db.query(Dia).filter(Dia.nombre == body.nombre, Dia.id != dia_id).first()
    if dup:
        raise HTTPException(status_code=400, detail="Ya existe un día con ese nombre.")
    row.nombre = body.nombre
    row.orden = body.orden
    db.commit()
    db.refresh(row)
    return row


@router.delete("/dias/{dia_id}", status_code=204)
def delete_dia(dia_id: int, db: Session = Depends(get_db)):
    row = db.get(Dia, dia_id)
    if not row:
        raise HTTPException(status_code=404, detail="Día no encontrado.")
    db.delete(row)
    db.commit()


# --- Jornadas ---
@router.get("/jornadas", response_model=list[JornadaOut])
def list_jornadas(db: Session = Depends(get_db)):
    rows = db.query(Jornada).order_by(Jornada.nombre).all()
    return [_jornada_out(j) for j in rows]


@router.post("/jornadas", response_model=JornadaOut, status_code=201)
def create_jornada(body: JornadaCreate, db: Session = Depends(get_db)):
    _validate_jornada_horas(body.horas, body.almuerzos)
    if db.query(Jornada).filter(Jornada.nombre == body.nombre).first():
        raise HTTPException(status_code=400, detail="Ya existe una jornada con ese nombre.")
    row = Jornada(
        nombre=body.nombre,
        horas_json=json.dumps(body.horas),
        almuerzos_json=json.dumps(body.almuerzos),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _jornada_out(row)


@router.put("/jornadas/{jornada_id}", response_model=JornadaOut)
def update_jornada(
    jornada_id: int, body: JornadaUpdate, db: Session = Depends(get_db)
):
    _validate_jornada_horas(body.horas, body.almuerzos)
    row = db.get(Jornada, jornada_id)
    if not row:
        raise HTTPException(status_code=404, detail="Jornada no encontrada.")
    dup = (
        db.query(Jornada)
        .filter(Jornada.nombre == body.nombre, Jornada.id != jornada_id)
        .first()
    )
    if dup:
        raise HTTPException(status_code=400, detail="Ya existe una jornada con ese nombre.")
    row.nombre = body.nombre
    row.horas_json = json.dumps(body.horas)
    row.almuerzos_json = json.dumps(body.almuerzos)
    db.commit()
    db.refresh(row)
    return _jornada_out(row)


@router.delete("/jornadas/{jornada_id}", status_code=204)
def delete_jornada(jornada_id: int, db: Session = Depends(get_db)):
    row = db.get(Jornada, jornada_id)
    if not row:
        raise HTTPException(status_code=404, detail="Jornada no encontrada.")
    db.delete(row)
    db.commit()
