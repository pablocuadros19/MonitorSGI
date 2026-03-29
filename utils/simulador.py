"""
Lógica de simulación de impacto.
Calcula: dado X acciones más, ¿qué ratio alcanzaría la sucursal y cruzaría el verde?
"""


def simular(suc_num: float, suc_den: float, banco_ratio: float, extra: int) -> dict:
    """
    Simula el efecto de X acciones adicionales sobre el ratio de un indicador.

    Args:
        suc_num: numerador actual (ej: 14 convertidos)
        suc_den: denominador actual (ej: 65 ingresados)
        banco_ratio: umbral del banco para verde (ej: 0.225)
        extra: acciones adicionales a simular

    Returns:
        {
            "ratio_actual": float,
            "ratio_simulado": float,
            "banco_ratio": float,
            "cruza_verde": bool,
            "faltan_para_verde": int,  # mínimo de acciones para cruzar
        }
    """
    if suc_den == 0:
        return {
            "ratio_actual": 0,
            "ratio_simulado": 0,
            "banco_ratio": banco_ratio,
            "cruza_verde": False,
            "faltan_para_verde": None,
        }

    ratio_actual = suc_num / suc_den
    ratio_simulado = (suc_num + extra) / suc_den
    cruza_verde = ratio_simulado >= banco_ratio

    # Calcular mínimo de acciones para cruzar
    import math
    faltan = None
    if ratio_actual < banco_ratio:
        # (num + n) / den >= banco  →  n >= den * banco - num
        n_minimo = math.ceil(banco_ratio * suc_den - suc_num)
        faltan = max(0, n_minimo)

    return {
        "ratio_actual": ratio_actual,
        "ratio_simulado": ratio_simulado,
        "banco_ratio": banco_ratio,
        "cruza_verde": cruza_verde,
        "faltan_para_verde": faltan,
    }


def mensaje_oportunidad(ind: dict) -> str | None:
    """
    Genera el texto de oportunidad para un indicador rojo simulable.

    Args:
        ind: resultado de fdm_reader.leer_indicador()

    Returns:
        Texto listo para mostrar, o None si no aplica.
    """
    if ind["estado"] != "rojo" or not ind["simulable"]:
        return None
    if ind["suc_den"] is None or ind["banco_ratio"] is None:
        return None

    suc_num = ind["suc_num"] or 0
    suc_den = ind["suc_den"]
    banco = ind["banco_ratio"]

    sim = simular(suc_num, suc_den, banco, 0)
    faltan = sim["faltan_para_verde"]

    if faltan is None:
        return None

    label_num = ind.get("label_num", "acciones").lower()
    label = ind["label"]

    if faltan == 0:
        return f"✅ {label}: ya cruzaste el promedio banco"
    elif faltan == 1:
        return f"⚡ {label}: con 1 {label_num[:-1] if label_num.endswith('s') else label_num} más → verde"
    else:
        return f"🎯 {label}: faltan {faltan} {label_num} para verde"


def micro_objetivo_del_dia(indicadores: dict) -> list[str]:
    """
    Genera los micro-objetivos del día ordenados por prioridad.
    Prioridad: indicadores más cerca de verde primero.

    Args:
        indicadores: dict de {id: resultado_leer_indicador}

    Returns:
        Lista de strings con las oportunidades más urgentes.
    """
    oportunidades = []

    for ind_id, ind in indicadores.items():
        if ind["estado"] != "rojo" or not ind["simulable"]:
            continue
        if ind["suc_den"] is None or ind["banco_ratio"] is None:
            continue

        suc_num = ind["suc_num"] or 0
        suc_den = ind["suc_den"]
        banco = ind["banco_ratio"]

        sim = simular(suc_num, suc_den, banco, 0)
        faltan = sim["faltan_para_verde"]

        if faltan is not None:
            oportunidades.append({
                "id": ind_id,
                "label": ind["label"],
                "faltan": faltan,
                "ratio_actual": sim["ratio_actual"],
                "banco_ratio": banco,
                "label_num": ind.get("label_num", "acciones"),
            })

    # Ordenar: primero los que menos acciones necesitan
    oportunidades.sort(key=lambda x: x["faltan"])

    mensajes = []
    for op in oportunidades[:3]:  # top 3
        faltan = op["faltan"]
        label = op["label"]
        label_num = op["label_num"].lower()
        ratio_pct = op["ratio_actual"] * 100
        banco_pct = op["banco_ratio"] * 100

        if faltan == 0:
            mensajes.append(f"✅ {label} ya está verde ({ratio_pct:.1f}% ≥ {banco_pct:.1f}%)")
        elif faltan == 1:
            mensajes.append(f"⚡ {label} — ¡1 {label_num[:-1] if label_num.endswith('s') else label_num} más y cruzás verde!")
        else:
            mensajes.append(f"🎯 {label} — faltan {faltan} {label_num} ({ratio_pct:.1f}% → necesitás {banco_pct:.1f}%)")

    return mensajes
