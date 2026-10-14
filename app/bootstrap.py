import json

from sqlalchemy.orm import Session

from app.models import Dia, Jornada, Semana

DEFAULT_DIAS = [
    ("Lunes", 1),
    ("Martes", 2),
    ("Miercoles", 3),
    ("Jueves", 4),
    ("Viernes", 5),
    ("Sabado", 6),
    ("Domingo", 7),
]

DEFAULT_JORNADAS = [
    (
        "Jornada1",
        ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00"],
        ["12:00", "13:00", "14:00"],
    ),
    (
        "Jornada2",
        ["10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00"],
        ["13:00", "14:00"],
    ),
    (
        "Jornada3",
        ["12:00", "13:00", "14:00", "15:00", "16:00"],
        [],
    ),
]


def seed_defaults(db: Session) -> None:
    for nombre, orden in DEFAULT_DIAS:
        if not db.query(Dia).filter(Dia.nombre == nombre).first():
            db.add(Dia(nombre=nombre, orden=orden, activo=True))

    if db.query(Semana).count() == 0:
        db.add(Semana(numero=1))

    if db.query(Jornada).count() == 0:
        for nombre, horas, almuerzos in DEFAULT_JORNADAS:
            db.add(
                Jornada(
                    nombre=nombre,
                    horas_json=json.dumps(horas),
                    almuerzos_json=json.dumps(almuerzos),
                )
            )

    db.commit()
