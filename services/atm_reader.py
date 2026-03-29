"""
Lee el indicador de ATMs desde el xlsx semanal.
Villa Ballester tiene sus ATMs en verde las 3 semanas medidas.
"""
import pandas as pd
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

CU = 5155

SEMANAS = ["1° Semana", "2° Semana", "3° Semana", "4° Semana", "5° Semana"]


def leer_atms(archivo: str) -> dict:
    """
    Lee los datos de ATMs de Villa Ballester.

    Returns:
        {
            "semanas": [{"semana": str, "ug": float, "um": float, "remanente": float,
                         "desvio": float, "semaforo": str}],
            "estado": "verde" | "rojo" | "parcial" | "sin_datos",
            "semanas_verde": int,
            "semanas_medidas": int,
        }
    """
    resultado = {
        "semanas": [],
        "estado": "sin_datos",
        "semanas_verde": 0,
        "semanas_medidas": 0,
    }

    try:
        for semana in SEMANAS:
            try:
                df = pd.read_excel(archivo, sheet_name=semana, header=None)
            except Exception:
                continue

            # Buscar fila de Villa Ballester en la sección de sucursales (filas 4-389)
            fila_vb = None
            for idx in range(3, min(390, len(df))):
                val = df.iloc[idx, 0]
                if val == CU or str(val) == str(CU):
                    fila_vb = idx
                    break

            if fila_vb is None:
                continue

            row = df.iloc[fila_vb]
            # Columnas: [0]=CU, [1]=gestión, [2]=zona, [3]=UG, [4]=UM, [5]=Remanente, [6]=Desvío, [7]=?, [8]=Semáforo?
            ug = _safe_float(row.iloc[3]) if len(row) > 3 else None
            um = _safe_float(row.iloc[4]) if len(row) > 4 else None
            rem = _safe_float(row.iloc[5]) if len(row) > 5 else None
            desvio = _safe_float(row.iloc[6]) if len(row) > 6 else None
            semaforo_raw = str(row.iloc[8]).strip() if len(row) > 8 else ""

            # Normalizar semáforo
            if "VERDE" in semaforo_raw.upper():
                semaforo = "verde"
            elif "ROJO" in semaforo_raw.upper():
                semaforo = "rojo"
            elif "AMARILLO" in semaforo_raw.upper():
                semaforo = "amarillo"
            elif ug is None:
                semaforo = "sin_datos"
            else:
                semaforo = "sin_datos"

            if ug is not None:
                resultado["semanas"].append({
                    "semana": semana,
                    "ug": ug,
                    "um": um,
                    "remanente": rem,
                    "desvio": desvio,
                    "semaforo": semaforo,
                })
                resultado["semanas_medidas"] += 1
                if semaforo == "verde":
                    resultado["semanas_verde"] += 1

    except Exception:
        pass

    # Determinar estado general
    if resultado["semanas_medidas"] == 0:
        resultado["estado"] = "sin_datos"
    elif resultado["semanas_verde"] == resultado["semanas_medidas"]:
        resultado["estado"] = "verde"
    elif resultado["semanas_verde"] == 0:
        resultado["estado"] = "rojo"
    else:
        resultado["estado"] = "parcial"

    return resultado


def encontrar_archivo_atms(directorio: str = "C:/PRUEBITAS") -> str | None:
    """Busca el archivo de ATMs más reciente en el directorio y en data/."""
    path = Path(directorio)
    candidatos = list(path.glob("*ATM*")) + list(path.glob("*atm*"))
    data_path = path / "data"
    if data_path.exists():
        candidatos += list(data_path.glob("*ATM*")) + list(data_path.glob("*atm*"))
    if not candidatos:
        return None
    return str(max(candidatos, key=lambda f: f.stat().st_mtime))


def _safe_float(val) -> float | None:
    if val is None:
        return None
    if isinstance(val, float) and pd.isna(val):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None
