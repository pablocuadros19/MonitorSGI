"""
Lee la Foto del Día y el Listado de Atendidos.

IMPORTANTE: Los formatos exactos se definen cuando Pablo traiga los archivos
el lunes 30/03. Este módulo tiene la estructura preparada con auto-detección.

Lógica de acumulación mensual:
- Cada foto del día trae solo datos del DÍA (no acumulado)
- La app suma todas las fotos del mes en diario/ para construir el mes-a-la-fecha
- Si el FDM ya tiene dato oficial para un indicador, el FDM tiene precedencia
"""
import pandas as pd
import json
import warnings
from pathlib import Path
from datetime import datetime, date

warnings.filterwarnings("ignore")

DIRECTORIO_DIARIO = "C:/PRUEBITAS/diario"
CACHE_FILE = "C:/PRUEBITAS/data/acumulado_mensual.json"


# ─── FOTO DEL DÍA ────────────────────────────────────────────────────────────

def detectar_columnas_foto(df: pd.DataFrame) -> dict:
    """
    Auto-detecta qué columnas de la foto del día corresponden a qué indicador.
    Busca por nombre de columna (case-insensitive).
    """
    columnas = {}
    for i, col in enumerate(df.columns):
        col_str = str(col).lower().strip()
        if "scoring" in col_str or "scoreado" in col_str:
            columnas["scoring_num"] = i
        elif "atendido" in col_str:
            columnas["scoring_den"] = i
        elif "activac" in col_str or "digital" in col_str or "bip" in col_str:
            columnas["activacion_num"] = i
        elif "digitaliz" in col_str:
            columnas["activacion_den"] = i
        elif "remediaci" in col_str or "dato" in col_str and "complet" in col_str:
            columnas["remediacion_num"] = i
        elif "alerta" in col_str:
            columnas["remediacion_den"] = i
        elif "campaña" in col_str or "prospecto" in col_str:
            columnas["campanas_num"] = i
    return columnas


def leer_foto_dia(archivo: str) -> dict | None:
    """
    Lee una foto del día y extrae los indicadores disponibles.

    Returns:
        {
            "fecha": date,
            "scoring_num": int | None,     # scoreados
            "scoring_den": int | None,     # atendidos
            "activacion_num": int | None,  # activados digitales
            "activacion_den": int | None,  # digitalizables
            "remediacion_num": int | None, # datos completados
            "remediacion_den": int | None, # alertas emitidas
            "raw": dict,                   # todos los datos crudos
        }
    """
    ext = Path(archivo).suffix.lower()
    try:
        if ext in (".xlsx", ".xls"):
            df = pd.read_excel(archivo)
        elif ext == ".csv":
            df = pd.read_csv(archivo, encoding="utf-8", errors="replace")
        else:
            return None
    except Exception:
        return None

    # Extraer fecha del nombre del archivo o del contenido
    fecha = _extraer_fecha_de_nombre(archivo)

    # Auto-detectar columnas
    cols = detectar_columnas_foto(df)

    def get_val(col_key):
        if col_key not in cols:
            return None
        try:
            val = df.iloc[0, cols[col_key]]
            return int(val) if pd.notna(val) else None
        except Exception:
            return None

    return {
        "fecha": fecha,
        "scoring_num": get_val("scoring_num"),
        "scoring_den": get_val("scoring_den"),
        "activacion_num": get_val("activacion_num"),
        "activacion_den": get_val("activacion_den"),
        "remediacion_num": get_val("remediacion_num"),
        "remediacion_den": get_val("remediacion_den"),
        "raw": df.to_dict("records"),
    }


# ─── LISTADO DE ATENDIDOS ─────────────────────────────────────────────────────

def leer_atendidos(archivo: str) -> list[dict] | None:
    """
    Lee el listado de clientes atendidos en el día.

    Returns:
        Lista de dicts con datos del cliente:
        [{"nombre": str, "dni": str, "telefono": str, "email": str, ...}]
    """
    ext = Path(archivo).suffix.lower()
    try:
        if ext in (".xlsx", ".xls"):
            df = pd.read_excel(archivo)
        elif ext == ".csv":
            df = pd.read_csv(archivo, encoding="utf-8", errors="replace")
        else:
            return None
    except Exception:
        return None

    if df.empty:
        return []

    # Normalizar nombres de columnas
    df.columns = [str(c).strip().lower() for c in df.columns]

    clientes = []
    for _, row in df.iterrows():
        cliente = {
            "nombre": _get_col(row, ["nombre", "apellido_nombre", "cliente", "apellido y nombre"]),
            "dni": _get_col(row, ["dni", "documento", "nro_doc", "nro documento"]),
            "cuil": _get_col(row, ["cuil", "cuit", "cuil_cuit"]),
            "telefono": _get_col(row, ["telefono", "tel", "celular", "teléfono"]),
            "email": _get_col(row, ["email", "mail", "correo"]),
            "sector": _get_col(row, ["sector", "area", "tipo_atencion", "tipo atención"]),
            "hora": _get_col(row, ["hora", "hora_atencion", "hora atención"]),
            "raw": row.to_dict(),
        }
        clientes.append(cliente)

    return clientes


# ─── CRUCE ATENDIDOS × TARJETAS ───────────────────────────────────────────────

def cruzar_con_tarjetas(atendidos: list[dict], stock_tarjetas: list[dict]) -> dict:
    """
    Cruza el listado de atendidos con el stock de tarjetas.

    Args:
        atendidos: lista de leer_atendidos()
        stock_tarjetas: lista de clientes con tarjetas en stock
                        [{"nombre": str, "dni": str, "tipo_tarjeta": str, ...}]

    Returns:
        {
            "total_atendidos": int,
            "con_tarjeta_entregable": int,
            "entregadas": int,       # las que ya se entregaron (si el stock lo indica)
            "pendientes": list[dict] # clientes que vinieron y tienen tarjeta sin entregar
        }
    """
    # Construir índice de tarjetas por DNI
    tarjetas_por_dni = {}
    for t in stock_tarjetas:
        dni = str(t.get("dni", "")).strip()
        if dni:
            tarjetas_por_dni[dni] = t

    pendientes = []
    con_tarjeta = 0

    for cliente in atendidos:
        dni = str(cliente.get("dni", "")).strip()
        if dni and dni in tarjetas_por_dni:
            con_tarjeta += 1
            tarjeta = tarjetas_por_dni[dni]
            # Verificar si ya fue entregada
            entregada = tarjeta.get("entregada", False) or tarjeta.get("estado", "").lower() == "entregada"
            if not entregada:
                pendientes.append({
                    "nombre": cliente.get("nombre", ""),
                    "dni": dni,
                    "telefono": cliente.get("telefono", ""),
                    "email": cliente.get("email", ""),
                    "tipo_tarjeta": tarjeta.get("tipo_tarjeta", ""),
                    "producto": tarjeta.get("producto", ""),
                    "dias_en_stock": tarjeta.get("dias_en_stock", ""),
                })

    return {
        "total_atendidos": len(atendidos),
        "con_tarjeta_entregable": con_tarjeta,
        "entregadas": con_tarjeta - len(pendientes),
        "pendientes": pendientes,
    }


# ─── ACUMULADO MENSUAL ────────────────────────────────────────────────────────

def calcular_acumulado_mensual(directorio: str = DIRECTORIO_DIARIO, mes: int = None, anio: int = None) -> dict:
    """
    Suma todas las fotos del día del mes para construir el acumulado mes-a-la-fecha.

    Returns:
        {
            "scoring_num": int, "scoring_den": int,
            "activacion_num": int, "activacion_den": int,
            "remediacion_num": int, "remediacion_den": int,
            "dias_cargados": int,
            "ultimo_dia": date | None,
        }
    """
    hoy = date.today()
    mes = mes or hoy.month
    anio = anio or hoy.year

    acumulado = {
        "scoring_num": 0, "scoring_den": 0,
        "activacion_num": 0, "activacion_den": 0,
        "remediacion_num": 0, "remediacion_den": 0,
        "dias_cargados": 0,
        "ultimo_dia": None,
    }

    path = Path(directorio)
    if not path.exists():
        return acumulado

    archivos = sorted(path.glob("*.xlsx")) + sorted(path.glob("*.xls")) + sorted(path.glob("*.csv"))

    for archivo in archivos:
        fecha = _extraer_fecha_de_nombre(str(archivo))
        if fecha and fecha.month == mes and fecha.year == anio:
            foto = leer_foto_dia(str(archivo))
            if foto:
                for key in ["scoring_num", "scoring_den", "activacion_num", "activacion_den",
                            "remediacion_num", "remediacion_den"]:
                    if foto.get(key) is not None:
                        acumulado[key] += foto[key]
                acumulado["dias_cargados"] += 1
                if acumulado["ultimo_dia"] is None or fecha > acumulado["ultimo_dia"]:
                    acumulado["ultimo_dia"] = fecha

    return acumulado


def enriquecer_con_foto_diaria(indicadores: dict, directorio: str = DIRECTORIO_DIARIO) -> dict:
    """
    Para indicadores "pendiente" en el FDM, intenta completarlos con el acumulado diario.

    Modifica el dict de indicadores in-place y lo retorna.
    """
    acum = calcular_acumulado_mensual(directorio)

    if acum["dias_cargados"] == 0:
        return indicadores

    enriquecibles = {
        "scoring": ("scoring_num", "scoring_den"),
        "activacion_digital": ("activacion_num", "activacion_den"),
        "remediacion": ("remediacion_num", "remediacion_den"),
    }

    for ind_id, (key_num, key_den) in enriquecibles.items():
        if ind_id not in indicadores:
            continue
        ind = indicadores[ind_id]
        if ind["estado"] != "pendiente":
            continue  # FDM ya tiene dato, no tocar

        num = acum.get(key_num, 0)
        den = acum.get(key_den, 0)

        if den and den > 0:
            ind["suc_num"] = num
            ind["suc_den"] = den
            ind["suc_ratio"] = num / den
            ind["fuente"] = "foto_diaria"
            # Estado queda "pendiente" hasta tener promedio banco para comparar

    return indicadores


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def _extraer_fecha_de_nombre(nombre_archivo: str) -> date | None:
    """Extrae la fecha del nombre del archivo. Ej: 2026-03-29_foto.xlsx → date(2026,3,29)"""
    from pathlib import Path
    stem = Path(nombre_archivo).stem
    # Probar formatos comunes
    formatos = ["%Y-%m-%d", "%d-%m-%Y", "%Y%m%d", "%d%m%Y"]
    partes = stem.replace("_", "-").replace(" ", "-").split("-")
    for fmt in formatos:
        for i in range(len(partes) - 2):
            try:
                candidato = "-".join(partes[i:i+3])
                return datetime.strptime(candidato, "%Y-%m-%d").date()
            except ValueError:
                pass
    return None


def _get_col(row, posibles: list):
    """Obtiene el valor de la primera columna que exista en el row."""
    for nombre in posibles:
        if nombre in row.index:
            val = row[nombre]
            return str(val).strip() if pd.notna(val) else None
    return None


def leer_stock_tarjetas(archivo: str) -> list[dict]:
    """
    Lee el stock de tarjetas. Formato TBD cuando llegue el archivo.
    Por ahora retorna lista vacía si no puede leer.
    """
    try:
        ext = Path(archivo).suffix.lower()
        if ext in (".xlsx", ".xls"):
            df = pd.read_excel(archivo)
        elif ext == ".csv":
            df = pd.read_csv(archivo, encoding="utf-8", errors="replace")
        else:
            return []
        df.columns = [str(c).strip().lower() for c in df.columns]
        return df.to_dict("records")
    except Exception:
        return []
