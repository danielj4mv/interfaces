from sqlalchemy import inspect, text

from app.database import engine


def run_migrations() -> None:
    insp = inspect(engine)
    if not insp.has_table("dias"):
        return
    cols = {c["name"] for c in insp.get_columns("dias")}
    if "activo" not in cols:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE dias ADD COLUMN activo BOOLEAN NOT NULL DEFAULT 1"
                )
            )
