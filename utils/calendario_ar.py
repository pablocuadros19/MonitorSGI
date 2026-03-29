"""
Días hábiles de Argentina.
Feriados nacionales hardcodeados por año. Actualizar al inicio de cada año.
"""
from datetime import date, timedelta
import calendar

# Feriados nacionales Argentina
# Fuente: https://www.argentina.gob.ar/interior/feriados
FERIADOS = {
    2025: [
        date(2025, 1, 1),    # Año Nuevo
        date(2025, 3, 3),    # Carnaval
        date(2025, 3, 4),    # Carnaval
        date(2025, 3, 24),   # Día de la Memoria
        date(2025, 4, 2),    # Día del Veterano / Malvinas
        date(2025, 4, 18),   # Viernes Santo
        date(2025, 5, 1),    # Día del Trabajador
        date(2025, 5, 2),    # Feriado puente turístico
        date(2025, 5, 25),   # Revolución de Mayo
        date(2025, 6, 16),   # Paso a la Inmortalidad Güemes (trasladado)
        date(2025, 6, 20),   # Día de la Bandera
        date(2025, 7, 9),    # Día de la Independencia
        date(2025, 8, 15),   # Feriado puente turístico
        date(2025, 8, 17),   # Paso a la Inmortalidad San Martín (trasladado)
        date(2025, 10, 12),  # Día del Respeto a la Diversidad Cultural
        date(2025, 11, 21),  # Feriado puente turístico
        date(2025, 11, 24),  # Día de la Soberanía Nacional (trasladado)
        date(2025, 12, 8),   # Inmaculada Concepción
        date(2025, 12, 25),  # Navidad
    ],
    2026: [
        date(2026, 1, 1),    # Año Nuevo
        date(2026, 2, 16),   # Carnaval
        date(2026, 2, 17),   # Carnaval
        date(2026, 3, 24),   # Día de la Memoria
        date(2026, 4, 2),    # Día del Veterano / Malvinas
        date(2026, 4, 3),    # Viernes Santo
        date(2026, 5, 1),    # Día del Trabajador
        date(2026, 5, 25),   # Revolución de Mayo
        date(2026, 6, 15),   # Paso a la Inmortalidad Güemes (trasladado)
        date(2026, 6, 20),   # Día de la Bandera
        date(2026, 7, 9),    # Día de la Independencia
        date(2026, 8, 17),   # Paso a la Inmortalidad San Martín
        date(2026, 10, 12),  # Día del Respeto a la Diversidad Cultural
        date(2026, 11, 23),  # Día de la Soberanía Nacional (trasladado)
        date(2026, 12, 7),   # Feriado puente turístico
        date(2026, 12, 8),   # Inmaculada Concepción
        date(2026, 12, 25),  # Navidad
    ],
}


def _feriados_set(anio: int) -> set[date]:
    return set(FERIADOS.get(anio, []))


def dias_habiles_mes(mes: int, anio: int) -> list[date]:
    """Retorna lista ordenada de días hábiles del mes (lun-vie, no feriados)."""
    feriados = _feriados_set(anio)
    total_dias = calendar.monthrange(anio, mes)[1]
    habiles = []
    for dia in range(1, total_dias + 1):
        d = date(anio, mes, dia)
        if d.weekday() < 5 and d not in feriados:  # lun=0 ... vie=4
            habiles.append(d)
    return habiles


def dias_sin_cargar(mes: int, anio: int, fechas_cargadas: list[str]) -> list[date]:
    """Retorna días hábiles del mes que no fueron cargados."""
    habiles = dias_habiles_mes(mes, anio)
    cargados = set(fechas_cargadas)
    return [d for d in habiles if d.isoformat() not in cargados]


def hoy_es_habil() -> bool:
    """True si hoy es día hábil."""
    hoy = date.today()
    feriados = _feriados_set(hoy.year)
    return hoy.weekday() < 5 and hoy not in feriados
