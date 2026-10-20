from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.constants import parse_dia
from app.database import get_db
from app.models import DemandaFila, Oficina, Seccional, Servicio
from app.schemas import (
    DemandaBulkIn,
    DemandaBulkResult,
    DemandaFilaOut,
    DemandaListOut,
)
from app.time_utils import normalize_hhmm

router = APIRouter(prefix="/api/demanda", tags=["demanda"])


def _resolve_names(db: Session, filas: list) -> tuple[list[dict], list[str]]:
    seccionales = {s.nombre.strip().lower(): s for s in db.query(Seccional).all()}
    oficinas = (
        db.query(Oficina)
        .options(joinedload(Oficina.seccional))
        .all()
    )
    oficina_by_key = {
        (o.seccional_id, o.nombre.strip().lower()): o for o in oficinas
    }
    servicios = db.query(Servicio).all()
    servicio_by_key = {
        (s.seccional_id, s.nombre.strip().lower()): s for s in servicios
    }

    errors: list[str] = []
    resolved: list[dict] = []
    seen: set[tuple] = set()

    for i, f in enumerate(filas, start=1):
        sec_name = f.seccional.strip()
        sec = seccionales.get(sec_name.lower())
        if not sec:
            errors.append(f"Fila {i}: seccional desconocida '{f.seccional}'.")
            continue
        of_name = f.oficina.strip()
        oficina = oficina_by_key.get((sec.id, of_name.lower()))
        if not oficina:
            errors.append(
                f"Fila {i}: oficina '{f.oficina}' no existe en seccional '{f.seccional}'."
            )
            continue
        srv_name = f.servicio.strip()
        servicio = servicio_by_key.get((sec.id, srv_name.lower()))
        if not servicio:
            errors.append(
                f"Fila {i}: servicio '{f.servicio}' no existe en seccional '{f.seccional}'."
            )
            continue
        dia = parse_dia(f.dia)
        if dia is None:
            errors.append(f"Fila {i}: día inválido '{f.dia}'.")
            continue
        hora = normalize_hhmm(f.hora)
        if not hora:
            errors.append(f"Fila {i}: hora inválida '{f.hora}' (use HH:MM, :00 o :30).")
            continue
        if f.semana < 1:
            errors.append(f"Fila {i}: semana debe ser >= 1.")
            continue
        if f.demanda < 0:
            errors.append(f"Fila {i}: demanda no puede ser negativa.")
            continue
        key = (oficina.id, servicio.id, f.semana, dia, hora)
        if key in seen:
            errors.append(
                f"Fila {i}: duplicado ({f.oficina}, {f.servicio}, semana {f.semana}, "
                f"día {dia}, {hora})."
            )
            continue
        seen.add(key)
        resolved.append(
            {
                "seccional_id": sec.id,
                "oficina_id": oficina.id,
                "servicio_id": servicio.id,
                "semana": int(f.semana),
                "dia": dia,
                "hora": hora,
                "demanda": int(f.demanda),
                "seccional": sec.nombre,
                "oficina": oficina.nombre,
                "servicio": servicio.nombre,
            }
        )
    return resolved, errors


@router.get("", response_model=DemandaListOut)
def list_demanda(
    db: Session = Depends(get_db),
    offset: int = Query(0, ge=0),
    limit: int = Query(500, ge=1, le=5000),
):
    total = db.query(DemandaFila).count()
    rows = (
        db.query(DemandaFila)
        .order_by(
            DemandaFila.seccional_id,
            DemandaFila.semana,
            DemandaFila.servicio_id,
            DemandaFila.oficina_id,
            DemandaFila.dia,
            DemandaFila.hora,
        )
        .offset(offset)
        .limit(limit)
        .all()
    )
    seccionales = {s.id: s.nombre for s in db.query(Seccional).all()}
    oficinas = {o.id: o.nombre for o in db.query(Oficina).all()}
    servicios = {s.id: s.nombre for s in db.query(Servicio).all()}
    filas = [
        DemandaFilaOut(
            id=r.id,
            seccional=seccionales.get(r.seccional_id, ""),
            oficina=oficinas.get(r.oficina_id, ""),
            servicio=servicios.get(r.servicio_id, ""),
            semana=r.semana,
            dia=r.dia,
            hora=r.hora,
            demanda=r.demanda,
        )
        for r in rows
    ]
    return DemandaListOut(filas=filas, total=total)


@router.post("", response_model=DemandaBulkResult)
def bulk_replace_demanda(body: DemandaBulkIn, db: Session = Depends(get_db)):
    if not body.filas:
        raise HTTPException(status_code=400, detail="No hay filas para guardar.")
    resolved, errors = _resolve_names(db, body.filas)
    if errors:
        return DemandaBulkResult(count=0, errors=errors)
    db.query(DemandaFila).delete()
    for item in resolved:
        db.add(
            DemandaFila(
                seccional_id=item["seccional_id"],
                oficina_id=item["oficina_id"],
                servicio_id=item["servicio_id"],
                semana=item["semana"],
                dia=item["dia"],
                hora=item["hora"],
                demanda=item["demanda"],
            )
        )
    db.commit()
    return DemandaBulkResult(count=len(resolved), errors=[])


@router.get("/count")
def demanda_count(db: Session = Depends(get_db)):
    return {"total": db.query(DemandaFila).count()}
