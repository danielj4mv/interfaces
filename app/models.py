from sqlalchemy import (
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Seccional(Base):
    __tablename__ = "seccionales"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)

    oficinas: Mapped[list["Oficina"]] = relationship(back_populates="seccional")
    servicios: Mapped[list["Servicio"]] = relationship(back_populates="seccional")
    empleados: Mapped[list["Empleado"]] = relationship(back_populates="seccional")


class Servicio(Base):
    __tablename__ = "servicios"
    __table_args__ = (
        UniqueConstraint("seccional_id", "nombre", name="uq_servicio_seccional_nombre"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    seccional_id: Mapped[int] = mapped_column(
        ForeignKey("seccionales.id"), nullable=False
    )

    seccional: Mapped["Seccional"] = relationship(back_populates="servicios")
    empleados: Mapped[list["Empleado"]] = relationship(back_populates="servicio")


class Oficina(Base):
    __tablename__ = "oficinas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    seccional_id: Mapped[int] = mapped_column(
        ForeignKey("seccionales.id"), nullable=False
    )

    seccional: Mapped["Seccional"] = relationship(back_populates="oficinas")
    jornadas: Mapped[list["Jornada"]] = relationship(back_populates="oficina")


class Empleado(Base):
    __tablename__ = "empleados"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    seccional_id: Mapped[int] = mapped_column(
        ForeignKey("seccionales.id"), nullable=False
    )
    servicio_id: Mapped[int] = mapped_column(
        ForeignKey("servicios.id"), nullable=False
    )
    horas_semanales: Mapped[float] = mapped_column(Float, nullable=False)
    dia_descanso: Mapped[int] = mapped_column(Integer, nullable=False)
    modo_horas: Mapped[str] = mapped_column(String(20), nullable=False, default="fixed")
    holgura_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    seccional: Mapped["Seccional"] = relationship(back_populates="empleados")
    servicio: Mapped["Servicio"] = relationship(back_populates="empleados")
    permisos: Mapped[list["PermisoLaboral"]] = relationship(
        back_populates="empleado", cascade="all, delete-orphan"
    )


class PermisoLaboral(Base):
    __tablename__ = "permisos_laborales"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empleado_id: Mapped[int] = mapped_column(
        ForeignKey("empleados.id", ondelete="CASCADE"), nullable=False
    )
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    dia: Mapped[int] = mapped_column(Integer, nullable=False)
    hora_inicio: Mapped[str | None] = mapped_column(String(10), nullable=True)
    hora_fin: Mapped[str | None] = mapped_column(String(10), nullable=True)

    empleado: Mapped["Empleado"] = relationship(back_populates="permisos")


class Jornada(Base):
    __tablename__ = "jornadas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    oficina_id: Mapped[int] = mapped_column(
        ForeignKey("oficinas.id"), nullable=False
    )
    inicio: Mapped[str] = mapped_column(String(10), nullable=False)
    fin: Mapped[str] = mapped_column(String(10), nullable=False)
    break_inicio: Mapped[str | None] = mapped_column(String(10), nullable=True)
    break_fin: Mapped[str | None] = mapped_column(String(10), nullable=True)
    dias_json: Mapped[str] = mapped_column(String(100), nullable=False, default="[]")

    oficina: Mapped["Oficina"] = relationship(back_populates="jornadas")


class DemandaFila(Base):
    __tablename__ = "demanda_filas"
    __table_args__ = (
        UniqueConstraint(
            "oficina_id",
            "servicio_id",
            "semana",
            "dia",
            "hora",
            name="uq_demanda_oficina_servicio_semana_dia_hora",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    seccional_id: Mapped[int] = mapped_column(
        ForeignKey("seccionales.id"), nullable=False
    )
    oficina_id: Mapped[int] = mapped_column(
        ForeignKey("oficinas.id"), nullable=False
    )
    servicio_id: Mapped[int] = mapped_column(
        ForeignKey("servicios.id"), nullable=False
    )
    semana: Mapped[int] = mapped_column(Integer, nullable=False)
    dia: Mapped[int] = mapped_column(Integer, nullable=False)
    hora: Mapped[str] = mapped_column(String(10), nullable=False)
    demanda: Mapped[int] = mapped_column(Integer, nullable=False)
