"""
Predictor de ratio banco a fin de mes.
Usa FDM finales históricos para estimar cuánto sube el promedio banco
entre el provisorio actual y el cierre.
"""
from pathlib import Path
from services.fdm_reader import leer_todos, encontrar_fdm_final, INDICADORES_MAP


def _buscar_fdm_finales(directorio: str = None) -> list[str]:
    """Busca todos los FDM finales en el directorio."""
    if directorio is None:
        directorio = str(Path(__file__).parent.parent / "fuentes")
    path = Path(directorio)
    if not path.exists():
        return []
    candidatos = list(path.glob("*.xlsb")) + list(path.glob("*.xlsx"))
    # Filtrar por nombre que sugiera FDM
    fdm = [f for f in candidatos if "FDM" in f.name.upper() or "Final" in f.name or "Provisorio" in f.name]
    if not fdm:
        fdm = [f for f in candidatos if f.stem.startswith("0") or "fdm" in f.stem.lower()]
    # Ordenar por fecha de modificación (más antiguo primero)
    fdm.sort(key=lambda f: f.stat().st_mtime)
    return [str(f) for f in fdm]


def calcular_mejora_historica(directorio: str = None) -> dict:
    """
    Lee todos los FDM finales y calcula la mejora promedio del ratio banco
    por indicador entre meses.

    Como no tenemos provisorios históricos para comparar contra finales del mismo mes,
    usamos el promedio absoluto del ratio banco en los finales como referencia.
    La "mejora" se estima como la variación típica del ratio banco entre meses.

    Returns:
        {
            "meses_usados": int,
            "archivos": list[str],
            "por_indicador": {
                ind_id: {
                    "ratios_historicos": list[float],  # ratio banco en cada final
                    "promedio_banco_final": float,     # promedio del ratio banco al cierre
                    "desvio": float,                   # variación típica
                }
            }
        }
    """
    archivos = _buscar_fdm_finales(directorio)

    if not archivos:
        return {"meses_usados": 0, "archivos": [], "por_indicador": {}}

    # Leer banco_ratio de cada archivo para cada indicador
    historico = {}
    archivos_validos = []

    for archivo in archivos:
        try:
            indicadores = leer_todos(archivo)
            archivos_validos.append(Path(archivo).name)

            for ind_id, ind in indicadores.items():
                banco = ind.get("banco_ratio")
                if banco is not None and banco > 0:
                    if ind_id not in historico:
                        historico[ind_id] = []
                    historico[ind_id].append(banco)
        except Exception:
            # Si un archivo no se puede leer, saltar
            continue

    # Calcular estadísticas por indicador
    por_indicador = {}
    for ind_id, ratios in historico.items():
        if len(ratios) >= 1:
            promedio = sum(ratios) / len(ratios)
            # Desvío: cuánto suele variar entre meses
            if len(ratios) >= 2:
                desvio = sum(abs(r - promedio) for r in ratios) / len(ratios)
            else:
                desvio = 0.0

            por_indicador[ind_id] = {
                "ratios_historicos": ratios,
                "promedio_banco_final": promedio,
                "desvio": desvio,
            }

    return {
        "meses_usados": len(archivos_validos),
        "archivos": archivos_validos,
        "por_indicador": por_indicador,
    }


def predecir_ratio_banco(indicadores_actuales: dict, directorio: str = None) -> dict:
    """
    Predice dónde va a terminar el ratio banco a fin de mes.

    Lógica: usa el promedio histórico del banco al cierre como estimación.
    Si el banco actual del provisorio es menor al promedio histórico, se espera que suba.
    Si es mayor, se espera que se mantenga o baje.

    Returns:
        {
            "meses_usados": int,
            "datos": [
                {
                    "id": str,
                    "label": str,
                    "suc_ratio": float,
                    "banco_actual": float,
                    "banco_estimado": float,
                    "mejora_estimada": float,
                    "estado_estimado": "verde" | "rojo",
                }
            ]
        }
    """
    mejora = calcular_mejora_historica(directorio)

    if mejora["meses_usados"] == 0:
        return {"meses_usados": 0, "datos": []}

    datos = []
    for ind_id, ind in indicadores_actuales.items():
        hist = mejora["por_indicador"].get(ind_id)
        if not hist:
            continue

        suc_ratio = ind.get("suc_ratio")
        banco_actual = ind.get("banco_ratio")

        if banco_actual is None:
            continue

        banco_estimado = hist["promedio_banco_final"]
        mejora_est = banco_estimado - banco_actual

        # Estado estimado: compara suc vs banco estimado
        meta = INDICADORES_MAP.get(ind_id, {})
        if suc_ratio is not None:
            if meta.get("invert"):
                estado_est = "verde" if suc_ratio <= banco_estimado else "rojo"
            else:
                estado_est = "verde" if suc_ratio >= banco_estimado else "rojo"
        else:
            estado_est = "pendiente"

        datos.append({
            "id": ind_id,
            "label": ind.get("label", ind_id),
            "suc_ratio": suc_ratio,
            "banco_actual": banco_actual,
            "banco_estimado": banco_estimado,
            "mejora_estimada": mejora_est,
            "estado_estimado": estado_est,
        })

    return {
        "meses_usados": mejora["meses_usados"],
        "datos": datos,
    }
