from sqlalchemy.orm import Session


def seed_defaults(db: Session) -> None:
    db.commit()
