from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config_loader import get_or_create_configuracion
from app.database import get_db
from app.schemas import ConfiguracionAvanzadaOut, ConfiguracionAvanzadaUpdate

router = APIRouter(prefix="/api", tags=["configuracion"])


@router.get("/configuracion", response_model=ConfiguracionAvanzadaOut)
def get_configuracion(db: Session = Depends(get_db)):
    return get_or_create_configuracion(db)


@router.put("/configuracion", response_model=ConfiguracionAvanzadaOut)
def update_configuracion(
    body: ConfiguracionAvanzadaUpdate, db: Session = Depends(get_db)
):
    row = get_or_create_configuracion(db)
    row.penalizacion_subpersonal = body.penalizacion_subpersonal
    row.penalizacion_sobrepersonal = body.penalizacion_sobrepersonal
    row.penalizacion_funcionario_utilizado = body.penalizacion_funcionario_utilizado
    row.max_horas_semanales = body.max_horas_semanales
    row.solver_time_limit = body.solver_time_limit
    db.commit()
    db.refresh(row)
    return row
