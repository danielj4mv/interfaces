import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Jornada, Oficina
from app.schemas import JornadaCreate, JornadaOut, JornadaUpdate
from app.time_utils import normalize_hhmm, validate_jornada_times

router = APIRouter(prefix="/api/jornadas", tags=["jornadas"])


def _jornada_out(j: Jornada) -> JornadaOut:
    return JornadaOut(
        id=j.id,
        oficina_id=j.oficina_id,
        inicio=j.inicio,
        fin=j.fin,
        break_inicio=j.break_inicio,
        break_fin=j.break_fin,
        dias=json.loads(j.dias_json),
        oficina_nombre=j.oficina.nombre if j.oficina else None,
        seccional_nombre=(
            j.oficina.seccional.nombre
            if j.oficina and j.oficina.seccional
            else None
        ),
    )


def _normalize_body(body: JornadaCreate | JornadaUpdate) -> tuple[str, str, str | None, str | None]:
    err = validate_jornada_times(
        body.inicio, body.fin, body.break_inicio, body.break_fin
    )
    if err:
        raise HTTPException(status_code=400, detail=err)
    ini = normalize_hhmm(body.inicio)
    fin = normalize_hhmm(body.fin)
    bi = normalize_hhmm(body.break_inicio or "") if body.break_inicio else None
    bf = normalize_hhmm(body.break_fin or "") if body.break_fin else None
    return ini, fin, bi, bf


@router.get("", response_model=list[JornadaOut])
def list_jornadas(db: Session = Depends(get_db)):
    rows = (
        db.query(Jornada)
        .options(joinedload(Jornada.oficina).joinedload(Oficina.seccional))
        .order_by(Jornada.id)
        .all()
    )
    return [_jornada_out(j) for j in rows]


@router.post("", response_model=JornadaOut, status_code=201)
def create_jornada(body: JornadaCreate, db: Session = Depends(get_db)):
    oficina = db.get(Oficina, body.oficina_id)
    if not oficina:
        raise HTTPException(status_code=400, detail="Oficina no válida.")
    ini, fin, bi, bf = _normalize_body(body)
    row = Jornada(
        oficina_id=body.oficina_id,
        inicio=ini,
        fin=fin,
        break_inicio=bi,
        break_fin=bf,
        dias_json=json.dumps(body.dias),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    row = (
        db.query(Jornada)
        .options(joinedload(Jornada.oficina).joinedload(Oficina.seccional))
        .filter(Jornada.id == row.id)
        .one()
    )
    return _jornada_out(row)


@router.put("/{jornada_id}", response_model=JornadaOut)
def update_jornada(
    jornada_id: int, body: JornadaUpdate, db: Session = Depends(get_db)
):
    row = db.get(Jornada, jornada_id)
    if not row:
        raise HTTPException(status_code=404, detail="Jornada no encontrada.")
    oficina = db.get(Oficina, body.oficina_id)
    if not oficina:
        raise HTTPException(status_code=400, detail="Oficina no válida.")
    ini, fin, bi, bf = _normalize_body(body)
    row.oficina_id = body.oficina_id
    row.inicio = ini
    row.fin = fin
    row.break_inicio = bi
    row.break_fin = bf
    row.dias_json = json.dumps(body.dias)
    db.commit()
    row = (
        db.query(Jornada)
        .options(joinedload(Jornada.oficina).joinedload(Oficina.seccional))
        .filter(Jornada.id == jornada_id)
        .one()
    )
    return _jornada_out(row)


@router.delete("/{jornada_id}", status_code=204)
def delete_jornada(jornada_id: int, db: Session = Depends(get_db)):
    row = db.get(Jornada, jornada_id)
    if not row:
        raise HTTPException(status_code=404, detail="Jornada no encontrada.")
    db.delete(row)
    db.commit()
