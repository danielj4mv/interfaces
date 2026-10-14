from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config_loader import load_solver_config
from app.database import BASE_DIR, get_db
from app.models import DemandaUpload
from app.schemas import SimulationRunOut
from app.solver import run_simulation

router = APIRouter(prefix="/api/simulacion", tags=["simulacion"])

UPLOAD_PATH = BASE_DIR / "uploads" / "demanda.xlsx"


def _latest_demanda_path(db: Session) -> Path | None:
    latest = (
        db.query(DemandaUpload).order_by(DemandaUpload.uploaded_at.desc()).first()
    )
    if latest and Path(latest.stored_path).is_file():
        return Path(latest.stored_path)
    if UPLOAD_PATH.is_file():
        return UPLOAD_PATH
    return None


@router.post("/ejecutar", response_model=SimulationRunOut)
def ejecutar_simulacion(db: Session = Depends(get_db)):
    path = _latest_demanda_path(db)
    if not path:
        return SimulationRunOut(
            ok=False,
            errors=["Debe cargar un archivo Excel de demanda antes de simular."],
        )

    config = load_solver_config(db)
    outcome = run_simulation(config, path)
    warnings = outcome.get("warnings", [])
    results = outcome.get("results")
    if results and isinstance(results, dict):
        # Surface capacity warnings from diagnostico
        for item in results.get("diagnostico_capacidad", []):
            if item.get("imposible"):
                warnings.append(
                    f"Seccional {item['seccional']}: faltan aprox. "
                    f"{item.get('faltan_horas', 0)} horas de capacidad."
                )

    return SimulationRunOut(
        ok=outcome["ok"],
        errors=outcome.get("errors", []),
        warnings=warnings,
        results=results,
    )
