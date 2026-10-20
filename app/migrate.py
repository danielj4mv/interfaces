from sqlalchemy import inspect, text

from app.database import engine


def _column_names(insp, table: str) -> set[str]:
    if not insp.has_table(table):
        return set()
    return {c["name"] for c in insp.get_columns(table)}


def run_migrations() -> None:
    insp = inspect(engine)
    if not insp.has_table("seccionales"):
        return

    needs_rebuild = False
    if insp.has_table("empleados"):
        cols = _column_names(insp, "empleados")
        if "pago_hora" in cols or "servicio_id" not in cols:
            needs_rebuild = True
    elif not insp.has_table("servicios"):
        needs_rebuild = True

    if insp.has_table("demanda_uploads") or insp.has_table("configuracion_avanzada"):
        needs_rebuild = True

    if not needs_rebuild:
        return

    legacy_tables = [
        "demanda_uploads",
        "configuracion_avanzada",
        "semanas",
        "dias",
        "permisos_laborales",
        "empleados",
        "jornadas",
        "demanda_filas",
        "servicios",
    ]

    with engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys=OFF"))
        for table in legacy_tables:
            if insp.has_table(table):
                conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
        conn.execute(text("PRAGMA foreign_keys=ON"))

    from app.models import Base

    Base.metadata.create_all(bind=engine)
