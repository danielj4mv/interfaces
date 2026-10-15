from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Seccional(Base):
    __tablename__ = "seccionales"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)

    oficinas: Mapped[list["Oficina"]] = relationship(back_populates="seccional")
    empleados: Mapped[list["Empleado"]] = relationship(back_populates="seccional")


class Oficina(Base):
    __tablename__ = "oficinas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    seccional_id: Mapped[int] = mapped_column(
        ForeignKey("seccionales.id"), nullable=False
    )

    seccional: Mapped["Seccional"] = relationship(back_populates="oficinas")
    permisos: Mapped[list["PermisoLaboral"]] = relationship(
        back_populates="oficina"
    )


class Empleado(Base):
    __tablename__ = "empleados"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    pago_hora: Mapped[float] = mapped_column(Float, nullable=False)
    seccional_id: Mapped[int] = mapped_column(
        ForeignKey("seccionales.id"), nullable=False
    )

    seccional: Mapped["Seccional"] = relationship(back_populates="empleados")
    permisos: Mapped[list["PermisoLaboral"]] = relationship(
        back_populates="empleado", cascade="all, delete-orphan"
    )


class PermisoLaboral(Base):
    __tablename__ = "permisos_laborales"
    __table_args__ = (
        UniqueConstraint(
            "empleado_id",
            "oficina_id",
            "dia",
            "hora",
            name="uq_permiso_empleado_oficina_dia_hora",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empleado_id: Mapped[int] = mapped_column(
        ForeignKey("empleados.id", ondelete="CASCADE"), nullable=False
    )
    oficina_id: Mapped[int] = mapped_column(
        ForeignKey("oficinas.id"), nullable=False
    )
    dia: Mapped[str] = mapped_column(String(50), nullable=False)
    hora: Mapped[str] = mapped_column(String(10), nullable=False)

    empleado: Mapped["Empleado"] = relationship(back_populates="permisos")
    oficina: Mapped["Oficina"] = relationship(back_populates="permisos")


class Semana(Base):
    __tablename__ = "semanas"
    __table_args__ = (UniqueConstraint("numero", name="uq_semana_numero"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)


class Dia(Base):
    __tablename__ = "dias"
    __table_args__ = (UniqueConstraint("nombre", name="uq_dia_nombre"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(50), nullable=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False)
    activo: Mapped[bool] = mapped_column(nullable=False, default=True)


class Jornada(Base):
    __tablename__ = "jornadas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    horas_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    almuerzos_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")


class ConfiguracionAvanzada(Base):
    __tablename__ = "configuracion_avanzada"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    penalizacion_subpersonal: Mapped[int] = mapped_column(Integer, nullable=False)
    penalizacion_sobrepersonal: Mapped[int] = mapped_column(Integer, nullable=False)
    penalizacion_funcionario_utilizado: Mapped[int] = mapped_column(
        Integer, nullable=False
    )
    max_horas_semanales: Mapped[int] = mapped_column(Integer, nullable=False)
    solver_time_limit: Mapped[int] = mapped_column(Integer, nullable=False)


class DemandaUpload(Base):
    __tablename__ = "demanda_uploads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
