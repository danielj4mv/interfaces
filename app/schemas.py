from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SeccionalBase(BaseModel):
    nombre: str


class SeccionalCreate(SeccionalBase):
    pass


class SeccionalUpdate(BaseModel):
    nombre: str


class SeccionalOut(SeccionalBase):
    id: int

    class Config:
        from_attributes = True


class OficinaBase(BaseModel):
    nombre: str
    seccional_id: int


class OficinaCreate(OficinaBase):
    pass


class OficinaUpdate(BaseModel):
    nombre: str
    seccional_id: int


class OficinaOut(OficinaBase):
    id: int
    seccional_nombre: Optional[str] = None

    class Config:
        from_attributes = True


class PermisoLaboralIn(BaseModel):
    oficina_id: int
    dia: str
    hora: str


class PermisoLaboralOut(PermisoLaboralIn):
    id: int

    class Config:
        from_attributes = True


class EmpleadoBase(BaseModel):
    nombre: str
    pago_hora: float = Field(gt=0)
    seccional_id: int


class EmpleadoCreate(EmpleadoBase):
    permisos: list[PermisoLaboralIn] = []


class EmpleadoUpdate(BaseModel):
    nombre: str
    pago_hora: float = Field(gt=0)
    seccional_id: int
    permisos: list[PermisoLaboralIn] = []


class EmpleadoOut(EmpleadoBase):
    id: int
    seccional_nombre: Optional[str] = None
    permisos: list[PermisoLaboralOut] = []

    class Config:
        from_attributes = True


class SemanaCreate(BaseModel):
    numero: int = Field(ge=1)


class SemanasSync(BaseModel):
    cantidad: int = Field(ge=1, le=52)


class SemanaOut(BaseModel):
    id: int
    numero: int

    class Config:
        from_attributes = True


class DiaCreate(BaseModel):
    nombre: str
    orden: int


class DiaUpdate(BaseModel):
    nombre: str
    orden: int


class DiaActivoUpdate(BaseModel):
    activo: bool


class DiaOut(BaseModel):
    id: int
    nombre: str
    orden: int
    activo: bool

    class Config:
        from_attributes = True


class JornadaBase(BaseModel):
    nombre: str
    horas: list[str]
    almuerzos: list[str] = []


class JornadaCreate(JornadaBase):
    pass


class JornadaUpdate(JornadaBase):
    pass


class JornadaOut(JornadaBase):
    id: int

    class Config:
        from_attributes = True


class ConfiguracionAvanzadaOut(BaseModel):
    penalizacion_subpersonal: int
    penalizacion_sobrepersonal: int
    penalizacion_funcionario_utilizado: int
    max_horas_semanales: int
    solver_time_limit: int

    class Config:
        from_attributes = True


class ConfiguracionAvanzadaUpdate(BaseModel):
    penalizacion_subpersonal: int = Field(ge=0)
    penalizacion_sobrepersonal: int = Field(ge=0)
    penalizacion_funcionario_utilizado: int = Field(ge=0)
    max_horas_semanales: int = Field(ge=1, le=168)
    solver_time_limit: int = Field(ge=1, le=86400)


class DemandaStatusOut(BaseModel):
    has_file: bool
    filename: Optional[str] = None
    uploaded_at: Optional[datetime] = None


class SimulationRunOut(BaseModel):
    ok: bool
    errors: list[str] = []
    warnings: list[str] = []
    results: Optional[dict] = None
