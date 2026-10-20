from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


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


class ServicioBase(BaseModel):
    nombre: str
    seccional_id: int


class ServicioCreate(ServicioBase):
    pass


class ServicioUpdate(BaseModel):
    nombre: str
    seccional_id: int


class ServicioOut(ServicioBase):
    id: int
    seccional_nombre: Optional[str] = None

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
    tipo: Literal["dia_completo", "horas"]
    dia: int = Field(ge=1, le=7)
    hora_inicio: Optional[str] = None
    hora_fin: Optional[str] = None

    @model_validator(mode="after")
    def validate_horas(self):
        if self.tipo == "horas":
            if not self.hora_inicio or not self.hora_fin:
                raise ValueError(
                    "hora_inicio y hora_fin son obligatorias para permisos por horas."
                )
        elif self.hora_inicio or self.hora_fin:
            raise ValueError(
                "hora_inicio y hora_fin solo aplican a permisos por horas."
            )
        return self


class PermisoLaboralOut(PermisoLaboralIn):
    id: int

    class Config:
        from_attributes = True


class EmpleadoBase(BaseModel):
    nombre: str
    seccional_id: int
    servicio_id: int
    horas_semanales: float = Field(gt=0)
    dia_descanso: int = Field(ge=1, le=7)
    modo_horas: Literal["fixed", "flexible"] = "fixed"
    holgura_pct: float = Field(ge=0, default=0.0)

    @field_validator("horas_semanales")
    @classmethod
    def half_hour_multiple(cls, v: float) -> float:
        if abs(v * 2 - round(v * 2)) > 1e-7:
            raise ValueError("horas_semanales debe ser múltiplo de 0.5")
        return v

    @model_validator(mode="after")
    def validate_flexible(self):
        if self.modo_horas == "fixed" and self.holgura_pct != 0:
            raise ValueError("holgura_pct solo aplica en modo flexible.")
        return self


class EmpleadoCreate(EmpleadoBase):
    permisos: list[PermisoLaboralIn] = []


class EmpleadoUpdate(BaseModel):
    nombre: str
    seccional_id: int
    servicio_id: int
    horas_semanales: float = Field(gt=0)
    dia_descanso: int = Field(ge=1, le=7)
    modo_horas: Literal["fixed", "flexible"] = "fixed"
    holgura_pct: float = Field(ge=0, default=0.0)
    permisos: list[PermisoLaboralIn] = []

    @field_validator("horas_semanales")
    @classmethod
    def half_hour_multiple(cls, v: float) -> float:
        if abs(v * 2 - round(v * 2)) > 1e-7:
            raise ValueError("horas_semanales debe ser múltiplo de 0.5")
        return v


class EmpleadoOut(EmpleadoBase):
    id: int
    seccional_nombre: Optional[str] = None
    servicio_nombre: Optional[str] = None
    permisos: list[PermisoLaboralOut] = []

    class Config:
        from_attributes = True


class JornadaBase(BaseModel):
    oficina_id: int
    inicio: str
    fin: str
    break_inicio: Optional[str] = None
    break_fin: Optional[str] = None
    dias: list[int] = Field(min_length=1)

    @field_validator("dias")
    @classmethod
    def validate_dias(cls, v: list[int]) -> list[int]:
        for d in v:
            if d < 1 or d > 7:
                raise ValueError("dias debe contener valores entre 1 y 7.")
        return sorted(set(v))


class JornadaCreate(JornadaBase):
    pass


class JornadaUpdate(JornadaBase):
    pass


class JornadaOut(JornadaBase):
    id: int
    oficina_nombre: Optional[str] = None
    seccional_nombre: Optional[str] = None

    class Config:
        from_attributes = True


class DemandaFilaIn(BaseModel):
    seccional: str
    oficina: str
    servicio: str
    semana: int = Field(ge=1)
    dia: int | str
    hora: str
    demanda: int = Field(ge=0)


class DemandaBulkIn(BaseModel):
    filas: list[DemandaFilaIn]


class DemandaFilaOut(BaseModel):
    id: int
    seccional: str
    oficina: str
    servicio: str
    semana: int
    dia: int
    hora: str
    demanda: int

    class Config:
        from_attributes = True


class DemandaBulkResult(BaseModel):
    count: int
    errors: list[str] = []


class DemandaListOut(BaseModel):
    filas: list[DemandaFilaOut]
    total: int
