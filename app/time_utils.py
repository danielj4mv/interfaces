import re

TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})$")


def normalize_hhmm(value: str) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    m = TIME_RE.match(text)
    if not m:
        return None
    hour, minute = int(m.group(1)), int(m.group(2))
    if minute not in (0, 30):
        return None
    if hour == 24 and minute == 0:
        return "24:00"
    if not (0 <= hour < 24):
        return None
    return f"{hour:02d}:{minute:02d}"


def validate_jornada_times(
    inicio: str,
    fin: str,
    break_inicio: str | None,
    break_fin: str | None,
) -> str | None:
    ini = normalize_hhmm(inicio)
    end = normalize_hhmm(fin)
    if not ini or not end:
        return "inicio y fin deben estar en formato HH:MM (:00 o :30)."
    bi = normalize_hhmm(break_inicio or "")
    bf = normalize_hhmm(break_fin or "")
    if (break_inicio or break_fin) and (not bi or not bf):
        if break_inicio and not break_fin:
            return "Si define inicio de descanso, defina también fin de descanso."
        if break_fin and not break_inicio:
            return "Si define fin de descanso, defina también inicio de descanso."
        return "Horas de descanso inválidas (HH:MM, :00 o :30)."
    if not break_inicio and not break_fin:
        bi = bf = None
    return None
