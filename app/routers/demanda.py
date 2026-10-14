from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.database import BASE_DIR, get_db
from app.models import DemandaUpload
from app.schemas import DemandaStatusOut

router = APIRouter(prefix="/api/demanda", tags=["demanda"])

UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_PATH = UPLOAD_DIR / "demanda.xlsx"


@router.get("/status", response_model=DemandaStatusOut)
def demanda_status(db: Session = Depends(get_db)):
    latest = (
        db.query(DemandaUpload).order_by(DemandaUpload.uploaded_at.desc()).first()
    )
    if not latest or not Path(latest.stored_path).is_file():
        return DemandaStatusOut(has_file=False)
    return DemandaStatusOut(
        has_file=True,
        filename=latest.filename,
        uploaded_at=latest.uploaded_at,
    )


@router.post("/upload", response_model=DemandaStatusOut)
async def upload_demanda(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="El archivo debe ser Excel (.xlsx).")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    content = await file.read()
    UPLOAD_PATH.write_bytes(content)

    row = DemandaUpload(
        filename=file.filename,
        stored_path=str(UPLOAD_PATH),
        uploaded_at=datetime.utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return DemandaStatusOut(
        has_file=True,
        filename=row.filename,
        uploaded_at=row.uploaded_at,
    )
