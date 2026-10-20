DIA_NOMBRES = {
    1: "Lunes",
    2: "Martes",
    3: "Miércoles",
    4: "Jueves",
    5: "Viernes",
    6: "Sábado",
    7: "Domingo",
}

DIA_ALIASES = {
    "lunes": 1,
    "martes": 2,
    "miercoles": 3,
    "miércoles": 3,
    "jueves": 4,
    "viernes": 5,
    "sabado": 6,
    "sábado": 6,
    "domingo": 7,
}


def parse_dia(value: int | str) -> int | None:
    if isinstance(value, int) or (isinstance(value, str) and value.isdigit()):
        n = int(value)
        return n if 1 <= n <= 7 else None
    if isinstance(value, str):
        return DIA_ALIASES.get(value.strip().lower())
    return None


def dia_nombre(dia: int) -> str:
    return DIA_NOMBRES.get(dia, str(dia))
