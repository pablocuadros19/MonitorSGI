"""
Monitor SGI — Villa Ballester 5155
Tablero táctico diario para mejorar la foto del mes SGI.
"""
import sys
from pathlib import Path
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

import streamlit as st
import pandas as pd
import base64
from datetime import date

from services.fdm_reader import leer_todos, encontrar_fdm_provisorio, encontrar_fdm_final, extraer_fecha_fdm
from services.atm_reader import leer_atms, encontrar_archivo_atms
from services.foto_dia_reader import (
    enriquecer_con_foto_diaria,
    leer_atendidos, leer_stock_tarjetas, cruzar_con_tarjetas
)
from services.foto_dia_manual import guardar_foto_dia, obtener_acumulado_mes, obtener_registro_fecha, enriquecer_indicadores_con_foto, borrar_foto_dia
from utils.simulador import simular, micro_objetivo_del_dia
from utils.calendario_ar import dias_habiles_mes, dias_sin_cargar, hoy_es_habil
from services.pdf_exporter import generar_pdf
from services.predictor import predecir_ratio_banco


def _img_b64(path: str) -> str:
    """Convierte imagen a base64 para usar inline en HTML."""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


# Rutas de assets
ASSET_DIR = BASE_DIR / "asset"
LOGO_BP_B64 = _img_b64(str(ASSET_DIR / "logo_bp.jpg"))
MONITOR_SGI_B64 = _img_b64(str(ASSET_DIR / "MonitorSGI.png"))
PERRITO_B64 = _img_b64(str(ASSET_DIR / "perrito_bp.png"))
FIRMA_B64 = _img_b64(str(ASSET_DIR / "firma_pablo.png"))

# ─── CONFIG ──────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Monitor SGI · Villa Ballester",
    page_icon=str(ASSET_DIR / "logo.png"),
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Estilos Banco Provincia
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600;700;900&display=swap');

html, body, [class*="css"] { font-family: 'Montserrat', sans-serif; }

/* Header — estilos movidos a .monitor-header más abajo */

/* Cards de indicadores */
.card-verde {
    background: #f0f9f4; border: 1px solid #c8e6d5; border-left: 4px solid #00A651;
    border-radius: 14px; padding: 16px 18px; height: 100%;
}
.card-rojo {
    background: #fff5f5; border: 1px solid #fed7d7; border-left: 4px solid #e53e3e;
    border-radius: 14px; padding: 16px 18px; height: 100%;
}
.card-gris {
    background: #f7f9fc; border: 1px solid #e0e5ec; border-left: 4px solid #999;
    border-radius: 14px; padding: 16px 18px; height: 100%;
}
.card-title { font-size: 0.9rem; font-weight: 700; color: #1a1a2e; margin-bottom: 8px; }
.card-ratio-big { font-size: 1.8rem; font-weight: 700; }
.ratio-verde { color: #00A651; }
.ratio-rojo  { color: #e53e3e; }
.ratio-gris  { color: #999; }
.card-banco { font-size: 0.78rem; color: #666; margin-top: 4px; }
.card-badge { font-size: 0.75rem; font-weight: 600; padding: 3px 10px; border-radius: 20px; display: inline-block; margin-top: 8px; }
.badge-verde { background: #e8f5ee; color: #00A651; }
.badge-rojo  { background: #fff0f0; color: #e53e3e; }
.badge-gris  { background: #f0f0f0; color: #999; }
.badge-foto  { background: #e8f4fd; color: #2b8cbd; }

/* Simulador */
.sim-box {
    background: #f7f9fc; border: 1px solid #e0e5ec; border-radius: 12px;
    padding: 20px; margin-bottom: 16px;
}
.sim-verde { color: #00A651; font-weight: 700; }
.sim-rojo  { color: #e53e3e; font-weight: 700; }

/* Alertas tarjetas */
.alerta-card {
    background: #fff8e1; border: 1px solid #ffd54f; border-left: 4px solid #f6ad55;
    border-radius: 12px; padding: 16px; margin-bottom: 12px;
}
.alerta-nombre { font-weight: 700; font-size: 0.95rem; color: #1a1a2e; }
.alerta-dato   { font-size: 0.82rem; color: #555; }

/* Pilar tag */
.pilar-tag {
    font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 2px;
    color: #999; margin-bottom: 4px;
}

/* Loader perrito */
@keyframes olfatear {
    0%, 100% { transform: translateX(0) rotate(0deg); }
    50%       { transform: translateX(15px) rotate(-3deg); }
}
.perrito-loader { width: 100px; display: inline-block; animation: olfatear 1.5s ease-in-out infinite; }

/* Header con logos */
.monitor-header {
    background: linear-gradient(90deg, #fff 0%, #00A651 25%, #00B8D4 100%);
    border-radius: 12px; padding: 14px 28px; margin-bottom: 20px;
    display: flex; align-items: center; gap: 16px;
}
.monitor-header .logo-bp { height: 70px; border-radius: 6px; }
.monitor-header .logo-monitor { height: 150px; }
.monitor-header .header-text { flex: 1; }
.monitor-header h1 { color: white; font-size: 1.6rem; font-weight: 900; margin: 0; text-shadow: 0 1px 3px rgba(0,0,0,0.2); }
.monitor-header p  { color: rgba(255,255,255,0.9); font-size: 0.8rem; margin: 4px 0 0; letter-spacing: 2px; font-weight: 400; }
.monitor-header .firma-header { height: 150px; opacity: 0.85; align-self: flex-end; }

/* Firma footer */
.firma-footer {
    text-align: center; padding: 30px 0 10px; margin-top: 40px;
    border-top: 1px solid #e0e5ec;
}
.firma-footer img { height: 175px; opacity: 0.6; }
.firma-footer:hover img { opacity: 1; transition: opacity 0.3s; }

/* Micro-objetivos */
.micro-obj {
    background: linear-gradient(135deg, #00A651, #00a34d);
    color: white; border-radius: 10px; padding: 14px 18px;
    margin-bottom: 10px; font-weight: 600; font-size: 0.95rem;
}
.fuente-tag { font-size: 0.7rem; opacity: 0.8; display: block; margin-top: 4px; }
</style>
""", unsafe_allow_html=True)

# ─── CIERRE DE MES ───────────────────────────────────────────────────────────

def _ejecutar_cierre_mes():
    """
    Cierre tentativo de mes:
    1. Genera PDF de cierre con los datos actuales
    2. Mueve el FDM actual a fuentes/ como histórico
    3. La app arranca limpia para el mes nuevo
    (Las fotos diarias se filtran por mes, no necesitan limpieza)
    """
    import shutil

    fdm_actual = encontrar_fdm_provisorio(str(BASE_DIR))

    if not fdm_actual:
        st.warning("No hay FDM cargado para cerrar.")
        return

    # Generar datos del mes que cierra
    indicadores_cierre = leer_todos(fdm_actual)
    indicadores_cierre = enriquecer_con_foto_diaria(indicadores_cierre)
    indicadores_cierre = enriquecer_indicadores_con_foto(indicadores_cierre)
    objetivos_cierre = micro_objetivo_del_dia(indicadores_cierre)
    prediccion_cierre = predecir_ratio_banco(indicadores_cierre)

    # Generar PDF de cierre
    pdf_cierre = generar_pdf(indicadores_cierre, objetivos_cierre, prediccion=prediccion_cierre)
    hoy = date.today()
    nombre_pdf = f"CierreSGI_{hoy.strftime('%Y-%m')}.pdf"

    # Guardar PDF en data/
    pdf_path = Path(BASE_DIR / "data") / nombre_pdf
    pdf_path.write_bytes(pdf_cierre)

    # Mover FDM a fuentes/ como histórico para el predictor
    fuentes_dir = Path(BASE_DIR / "fuentes")
    fuentes_dir.mkdir(parents=True, exist_ok=True)
    fdm_dest = fuentes_dir / Path(fdm_actual).name
    if not fdm_dest.exists():
        shutil.move(fdm_actual, str(fdm_dest))

    # Limpiar cache
    st.cache_data.clear()

    st.success(f"Mes cerrado. PDF guardado: {nombre_pdf}")
    st.download_button(
        "📄 Descargar PDF de cierre",
        data=pdf_cierre,
        file_name=nombre_pdf,
        mime="application/pdf",
    )
    st.info("El FDM se movió a fuentes/ como histórico. Subí el nuevo FDM Provisorio para empezar el mes.")


# ─── CARGA DE DATOS ──────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def cargar_datos(fdm_path: str, atm_path: str | None):
    indicadores = leer_todos(fdm_path)
    indicadores = enriquecer_con_foto_diaria(indicadores)
    # Fotos manuales llenan pendientes que la foto archivo no cubrió
    indicadores = enriquecer_indicadores_con_foto(indicadores)
    atms = leer_atms(atm_path) if atm_path else {"estado": "sin_datos", "semanas": []}
    objetivos = micro_objetivo_del_dia(indicadores)
    return indicadores, atms, objetivos


def _pct(val) -> str:
    if val is None:
        return "&mdash;"
    return f"{val * 100:.1f}%"


def _estado_icon(estado: str) -> str:
    return {"verde": "&#9650;", "rojo": "&#9660;", "pendiente": "&mdash;"}.get(estado, "&mdash;")


def _card_html(ind: dict) -> str:
    estado = ind["estado"]
    cls = {"verde": "verde", "rojo": "rojo", "pendiente": "gris"}.get(estado, "gris")
    ratio_cls = f"ratio-{cls}"

    ratio_str = _pct(ind["suc_ratio"])
    banco_str = _pct(ind["banco_ratio"])

    badge_label = {"verde": "VERDE", "rojo": "ROJO", "pendiente": "PENDIENTE"}.get(estado, "-")

    # Construir HTML sin blank lines (las blank lines rompen el parser de Streamlit)
    parts = [
        f'<div class="card-{cls}">',
        f'<div class="pilar-tag">{ind["pilar"]}</div>',
        f'<div class="card-title">{ind["label"]}</div>',
        f'<div class="card-ratio-big {ratio_cls}">{ratio_str}</div>',
    ]
    if ind["banco_ratio"]:
        parts.append(f'<div class="card-banco">Banco: {banco_str}</div>')
    if ind["suc_num"] is not None and ind["suc_den"] is not None:
        parts.append(f'<div class="card-banco">{ind["label_num"]}: {int(ind["suc_num"])} / {int(ind["suc_den"])}</div>')
    parts.append(f'<div class="card-badge badge-{cls}">{badge_label}</div>')
    if ind.get("fuente") == "foto_diaria":
        parts.append('<div class="card-badge badge-foto">Estimado - Foto diaria</div>')
    elif ind.get("fuente") == "backup":
        parts.append('<div class="card-badge badge-gris">Banco: referencia</div>')
    parts.append('</div>')

    return "".join(parts)


# ─── HEADER ──────────────────────────────────────────────────────────────────

st.markdown(f"""
<div class="monitor-header">
    <img src="data:image/jpeg;base64,{LOGO_BP_B64}" class="logo-bp" alt="Banco Provincia">
    <img src="data:image/png;base64,{MONITOR_SGI_B64}" class="logo-monitor" alt="Monitor SGI">
    <div class="header-text">
        <h1>Monitor SGI · Villa Ballester</h1>
        <p>5155 · CENTRO ZONAL OLIVOS · CLASE MEDIA</p>
    </div>
    <img src="data:image/png;base64,{FIRMA_B64}" class="firma-header" alt="@Pablocuadros19">
</div>
""", unsafe_allow_html=True)

# Buscar archivos
fdm_path = encontrar_fdm_provisorio(str(BASE_DIR))
atm_path = encontrar_archivo_atms(str(BASE_DIR))

# Sidebar: subir archivos manualmente
with st.sidebar:
    st.markdown("### 📂 Archivos")
    fdm_manual = st.file_uploader("FDM Provisorio (.xlsx/.xlsb)", type=["xlsx", "xlsb"])
    atm_manual = st.file_uploader("Indicador ATMs (.xlsx)", type=["xlsx"])
    atendidos_manual = st.file_uploader("Listado de atendidos (.xlsx/.csv)", type=["xlsx", "xls", "csv"])
    stock_manual = st.file_uploader("Stock de tarjetas (.xlsx/.csv)", type=["xlsx", "xls", "csv"])

    if fdm_manual:
        # Validar fecha del FDM nuevo vs actual
        fecha_nueva = extraer_fecha_fdm(fdm_manual.name)
        fecha_actual = extraer_fecha_fdm(Path(fdm_path).name) if fdm_path else None
        cargar_fdm = True

        if fecha_nueva and fecha_actual:
            mes_n, anio_n = fecha_nueva
            mes_a, anio_a = fecha_actual
            # Comparar si ambos tienen año
            if anio_n and anio_a and (anio_n, mes_n) < (anio_a, mes_a):
                st.warning(f"⚠️ Este FDM parece ser de {mes_n:02d}/{anio_n} pero el actual es de {mes_a:02d}/{anio_a}. Cargar uno anterior puede pisar datos.")
                cargar_fdm = st.checkbox("Cargar de todas formas", key="forzar_fdm")
            elif anio_n is None and anio_a is None and mes_n < mes_a:
                st.warning(f"⚠️ Este FDM parece ser del mes {mes_n:02d} pero el actual es del mes {mes_a:02d}.")
                cargar_fdm = st.checkbox("Cargar de todas formas", key="forzar_fdm")

        if cargar_fdm:
            tmp = BASE_DIR / "data" / fdm_manual.name
            tmp.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_bytes(fdm_manual.read())
            fdm_path = str(tmp)
            st.success(f"FDM cargado: {fdm_manual.name}")

    if atm_manual:
        tmp = BASE_DIR / "data" / atm_manual.name
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_bytes(atm_manual.read())
        atm_path = str(tmp)

    if st.button("🔄 Recargar datos"):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.markdown("### 📆 Cierre de mes")
    if st.button("Cerrar mes y archivar"):
        _ejecutar_cierre_mes()

indicadores = {}
atms = {"estado": "sin_datos", "semanas": []}
objetivos = []
prediccion = None

if fdm_path:
    # Cargar con spinner perrito
    with st.spinner(""):
        placeholder = st.empty()
        placeholder.markdown(f'<div style="text-align:center;padding:40px"><img src="data:image/png;base64,{PERRITO_B64}" class="perrito-loader" alt="Cargando..."><br><small style="color:#666;font-family:Montserrat">Olfateando datos...</small></div>', unsafe_allow_html=True)
        indicadores, atms, objetivos = cargar_datos(fdm_path, atm_path)
        # Predicción del ratio banco (si hay FDM finales en fuentes/)
        prediccion = predecir_ratio_banco(indicadores)
        placeholder.empty()
    fdm_nombre = Path(fdm_path).name
    st.caption(f"📊 FDM: {fdm_nombre} · ATMs: {'cargado' if atm_path else 'no encontrado'} · Fotos diarias: {obtener_acumulado_mes()['dias_cargados']} días")
else:
    st.info("Subí el FDM Provisorio desde el panel lateral (☰) para empezar a ver los indicadores.")

# ─── TABS ─────────────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4 = st.tabs(["📸 Foto del mes", "🎯 Simulador", "📅 Pulso diario", "🃏 Alertas tarjetas"])


# ═══════════════════════════════════════════════════════════════════════════
# TAB 1: FOTO DEL MES
# ═══════════════════════════════════════════════════════════════════════════
with tab1:

    # Resumen ejecutivo
    verdes = [i for i in indicadores.values() if i["estado"] == "verde"]
    rojos  = [i for i in indicadores.values() if i["estado"] == "rojo"]
    pendientes = [i for i in indicadores.values() if i["estado"] == "pendiente"]

    # ATMs
    if atms["estado"] == "verde":
        verdes_atm_count = 1
        rojos_atm_count = 0
    elif atms["estado"] in ("rojo", "parcial"):
        verdes_atm_count = 0
        rojos_atm_count = 1
    else:
        verdes_atm_count = 0
        rojos_atm_count = 0

    total_v = len(verdes) + verdes_atm_count
    total_r = len(rojos) + rojos_atm_count
    total_p = len(pendientes)

    c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
    with c1:
        st.metric("✅ En verde", total_v)
    with c2:
        st.metric("🔴 En rojo", total_r)
    with c3:
        st.metric("⬜ Pendiente", total_p, help="Sin datos en el provisorio todavía")
    with c4:
        if indicadores:
            pdf_bytes = generar_pdf(indicadores, objetivos, prediccion=prediccion)
            st.download_button(
                "📄 Descargar PDF",
                data=pdf_bytes,
                file_name=f"MonitorSGI_{date.today()}.pdf",
                mime="application/pdf",
            )

    st.divider()

    # Micro-objetivos del día
    if objetivos:
        st.markdown("### Foco de hoy")
        for obj in objetivos:
            st.markdown(f'<div class="micro-obj">{obj}</div>', unsafe_allow_html=True)
        st.markdown("")

    # ── INDICADORES CON DATOS ──
    st.markdown("### Indicadores con datos")

    # Agrupar por pilar
    pilares_orden = ["Individuos", "Empresas", "Administrativo", "Recupero"]
    por_pilar = {}
    for ind in indicadores.values():
        if ind["estado"] != "pendiente":
            p = ind["pilar"]
            por_pilar.setdefault(p, []).append(ind)

    # ATMs como indicador especial
    if atms["estado"] != "sin_datos":
        por_pilar.setdefault("Administrativo", []).append({
            "id": "atms",
            "label": "Gestión ATMs",
            "pilar": "Administrativo",
            "suc_ratio": None,
            "banco_ratio": None,
            "suc_num": atms["semanas_verde"],
            "suc_den": atms["semanas_medidas"],
            "estado": atms["estado"],
            "fuente": "fdm",
            "simulable": False,
            "label_num": "Semanas verde",
            "label_den": "Semanas medidas",
        })

    for pilar in pilares_orden:
        inds = por_pilar.get(pilar, [])
        if not inds:
            continue
        st.markdown(f"**{pilar}**")
        cols = st.columns(min(len(inds), 4))
        for i, ind in enumerate(inds):
            with cols[i % 4]:
                st.markdown(_card_html(ind), unsafe_allow_html=True)
        st.markdown("")

    # ── INDICADORES PENDIENTES ──
    pendientes_list = [i for i in indicadores.values() if i["estado"] == "pendiente"]
    if pendientes_list:
        with st.expander(f"⬜ Indicadores pendientes ({len(pendientes_list)}) — esperando datos del FDM o foto del día"):
            cols = st.columns(4)
            for i, ind in enumerate(pendientes_list):
                with cols[i % 4]:
                    st.markdown(_card_html(ind), unsafe_allow_html=True)

    # ── PREDICCIÓN RATIO BANCO ──
    if prediccion and prediccion.get("datos"):
        st.divider()
        with st.expander(f"📈 Predicción ratio banco a fin de mes (basado en {prediccion['meses_usados']} meses)"):
            pred_df = pd.DataFrame(prediccion["datos"])
            pred_df = pred_df.rename(columns={
                "label": "Indicador",
                "suc_ratio": "Suc actual",
                "banco_actual": "Banco actual",
                "banco_estimado": "Banco estimado",
                "mejora_estimada": "Diferencia",
                "estado_estimado": "Estado est.",
            })
            cols_show = ["Indicador", "Suc actual", "Banco actual", "Banco estimado", "Diferencia", "Estado est."]
            cols_exist = [c for c in cols_show if c in pred_df.columns]
            # Formatear porcentajes
            for col_pct in ["Suc actual", "Banco actual", "Banco estimado", "Diferencia"]:
                if col_pct in pred_df.columns:
                    pred_df[col_pct] = pred_df[col_pct].apply(lambda v: f"{v*100:.1f}%" if v is not None else "—")
            st.dataframe(pred_df[cols_exist], use_container_width=True, hide_index=True)
            st.caption("Estimación basada en el promedio histórico del ratio banco al cierre. Usar como referencia orientativa.")


# ═══════════════════════════════════════════════════════════════════════════
# TAB 2: SIMULADOR
# ═══════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### Simulador de impacto")
    st.markdown("Mové el slider y ve cuántas acciones necesitás para cruzar a verde.")

    simulables = {k: v for k, v in indicadores.items()
                  if v["simulable"] and v["suc_den"] is not None and v["banco_ratio"] is not None}

    if not simulables:
        st.info("No hay indicadores simulables con datos disponibles en este momento. Cuando cargues las fotos del día aparecerán acá.")
    else:
        for ind_id, ind in simulables.items():
            suc_num = ind["suc_num"] or 0
            suc_den = ind["suc_den"]
            banco = ind["banco_ratio"]
            label_num = ind["label_num"]
            estado_actual = ind["estado"]

            st.markdown(f'<div class="sim-box">', unsafe_allow_html=True)

            col_info, col_slider = st.columns([1, 2])
            with col_info:
                st.markdown(f"**{ind['label']}**")
                st.markdown(f"<small>{ind['pilar']}</small>", unsafe_allow_html=True)
                st.metric("Ratio actual", _pct(ind["suc_ratio"]),
                          delta=f"Banco: {_pct(banco)}", delta_color="off")
                st.caption(f"{label_num}: {int(suc_num)} / {int(suc_den)}")

            with col_slider:
                max_slider = max(20, int(suc_den - suc_num) + 5)
                extra = st.slider(
                    f"{label_num} adicionales",
                    min_value=0, max_value=max_slider, value=0,
                    key=f"slider_{ind_id}"
                )
                sim = simular(suc_num, suc_den, banco, extra)

                nuevo_ratio = _pct(sim["ratio_simulado"])
                color_cls = "sim-verde" if sim["cruza_verde"] else "sim-rojo"
                icono = "▲ VERDE" if sim["cruza_verde"] else "▼ ROJO"

                st.markdown(f"""
                **Con {extra} {label_num.lower()} más:**
                <span class="{color_cls}">{nuevo_ratio} → {icono}</span>
                """, unsafe_allow_html=True)

                if sim["faltan_para_verde"] is not None and sim["faltan_para_verde"] > 0:
                    st.caption(f"Mínimo para verde: {sim['faltan_para_verde']} {label_num.lower()}")
                elif sim["cruza_verde"] and estado_actual == "rojo":
                    st.success(f"✅ Con {extra} más cruzás verde")

            st.markdown("</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# TAB 3: PULSO DIARIO
# ═══════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("### Pulso diario")

    # ── PROGRESO DÍAS HÁBILES ──
    hoy = date.today()
    habiles_mes = dias_habiles_mes(hoy.month, hoy.year)
    acum_check = obtener_acumulado_mes()
    fechas_cargadas = [r["fecha"] for r in acum_check.get("registros", [])]
    faltantes = dias_sin_cargar(hoy.month, hoy.year, fechas_cargadas)
    # Solo mostrar faltantes hasta hoy (no futuros)
    faltantes_pasados = [d for d in faltantes if d <= hoy]

    total_habiles = len(habiles_mes)
    cargados = len(fechas_cargadas)
    progreso = cargados / total_habiles if total_habiles > 0 else 0

    st.progress(progreso, text=f"Foto del día: {cargados} / {total_habiles} días hábiles cargados")

    if faltantes_pasados:
        fechas_fmt = ", ".join(d.strftime("%d/%b") for d in faltantes_pasados)
        st.warning(f"Sin cargar: {fechas_fmt}")
    elif cargados > 0:
        st.success("Todos los días hábiles hasta hoy están cargados")

    if hoy_es_habil() and hoy.isoformat() not in fechas_cargadas:
        st.info("📋 Hoy es día hábil y todavía no cargaste la foto")

    # ── CARGA POR ARCHIVO: Foto del Día ──
    with st.expander("📎 Cargar Foto del Día desde archivo Excel"):
        foto_archivo = st.file_uploader("Subí el Excel de la Foto del Día", type=["xlsx", "xls", "csv"], key="foto_dia_archivo")
        if foto_archivo:
            from services.foto_dia_reader import leer_foto_dia
            tmp_foto = BASE_DIR / "data" / foto_archivo.name
            tmp_foto.parent.mkdir(parents=True, exist_ok=True)
            tmp_foto.write_bytes(foto_archivo.read())
            resultado = leer_foto_dia(str(tmp_foto))
            if resultado and resultado.get("raw"):
                st.success(f"Archivo leído: {len(resultado['raw'])} filas")
                st.dataframe(pd.DataFrame(resultado["raw"]).head(10), use_container_width=True, hide_index=True)
                st.caption("Revisá que los datos se leyeron bien. Mañana ajustamos el mapeo si hace falta.")
            else:
                st.warning("No se pudo leer el archivo. Mañana con el formato real lo ajustamos.")

    # ── FORMULARIO MANUAL: Foto del Día ──
    fecha_cargar = st.date_input("¿Qué día estás cargando?", value=date.today(), key="fecha_foto_dia")
    fecha_str = fecha_cargar.strftime("%Y-%m-%d")
    registro_fecha = obtener_registro_fecha(fecha_str)
    es_hoy = fecha_cargar == date.today()
    label_dia = "hoy" if es_hoy else fecha_cargar.strftime("%d/%b")

    with st.expander(f"📋 Cargar Foto del Día ({label_dia})" + (f" — ✅ {label_dia} cargado" if registro_fecha else ""), expanded=not registro_fecha):
        st.caption("Copiá los números de BIP Sucursales (16:30 hs) y completá acá. Tarda 2 minutos.")

        with st.form("foto_dia_form", clear_on_submit=False):
            st.markdown("**OPORTUNIDADES — Scoring**")
            fc1, fc2, fc3 = st.columns(3)
            with fc1:
                scoring_solicitados = st.number_input("Scorings solicitados", min_value=0, value=registro_fecha.get("scoring_solicitados", 0) if registro_fecha else 0, key="f_ss")
                scoring_turnos = st.number_input("Turnos del día", min_value=0, value=registro_fecha.get("scoring_turnos", 0) if registro_fecha else 0, key="f_st")
            with fc2:
                scoring_ventas = st.number_input("Ventas", min_value=0, value=registro_fecha.get("scoring_ventas", 0) if registro_fecha else 0, key="f_sv")
                scoring_no_ventas = st.number_input("No ventas", min_value=0, value=registro_fecha.get("scoring_no_ventas", 0) if registro_fecha else 0, key="f_snv")
            with fc3:
                scoring_pendientes = st.number_input("Pendientes", min_value=0, value=registro_fecha.get("scoring_pendientes", 0) if registro_fecha else 0, key="f_sp")

            st.markdown("**LLAMADOS**")
            lc1, lc2, lc3, lc4 = st.columns(4)
            with lc1:
                st.markdown("<small style='color:#999;font-weight:700'>PROSPECTO DIGITAL</small>", unsafe_allow_html=True)
                prospecto_ingresos = st.number_input("Ingresos", min_value=0, value=registro_fecha.get("prospecto_ingresos", 0) if registro_fecha else 0, key="f_pi")
                prospecto_llamados = st.number_input("Llamados", min_value=0, value=registro_fecha.get("prospecto_llamados", 0) if registro_fecha else 0, key="f_pl")
                prospecto_gestionados = st.number_input("Gestionados", min_value=0, value=registro_fecha.get("prospecto_gestionados", 0) if registro_fecha else 0, key="f_pg")
            with lc2:
                st.markdown("<small style='color:#999;font-weight:700'>TURNO PREVIO</small>", unsafe_allow_html=True)
                turno_ingresos = st.number_input("Ingresos", min_value=0, value=registro_fecha.get("turno_previo_ingresos", 0) if registro_fecha else 0, key="f_ti")
                turno_llamados = st.number_input("Llamados", min_value=0, value=registro_fecha.get("turno_previo_llamados", 0) if registro_fecha else 0, key="f_tl")
                turno_gestionados = st.number_input("Gestionados", min_value=0, value=registro_fecha.get("turno_previo_gestionados", 0) if registro_fecha else 0, key="f_tg")
            with lc3:
                st.markdown("<small style='color:#999;font-weight:700'>CAMPAÑAS</small>", unsafe_allow_html=True)
                campanas_disponibles = st.number_input("Disponibles", min_value=0, value=registro_fecha.get("campanas_disponibles", 0) if registro_fecha else 0, key="f_cd")
                campanas_llamados = st.number_input("Llamados", min_value=0, value=registro_fecha.get("campanas_llamados", 0) if registro_fecha else 0, key="f_cl")
                campanas_gestionados = st.number_input("Gestionados", min_value=0, value=registro_fecha.get("campanas_gestionados", 0) if registro_fecha else 0, key="f_cg")
            with lc4:
                st.markdown("<small style='color:#999;font-weight:700'>MIGAS</small>", unsafe_allow_html=True)
                migas_ingresos = st.number_input("Ingresos", min_value=0, value=registro_fecha.get("migas_ingresos", 0) if registro_fecha else 0, key="f_mi")
                migas_llamados = st.number_input("Llamados", min_value=0, value=registro_fecha.get("migas_llamados", 0) if registro_fecha else 0, key="f_ml")

            st.markdown("**OTROS**")
            oc1, oc2 = st.columns(2)
            with oc1:
                derivaciones_tesoreria = st.number_input("Derivaciones a Tesorería", min_value=0, value=registro_fecha.get("derivaciones_tesoreria", 0) if registro_fecha else 0, key="f_dt")
            with oc2:
                observaciones = st.text_input("Observaciones", value=registro_fecha.get("observaciones", "") if registro_fecha else "", key="f_obs")

            submitted = st.form_submit_button("Guardar Foto del Día", type="primary")

            if submitted:
                datos = {
                    "fecha": fecha_str,
                    "scoring_solicitados": scoring_solicitados,
                    "scoring_turnos": scoring_turnos,
                    "scoring_ventas": scoring_ventas,
                    "scoring_no_ventas": scoring_no_ventas,
                    "scoring_pendientes": scoring_pendientes,
                    "prospecto_ingresos": prospecto_ingresos,
                    "prospecto_llamados": prospecto_llamados,
                    "prospecto_gestionados": prospecto_gestionados,
                    "turno_previo_ingresos": turno_ingresos,
                    "turno_previo_llamados": turno_llamados,
                    "turno_previo_gestionados": turno_gestionados,
                    "campanas_disponibles": campanas_disponibles,
                    "campanas_llamados": campanas_llamados,
                    "campanas_gestionados": campanas_gestionados,
                    "migas_ingresos": migas_ingresos,
                    "migas_llamados": migas_llamados,
                    "derivaciones_tesoreria": derivaciones_tesoreria,
                    "observaciones": observaciones,
                }
                guardar_foto_dia(datos)
                st.success("Foto del día guardada correctamente")
                st.cache_data.clear()

    st.divider()

    # ── ACUMULADO MENSUAL ──
    acum_manual = obtener_acumulado_mes()

    if acum_manual["dias_cargados"] == 0:
        st.info("Todavía no hay fotos del día cargadas para este mes. Completá el formulario de arriba a las 16:30.")
    else:
        st.success(f"**{acum_manual['dias_cargados']} días cargados** — último: {acum_manual['ultimo_dia']}")
        st.markdown("")

        mc1, mc2, mc3, mc4, mc5 = st.columns(5)
        with mc1:
            st.metric("Scorings solicitados", acum_manual["scoring_solicitados"])
        with mc2:
            st.metric("Prospecto gestionados", acum_manual["prospecto_gestionados"])
        with mc3:
            st.metric("Turno previo gestionados", acum_manual["turno_previo_gestionados"])
        with mc4:
            st.metric("Campañas gestionadas", acum_manual["campanas_gestionados"])
        with mc5:
            migas_ing = acum_manual.get("migas_ingresos", 0)
            migas_lla = acum_manual.get("migas_llamados", 0)
            cobertura = f"{migas_lla}/{migas_ing}" if migas_ing else "—"
            st.metric("Migas", cobertura)

        # Detalle por día
        if acum_manual["registros"]:
            with st.expander(f"Ver detalle por día ({acum_manual['dias_cargados']} registros)"):
                df_dias = pd.DataFrame(acum_manual["registros"])
                cols_mostrar = ["fecha", "scoring_solicitados", "scoring_ventas",
                                "prospecto_gestionados", "turno_previo_gestionados",
                                "campanas_gestionados", "migas_ingresos", "migas_llamados",
                                "derivaciones_tesoreria"]
                cols_exist = [c for c in cols_mostrar if c in df_dias.columns]
                st.dataframe(df_dias[cols_exist], use_container_width=True, hide_index=True)

                # Borrar un día
                fechas_cargadas = sorted([r["fecha"] for r in acum_manual["registros"]], reverse=True)
                col_sel, col_btn = st.columns([2, 1])
                with col_sel:
                    fecha_borrar = st.selectbox("Seleccionar día a borrar", fechas_cargadas, key="fecha_borrar")
                with col_btn:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🗑️ Borrar día", type="secondary", key="btn_borrar_dia"):
                        if borrar_foto_dia(fecha_borrar):
                            st.cache_data.clear()
                            st.success(f"Registro del {fecha_borrar} eliminado.")
                            st.rerun()
                        else:
                            st.warning("No se encontró ese registro.")

    st.divider()
    st.markdown("**Micro-objetivos de hoy** (del simulador)")
    if objetivos:
        for obj in objetivos:
            st.markdown(f'<div class="micro-obj">{obj}</div>', unsafe_allow_html=True)
    else:
        st.info("No hay indicadores accionables con datos en este momento.")


# ═══════════════════════════════════════════════════════════════════════════
# TAB 4: ALERTAS DE TARJETAS
# ═══════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("### Alertas de tarjetas — Clientes que vinieron y tienen plástico pendiente")
    st.caption("Cruzás el listado de atendidos del día con el stock de tarjetas en sucursal")

    # Verificar si hay archivos cargados
    atendidos_path = None
    stock_path = None

    # Buscar en data/
    data_dir = BASE_DIR / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    for f in sorted(data_dir.glob("*atendidos*"), reverse=True):
        atendidos_path = str(f)
        break
    for f in sorted(data_dir.glob("*stock*"), reverse=True):
        stock_path = str(f)
        break

    if atendidos_manual:
        tmp = data_dir / f"atendidos_{atendidos_manual.name}"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_bytes(atendidos_manual.read())
        atendidos_path = str(tmp)
        st.success("Listado de atendidos cargado")

    if stock_manual:
        tmp = data_dir / f"stock_{stock_manual.name}"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_bytes(stock_manual.read())
        stock_path = str(tmp)
        st.success("Stock de tarjetas cargado")

    if not atendidos_path or not stock_path:
        st.info("Subí el **listado de atendidos** y el **stock de tarjetas** desde el panel lateral para ver las alertas.")
        with st.expander("¿Qué hace esta pantalla?"):
            st.markdown("""
            **Cruza dos archivos que tenés disponibles a las 16:30:**

            1. **Listado de clientes atendidos** — quiénes pasaron por la sucursal hoy
            2. **Stock de tarjetas** — qué plásticos están en la sucursal sin entregar

            **Resultado:** lista de clientes que vinieron hoy y tienen una tarjeta esperándolos,
            con sus datos de contacto para poder gestionar la entrega.

            Esto alimenta el indicador **"Tarjetas entregadas a clientes con turno"** del SGI.
            """)
    else:
        atendidos = leer_atendidos(atendidos_path) or []
        stock = leer_stock_tarjetas(stock_path)
        cruce = cruzar_con_tarjetas(atendidos, stock)

        # Resumen
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Clientes atendidos hoy", cruce["total_atendidos"])
        with c2:
            st.metric("Con tarjeta entregable", cruce["con_tarjeta_entregable"])
        with c3:
            pendientes_tar = len(cruce["pendientes"])
            st.metric("Pendientes de entrega", pendientes_tar,
                      delta=f"-{cruce['entregadas']} ya entregadas" if cruce["entregadas"] else None)

        if pendientes_tar == 0:
            st.success("✅ No quedan tarjetas pendientes de entregar a clientes que vinieron hoy.")
        else:
            st.warning(f"⚠️ {pendientes_tar} clientes vinieron hoy y tienen tarjeta sin retirar")
            st.markdown("")

            for cliente in cruce["pendientes"]:
                nombre = cliente.get("nombre") or "(sin nombre)"
                dni = cliente.get("dni") or "—"
                tel = cliente.get("telefono") or "—"
                email = cliente.get("email") or "—"
                tarjeta = cliente.get("tipo_tarjeta") or cliente.get("producto") or "—"
                dias = cliente.get("dias_en_stock")
                dias_str = f" · {dias} días en stock" if dias else ""

                st.markdown(f"""
                <div class="alerta-card">
                    <div class="alerta-nombre">{nombre}</div>
                    <div class="alerta-dato">DNI: {dni} · Tel: {tel} · Email: {email}</div>
                    <div class="alerta-dato">Tarjeta: <strong>{tarjeta}</strong>{dias_str}</div>
                </div>
                """, unsafe_allow_html=True)

            st.divider()
            # Exportar como tabla para gestión
            df_export = pd.DataFrame(cruce["pendientes"])
            if not df_export.empty:
                st.download_button(
                    "📥 Descargar listado pendientes",
                    data=df_export.to_csv(index=False, encoding="utf-8-sig"),
                    file_name=f"tarjetas_pendientes_{date.today()}.csv",
                    mime="text/csv"
                )

# ═══════════════════════════════════════════════════════════════════════════
# FOOTER — Firma
# ═══════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="firma-footer">
    <img src="data:image/png;base64,{FIRMA_B64}" alt="@Pablocuadros19">
</div>
""", unsafe_allow_html=True)
