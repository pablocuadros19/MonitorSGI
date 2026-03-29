"""
Lee el FDM Provisorio/Final (xlsx o xlsb) y extrae los indicadores de Villa Ballester.

Columnas verificadas empíricamente en el FDM Provisorio 26-03-2026.
Los indicadores "Pendiente" retornan None en sus valores numéricos.
"""
import re
import pandas as pd
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

CU = 5155
CU_STR = "5155"

# Mapa de indicadores: hoja → metadatos y columnas exactas
# col_suc_den  = denominador de la sucursal (ingresados, atendidos, etc.)
# col_suc_num  = numerador de la sucursal (convertidos, gestionados, etc.)
# col_suc_ratio = ratio calculado de la sucursal
# col_banco    = promedio banco (mismo ratio)
# Todos son índices 0-based de la fila de Villa Ballester

INDICADORES_MAP = {
    "turno_previo": {
        "label": "Turnos Previos",
        "pilar": "Individuos",
        "hoja": "Turno previo",
        "col_suc_den": 6,    # turnos web
        "col_suc_num": 7,    # gestionados
        "col_suc_ratio": 8,  # gestionados/turnos web (sucursal)
        "col_banco": 9,      # promedio banco
        "label_num": "Gestionados",
        "label_den": "Turnos web",
        "invert": False,
        "simulable": False,
    },
    "campanas_ind": {
        "label": "Campañas Comerciales IND",
        "pilar": "Individuos",
        "hoja": "Campañas comerciales (IND)",
        "col_suc_den": 6,     # ingresados
        "col_suc_num": None,  # sin columna explícita de convertidos IND
        "col_suc_ratio": None,# suc_ratio se fuerza a 0 (FDM no expone el ratio de suc aquí)
        "col_banco": 12,      # col 12 = promedio banco conversión (2.9%)
        "label_num": "Convertidos",
        "label_den": "Ingresados",
        "invert": False,
        "simulable": True,
        # suc_ratio se setea a 0.0 por defecto hasta tener foto del día
    },
    "campanas_emp": {
        "label": "Campañas Comerciales EMP",
        "pilar": "Empresas",
        "hoja": "Campañas comerciales (EMP)",
        "col_suc_den": 6,    # ingresados
        "col_suc_num": 8,    # convertidos
        "col_suc_ratio": 10, # convertidos/ingresados (sucursal)
        "col_banco": 12,     # promedio banco
        "label_num": "Convertidos",
        "label_den": "Ingresados",
        "invert": False,
        "simulable": True,
    },
    "prospecto_ind": {
        "label": "Prospectos Digitales IND",
        "pilar": "Individuos",
        "hoja": "Prospecto digital (IND)",
        "col_suc_den": 6,    # ingresados
        "col_suc_num": None, # convertidos = ratio × den
        "col_suc_ratio": 11, # convertidos/ingresados (sucursal)
        "col_banco": 13,     # promedio banco conversión
        "label_num": "Convertidos",
        "label_den": "Ingresados",
        "invert": False,
        "simulable": True,
    },
    "prospecto_emp": {
        "label": "Prospectos Digitales EMP",
        "pilar": "Empresas",
        "hoja": "Prospecto digital (EMP)",
        "col_suc_den": 6,    # ingresados
        "col_suc_num": 9,    # convertidos
        "col_suc_ratio": 11, # convertidos/ingresados
        "col_banco": 13,     # promedio banco
        "label_num": "Convertidos",
        "label_den": "Ingresados",
        "invert": False,
        "simulable": True,
    },
    "scoring": {
        "label": "Scoring vs Atendidos",
        "pilar": "Individuos",
        "hoja": "Scoring",
        "col_suc_den": None,
        "col_suc_num": None,
        "col_suc_ratio": None,
        "col_banco": None,
        "label_num": "Scoreados",
        "label_den": "Atendidos",
        "invert": False,
        "simulable": False,
        "pendiente_en_provisorio": True,
    },
    "activacion_digital": {
        "label": "Activación Digital",
        "pilar": "Individuos",
        "hoja": "Activación digital",
        "col_suc_den": None,
        "col_suc_num": None,
        "col_suc_ratio": None,
        "col_banco": None,
        "label_num": "Activados",
        "label_den": "Digitalizables",
        "invert": False,
        "simulable": True,
        "pendiente_en_provisorio": True,
    },
    "remediacion": {
        "label": "Remediación de Datos",
        "pilar": "Administrativo",
        "hoja": "Remediación de datos",
        "col_suc_den": None,
        "col_suc_num": None,
        "col_suc_ratio": None,
        "col_banco": None,
        "label_num": "Datos completados",
        "label_den": "Alertas emitidas",
        "invert": False,
        "simulable": True,
        "pendiente_en_provisorio": True,
    },
    "crm_ind": {
        "label": "Reclamos CRM IND",
        "pilar": "Individuos",
        "hoja": "CRM (IND)",
        "col_suc_den": None,
        "col_suc_num": None,
        "col_suc_ratio": None,
        "col_banco": None,
        "label_num": "Resueltos",
        "label_den": "A vencer",
        "invert": False,
        "simulable": False,
        "tendencia_verde": True,  # trend ▲▲ = verde
    },
    "crm_emp": {
        "label": "Reclamos CRM EMP",
        "pilar": "Empresas",
        "hoja": "CRM (EMP)",
        "col_suc_den": None,
        "col_suc_num": None,
        "col_suc_ratio": None,
        "col_banco": None,
        "label_num": "Resueltos",
        "label_den": "A vencer",
        "invert": False,
        "simulable": False,
        "tendencia_verde": True,
    },
    "pla": {
        "label": "PLA Preventor",
        "pilar": "Administrativo",
        "hoja": "PLA",
        "col_suc_den": None,
        "col_suc_num": None,
        "col_suc_ratio": 8,  # 1 = verde (sin alertas)
        "col_banco": None,
        "label_num": "Sin alertas",
        "label_den": None,
        "invert": False,
        "simulable": False,
        "umbral_fijo": 1.0,
    },
    "balance_tarjetas": {
        "label": "Balance de Tarjetas",
        "pilar": "Administrativo",
        "hoja": "Balance de tarjetas",
        "col_suc_den": None,
        "col_suc_num": None,
        "col_suc_ratio": 8,  # 1 = verde
        "col_banco": None,
        "label_num": "Balances aprobados",
        "label_den": "Días hábiles -2",
        "invert": False,
        "simulable": False,
        "umbral_fijo": 1.0,
    },
    "haberes": {
        "label": "Convenios Haberes",
        "pilar": "Empresas",
        "hoja": "Cuentas haberes",
        "col_suc_den": None,
        "col_suc_num": None,
        "col_suc_ratio": None,
        "col_banco": None,
        "label_num": "Convenios actuales",
        "label_den": "Convenios anteriores",
        "invert": False,
        "simulable": False,
        "pendiente_en_provisorio": True,
    },
    "nps": {
        "label": "NPS",
        "pilar": "Administrativo",
        "hoja": "NPS",
        "col_suc_den": None,
        "col_suc_num": None,
        "col_suc_ratio": None,
        "col_banco": None,
        "label_num": "Promotores netos",
        "label_den": None,
        "invert": False,
        "simulable": False,
        "pendiente_en_provisorio": True,
    },
}

# Promedio banco conocido desde las capturas (backup cuando no está en el FDM)
BANCO_CONOCIDO = {
    "turno_previo": 0.960,
    "campanas_ind": 0.029,   # 2.9% según captura 24-03
    "campanas_emp": 0.225,   # 22.5% según captura 25-03
    "prospecto_ind": 0.276,  # 27.6% según captura 25-03
    "prospecto_emp": 0.418,  # 41.8% según captura 25-03
}


def _find_cu_row(df: pd.DataFrame, cu: int) -> int | None:
    """Encuentra la fila donde aparece el CU (búsqueda dinámica)."""
    for idx, row in df.iterrows():
        for val in row:
            if val == cu or str(val) == str(cu):
                return idx
    return None


def _safe_float(val) -> float | None:
    """Convierte a float, devuelve None si no es válido."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, str) and val.strip() in ("0x7", "●", "▲", "▼", ""):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _read_sheet(archivo: str, hoja: str, engine: str = None) -> pd.DataFrame | None:
    """Lee una hoja del FDM."""
    try:
        kwargs = {"sheet_name": hoja, "header": None}
        if engine:
            kwargs["engine"] = engine
        return pd.read_excel(archivo, **kwargs)
    except Exception:
        return None


def leer_indicador(archivo: str, ind_id: str) -> dict:
    """
    Lee un indicador del FDM y devuelve sus datos para Villa Ballester.

    Retorna:
        {
            "id": str,
            "label": str,
            "pilar": str,
            "suc_ratio": float | None,
            "banco_ratio": float | None,
            "suc_den": float | None,   # denominador (ingresados, etc.)
            "suc_num": float | None,   # numerador (convertidos, etc.)
            "estado": "verde" | "rojo" | "pendiente",
            "fuente": "fdm" | "backup",
            "simulable": bool,
        }
    """
    meta = INDICADORES_MAP.get(ind_id, {})
    resultado = {
        "id": ind_id,
        "label": meta.get("label", ind_id),
        "pilar": meta.get("pilar", ""),
        "suc_ratio": None,
        "banco_ratio": None,
        "suc_den": None,
        "suc_num": None,
        "estado": "pendiente",
        "fuente": "fdm",
        "simulable": meta.get("simulable", False),
        "label_num": meta.get("label_num", ""),
        "label_den": meta.get("label_den", ""),
    }

    if meta.get("pendiente_en_provisorio"):
        resultado["estado"] = "pendiente"
        return resultado

    hoja = meta.get("hoja")
    if not hoja:
        return resultado

    # Detectar engine según extensión
    ext = Path(archivo).suffix.lower()
    engine = "pyxlsb" if ext == ".xlsb" else None

    df = _read_sheet(archivo, hoja, engine)
    if df is None:
        return resultado

    row_idx = _find_cu_row(df, CU)
    if row_idx is None:
        return resultado

    row = df.iloc[row_idx]

    # Extraer valores
    col_ratio = meta.get("col_suc_ratio")
    col_banco = meta.get("col_banco")
    col_den = meta.get("col_suc_den")
    col_num = meta.get("col_suc_num")

    suc_ratio = _safe_float(row.iloc[col_ratio]) if col_ratio is not None else None
    banco_ratio = _safe_float(row.iloc[col_banco]) if col_banco is not None else None
    suc_den = _safe_float(row.iloc[col_den]) if col_den is not None else None
    suc_num = _safe_float(row.iloc[col_num]) if col_num is not None else None

    # Si no tenemos banco_ratio del FDM, usar backup conocido
    if banco_ratio is None and ind_id in BANCO_CONOCIDO:
        banco_ratio = BANCO_CONOCIDO[ind_id]
        resultado["fuente"] = "backup"

    # Derivar num si tenemos ratio y den
    if suc_num is None and suc_ratio is not None and suc_den is not None:
        suc_num = round(suc_ratio * suc_den)

    # Para campañas IND: no hay col directa del ratio suc → default 0 (rojo conservador)
    # El dato real llega vía foto del día
    if ind_id == "campanas_ind":
        if suc_ratio is None:
            suc_ratio = 0.0
            suc_num = 0

    resultado["suc_ratio"] = suc_ratio
    resultado["banco_ratio"] = banco_ratio
    resultado["suc_den"] = suc_den
    resultado["suc_num"] = suc_num

    # Determinar estado
    umbral_fijo = meta.get("umbral_fijo")
    if umbral_fijo is not None:
        resultado["estado"] = "verde" if (suc_ratio or 0) >= umbral_fijo else "rojo"
    elif suc_ratio is not None and banco_ratio is not None:
        if meta.get("invert"):
            resultado["estado"] = "verde" if suc_ratio <= banco_ratio else "rojo"
        else:
            resultado["estado"] = "verde" if suc_ratio >= banco_ratio else "rojo"
    elif meta.get("tendencia_verde"):
        resultado["estado"] = "verde"  # CRM sin datos crudos pero tendencia ▲
    else:
        resultado["estado"] = "pendiente"

    return resultado


def leer_todos(archivo: str) -> dict[str, dict]:
    """Lee todos los indicadores del FDM para Villa Ballester."""
    return {ind_id: leer_indicador(archivo, ind_id) for ind_id in INDICADORES_MAP}


def encontrar_fdm_provisorio(directorio: str = "C:/PRUEBITAS") -> str | None:
    """Busca el FDM Provisorio más reciente en el directorio y en data/."""
    path = Path(directorio)
    candidatos = list(path.glob("*.xlsx")) + list(path.glob("*.xlsb"))
    data_path = path / "data"
    if data_path.exists():
        candidatos += list(data_path.glob("*.xlsx")) + list(data_path.glob("*.xlsb"))
    # Filtrar por nombre
    fdm = [f for f in candidatos if "FDM" in f.name.upper() or "Provisorio" in f.name]
    if not fdm:
        fdm = [f for f in candidatos if f.stem.startswith("0") or "fdm" in f.stem.lower()]
    if not fdm:
        return None
    return str(max(fdm, key=lambda f: f.stat().st_mtime))


def encontrar_fdm_final(directorio: str = "C:/PRUEBITAS/fuentes") -> str | None:
    """Busca el FDM Final más reciente."""
    path = Path(directorio)
    candidatos = list(path.glob("*.xlsb")) + list(path.glob("*.xlsx"))
    fdm = [f for f in candidatos if "Final" in f.name or "FDM" in f.name.upper()]
    if not fdm:
        return None
    return str(max(fdm, key=lambda f: f.stat().st_mtime))


def extraer_fecha_fdm(nombre: str) -> tuple[int, int] | None:
    """
    Extrae (mes, año) del nombre de un archivo FDM.
    Patrones soportados:
        '03. FDM_Provisorio_26-03.xlsb' → (3, 2026) via sufijo YY-MM
        '11. FDM_Final.xlsb'            → (11, None) via prefijo MM.
    Retorna None si no puede parsear.
    """
    # Intento 1: sufijo _YY-MM o espacio YY-MM antes de extensión
    m = re.search(r'[_ ](\d{2})-(\d{2})\.\w+$', nombre)
    if m:
        yy, mm = int(m.group(1)), int(m.group(2))
        if 1 <= mm <= 12:
            anio = 2000 + yy
            return (mm, anio)

    # Intento 2: prefijo numérico "MM. " al inicio
    m = re.match(r'^(\d{1,2})\.\s', nombre)
    if m:
        mm = int(m.group(1))
        if 1 <= mm <= 12:
            return (mm, None)

    return None
