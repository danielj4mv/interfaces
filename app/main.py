from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.bootstrap import seed_defaults
from app.database import BASE_DIR, SessionLocal, engine
from app.migrate import run_migrations
from app.models import Base
from app.routers import (
    configuracion,
    demanda,
    empleados,
    jornadas,
    oficinas,
    seccionales,
    simulacion,
)

Base.metadata.create_all(bind=engine)
run_migrations()

db = SessionLocal()
try:
    seed_defaults(db)
finally:
    db.close()

app = FastAPI(title="Workforce Planning")

static_dir = BASE_DIR / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

app.include_router(seccionales.router)
app.include_router(oficinas.router)
app.include_router(empleados.router)
app.include_router(jornadas.router)
app.include_router(configuracion.router)
app.include_router(demanda.router)
app.include_router(simulacion.router)


@app.get("/")
def index():
    index_path = static_dir / "index.html"
    return FileResponse(index_path)
