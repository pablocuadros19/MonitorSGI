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
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import date, datetime


DATA_DIR = Path(__file__).parent.parent / "data"
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


def borrar_foto_dia(fecha: str) -> bool:
    """Borra el registro de una fecha específica. Retorna True si existía."""
    db = _cargar_db()
    antes = len(db["registros"])
    db["registros"] = [r for r in db["registros"] if r.get("fecha") != fecha]
    if len(db["registros"]) < antes:
        _guardar_db(db)
        return True
    return False


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


def leer_foto_dia_excel(archivo_bytes: bytes) -> dict | None:
    """
    Lee el Excel exportado de BIP Sucursales (Foto del Día).
    Formato conocido: una hoja con secciones Turnos, Oportunidades, Llamados.

    Retorna un dict compatible con guardar_foto_dia(), o None si falla.
    """
    NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

    def _int(val):
        try:
            return int(float(val)) if val is not None else 0
        except (ValueError, TypeError):
            return 0

    try:
        import io
        zf = zipfile.ZipFile(io.BytesIO(archivo_bytes))
        # Buscar la hoja (puede llamarse sheet.xml o sheet1.xml)
        hojas = [n for n in zf.namelist() if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")]
        if not hojas:
            return None
        with zf.open(hojas[0]) as f:
            tree = ET.parse(f)
    except Exception:
        return None

    # Extraer todas las filas con valores
    filas = []
    for row in tree.findall(f".//{NS}row"):
        vals = []
        for c in row.findall(f"{NS}c"):
            v = c.find(f"{NS}v")
            is_elem = c.find(f"{NS}is")
            if is_elem is not None:
                t_elem = is_elem.find(f"{NS}t")
                vals.append(t_elem.text if t_elem is not None else None)
            elif v is not None:
                vals.append(v.text)
            else:
                vals.append(None)
        if any(v is not None for v in vals):
            filas.append(vals)

    # Aplanar a dict por etiqueta para búsqueda fácil
    # Estrategia: recorrer fila a fila buscando labels conocidos
    datos = {}
    fecha_str = str(date.today())

    for i, fila in enumerate(filas):
        etiquetas = [str(v).strip() if v else "" for v in fila]

        # Fecha
        if i == 1 and fila[0]:
            try:
                from datetime import datetime as dt
                fecha_raw = str(fila[0])
                for fmt in ("%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y", "%Y-%m-%d"):
                    try:
                        fecha_str = dt.strptime(fecha_raw[:len(fmt)], fmt).strftime("%Y-%m-%d")
                        break
                    except ValueError:
                        continue
            except Exception:
                pass

        # Scoring (fila con "total de scoring" y "total de turnos")
        if any("total de scoring" in e.lower() for e in etiquetas):
            siguiente = filas[i + 1] if i + 1 < len(filas) else []
            datos["scoring_solicitados"] = _int(siguiente[0] if siguiente else None)
            datos["scoring_turnos"] = _int(siguiente[1] if len(siguiente) > 1 else None)
            datos["scoring_ventas"] = _int(siguiente[2] if len(siguiente) > 2 else None)

        if any("no venta" in e.lower() for e in etiquetas):
            siguiente = filas[i + 1] if i + 1 < len(filas) else []
            datos["scoring_no_ventas"] = _int(siguiente[0] if siguiente else None)
            datos["scoring_pendientes"] = _int(siguiente[1] if len(siguiente) > 1 else None)
            datos["derivaciones_tesoreria"] = _int(siguiente[2] if len(siguiente) > 2 else None)

        # Migas
        if any("migas" in e.lower() and "ingresos" in e.lower() for e in etiquetas):
            siguiente = filas[i + 1] if i + 1 < len(filas) else []
            idx_ing = next((j for j, e in enumerate(etiquetas) if "migas" in e.lower() and "ingresos" in e.lower()), None)
            idx_lla = next((j for j, e in enumerate(etiquetas) if "migas" in e.lower() and "llamados" in e.lower()), None)
            if idx_ing is not None and siguiente:
                datos["migas_ingresos"] = _int(siguiente[idx_ing] if idx_ing < len(siguiente) else None)
            if idx_lla is not None and siguiente:
                datos["migas_llamados"] = _int(siguiente[idx_lla] if idx_lla < len(siguiente) else None)

        # Prospecto Digital
        if any("prosp" in e.lower() and "ingresos" in e.lower() for e in etiquetas):
            siguiente = filas[i + 1] if i + 1 < len(filas) else []
            idx_ing = next((j for j, e in enumerate(etiquetas) if "prosp" in e.lower() and "ingresos" in e.lower()), None)
            idx_lla = next((j for j, e in enumerate(etiquetas) if "prosp" in e.lower() and "llamados" in e.lower()), None)
            if idx_ing is not None and siguiente:
                datos["prospecto_ingresos"] = _int(siguiente[idx_ing] if idx_ing < len(siguiente) else None)
            if idx_lla is not None and siguiente:
                datos["prospecto_llamados"] = _int(siguiente[idx_lla] if idx_lla < len(siguiente) else None)

        # Turno Previo
        if any("turno previo" in e.lower() and "ingresos" in e.lower() for e in etiquetas):
            siguiente = filas[i + 1] if i + 1 < len(filas) else []
            idx_ing = next((j for j, e in enumerate(etiquetas) if "turno previo" in e.lower() and "ingresos" in e.lower()), None)
            idx_lla = next((j for j, e in enumerate(etiquetas) if "turno previo" in e.lower() and "llamados" in e.lower()), None)
            if idx_ing is not None and siguiente:
                datos["turno_previo_ingresos"] = _int(siguiente[idx_ing] if idx_ing < len(siguiente) else None)
            if idx_lla is not None and siguiente:
                datos["turno_previo_llamados"] = _int(siguiente[idx_lla] if idx_lla < len(siguiente) else None)

        # Campañas
        if any("campan" in e.lower() and "disponible" in e.lower() for e in etiquetas):
            siguiente = filas[i + 1] if i + 1 < len(filas) else []
            idx_disp = next((j for j, e in enumerate(etiquetas) if "campan" in e.lower() and "disponible" in e.lower()), None)
            idx_lla = next((j for j, e in enumerate(etiquetas) if "campan" in e.lower() and "llamados" in e.lower()), None)
            if idx_disp is not None and siguiente:
                datos["campanas_disponibles"] = _int(siguiente[idx_disp] if idx_disp < len(siguiente) else None)
            if idx_lla is not None and siguiente:
                datos["campanas_llamados"] = _int(siguiente[idx_lla] if idx_lla < len(siguiente) else None)

    if not datos:
        return None

    datos["fecha"] = fecha_str
    datos.setdefault("scoring_solicitados", 0)
    datos.setdefault("scoring_turnos", 0)
    datos.setdefault("scoring_ventas", 0)
    datos.setdefault("scoring_no_ventas", 0)
    datos.setdefault("scoring_pendientes", 0)
    datos.setdefault("prospecto_ingresos", 0)
    datos.setdefault("prospecto_llamados", 0)
    datos.setdefault("prospecto_gestionados", 0)
    datos.setdefault("turno_previo_ingresos", 0)
    datos.setdefault("turno_previo_llamados", 0)
    datos.setdefault("turno_previo_gestionados", 0)
    datos.setdefault("campanas_disponibles", 0)
    datos.setdefault("campanas_llamados", 0)
    datos.setdefault("campanas_gestionados", 0)
    datos.setdefault("migas_ingresos", 0)
    datos.setdefault("migas_llamados", 0)
    datos.setdefault("derivaciones_tesoreria", 0)
    datos.setdefault("observaciones", "")
    return datos
