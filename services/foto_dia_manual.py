"""
Gestión de carga manual de la Foto del Día.
La Foto del Día se muestra en BIP Sucursales a las 16:30 pero no exporta archivo.
Pablo copia los números a un formulario en la app y se guardan en JSON.

Datos que trae la Foto del Día:
- OPORTUNIDADES: Scorings solicitados/Turnos, Ventas, No ventas, Pendientes
- LLAMADOS: Prospecto Digital (ingresos, llamados, gestionados)
              Turno Previo (ingresos, llamados, gestionados)
              Campañas (datos disponibles, llamados, gestionados)
"""
import json
from pathlib import Path
from datetime import date, datetime


DATA_DIR = Path("C:/PRUEBITAS/data")
ARCHIVO_DIARIO = DATA_DIR / "fotos_dia.json"


def _cargar_db() -> dict:
    if ARCHIVO_DIARIO.exists():
        with open(ARCHIVO_DIARIO, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"registros": []}


def _guardar_db(db: dict):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(ARCHIVO_DIARIO, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2, default=str)


def guardar_foto_dia(datos: dict) -> bool:
    """
    Guarda un registro de Foto del Día.

    datos debe tener:
        fecha: str (YYYY-MM-DD)
        scoring_solicitados: int
        scoring_turnos: int
        scoring_ventas: int
        scoring_no_ventas: int
        scoring_pendientes: int
        prospecto_ingresos: int
        prospecto_llamados: int
        prospecto_gestionados: int
        turno_previo_ingresos: int
        turno_previo_llamados: int
        turno_previo_gestionados: int
        campanas_disponibles: int
        campanas_llamados: int
        campanas_gestionados: int
        derivaciones_tesoreria: int
        observaciones: str
    """
    db = _cargar_db()

    # Si ya existe registro para esa fecha, actualizar
    fecha = datos.get("fecha", str(date.today()))
    existente = next((r for r in db["registros"] if r["fecha"] == fecha), None)

    if existente:
        existente.update(datos)
    else:
        datos["fecha"] = fecha
        datos["timestamp"] = datetime.now().isoformat()
        db["registros"].append(datos)

    _guardar_db(db)
    return True


def obtener_acumulado_mes(mes: int = None, anio: int = None) -> dict:
    """
    Suma todos los registros del mes para construir el acumulado.

    Returns:
        {
            "scoring_solicitados": int,
            "scoring_turnos": int,
            "scoring_ventas": int,
            "prospecto_ingresos": int,
            "prospecto_gestionados": int,
            "turno_previo_ingresos": int,
            "turno_previo_gestionados": int,
            "campanas_disponibles": int,
            "campanas_gestionados": int,
            "derivaciones_tesoreria": int,
            "dias_cargados": int,
            "ultimo_dia": str | None,
            "registros": list[dict],
        }
    """
    hoy = date.today()
    mes = mes or hoy.month
    anio = anio or hoy.year

    db = _cargar_db()

    campos_suma = [
        "scoring_solicitados", "scoring_turnos", "scoring_ventas",
        "scoring_no_ventas", "scoring_pendientes",
        "prospecto_ingresos", "prospecto_llamados", "prospecto_gestionados",
        "turno_previo_ingresos", "turno_previo_llamados", "turno_previo_gestionados",
        "campanas_disponibles", "campanas_llamados", "campanas_gestionados",
        "migas_ingresos", "migas_llamados",
        "derivaciones_tesoreria",
    ]

    acum = {c: 0 for c in campos_suma}
    acum["dias_cargados"] = 0
    acum["ultimo_dia"] = None
    acum["registros"] = []

    for reg in db.get("registros", []):
        try:
            fecha = date.fromisoformat(reg["fecha"])
        except (ValueError, KeyError):
            continue

        if fecha.month == mes and fecha.year == anio:
            for campo in campos_suma:
                acum[campo] += reg.get(campo, 0) or 0
            acum["dias_cargados"] += 1
            acum["registros"].append(reg)
            if acum["ultimo_dia"] is None or reg["fecha"] > acum["ultimo_dia"]:
                acum["ultimo_dia"] = reg["fecha"]

    return acum


def obtener_registro_fecha(fecha: str) -> dict | None:
    """Retorna el registro de una fecha específica."""
    db = _cargar_db()
    return next((r for r in db.get("registros", []) if r.get("fecha") == fecha), None)


def enriquecer_indicadores_con_foto(indicadores: dict, mes: int = None, anio: int = None) -> dict:
    """
    Para indicadores "pendiente" en el FDM, completa con acumulado de fotos del día manuales.
    """
    acum = obtener_acumulado_mes(mes, anio)

    if acum["dias_cargados"] == 0:
        return indicadores

    # Scoring: scoring_solicitados / scoring_turnos
    if "scoring" in indicadores and indicadores["scoring"]["estado"] == "pendiente":
        den = acum["scoring_turnos"]
        num = acum["scoring_solicitados"]
        if den > 0:
            indicadores["scoring"]["suc_num"] = num
            indicadores["scoring"]["suc_den"] = den
            indicadores["scoring"]["suc_ratio"] = num / den
            indicadores["scoring"]["fuente"] = "foto_diaria"

    # Activación digital: no sale directamente de la foto del día (sale de remediación/scoring)
    # Se puede agregar cuando se confirme qué campo usar

    return indicadores
