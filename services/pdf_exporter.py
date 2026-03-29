"""
Exportador PDF del Monitor SGI.
Genera un reporte de 2-4 páginas con el estado actual de los indicadores,
micro-objetivos y opcionalmente predicción del ratio banco.
"""
from fpdf import FPDF
from datetime import date
from pathlib import Path

ASSET_DIR = Path("C:/PRUEBITAS/asset")

# Colores BP
VERDE = (0, 166, 81)       # #00A651
ROJO = (229, 62, 62)       # #e53e3e
GRIS = (153, 153, 153)     # #999
TEXTO = (26, 26, 46)       # #1a1a2e
TEXTO_SEC = (85, 85, 85)   # #555
BG_CARD = (247, 249, 252)  # #f7f9fc
BG_VERDE = (240, 249, 244) # #f0f9f4
BLANCO = (255, 255, 255)


class MonitorSGIPDF(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        # Logo BP
        logo_bp = str(ASSET_DIR / "logo_bp.jpg")
        if Path(logo_bp).exists():
            self.image(logo_bp, x=10, y=8, h=12)

        # Logo Monitor SGI
        logo_sgi = str(ASSET_DIR / "MonitorSGI.png")
        if Path(logo_sgi).exists():
            self.image(logo_sgi, x=40, y=6, h=16)

        # Título
        self.set_xy(100, 8)
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(*TEXTO)
        self.cell(0, 6, "Monitor SGI", align="L")
        self.set_xy(100, 14)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*TEXTO_SEC)
        self.cell(0, 5, "Villa Ballester 5155 - Centro Zonal Olivos", align="L")

        # Fecha
        self.set_xy(160, 8)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*GRIS)
        self.cell(0, 6, date.today().strftime("%d/%m/%Y"), align="R")

        self.ln(18)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(*GRIS)
        self.cell(0, 10, f"Monitor SGI - Villa Ballester 5155 - Pagina {self.page_no()}/{{nb}}", align="C")

    def _color_estado(self, estado: str):
        """Retorna color RGB según estado."""
        if estado == "verde":
            return VERDE
        elif estado == "rojo":
            return ROJO
        return GRIS

    def _pct(self, val) -> str:
        if val is None:
            return "-"
        return f"{val * 100:.1f}%"

    def _safe_text(self, text: str) -> str:
        """Reemplaza caracteres Unicode no soportados por Helvetica."""
        reemplazos = {
            "\u2014": "-",    # —
            "\u2013": "-",    # –
            "\u2019": "'",    # '
            "\u201c": '"',    # "
            "\u201d": '"',    # "
            "\u2026": "...",  # …
            "\u2192": "->",   # →
            "\u2190": "<-",   # ←
            "\u2265": ">=",   # ≥
            "\u2264": "<=",   # ≤
            "\u2022": "*",    # •
            "\u25b2": "^",    # ▲
            "\u25bc": "v",    # ▼
            "\u00a1": "!",    # ¡
            # Emojis comunes
            "\u26a1": ">",    # ⚡
            "\u2705": "[OK]", # ✅
            "\U0001f3af": ">",# 🎯
            "\U0001f4ca": "",  # 📊
            "\U0001f4c5": "",  # 📅
            "\U0001f4c4": "",  # 📄
        }
        for orig, repl in reemplazos.items():
            text = text.replace(orig, repl)
        # Fallback: eliminar cualquier caracter fuera de latin-1
        return text.encode("latin-1", errors="replace").decode("latin-1")


def generar_pdf(indicadores: dict, objetivos: list, prediccion: dict = None) -> bytes:
    """
    Genera el PDF del Monitor SGI.

    Args:
        indicadores: dict de indicadores con estado, ratios, etc.
        objetivos: lista de strings con micro-objetivos
        prediccion: dict opcional con predicción por indicador

    Returns:
        bytes del PDF generado
    """
    pdf = MonitorSGIPDF()
    pdf.alias_nb_pages()

    # ═══════════════════════════════════════════════════════════════
    # PÁGINA 1: Resumen ejecutivo + Semáforo
    # ═══════════════════════════════════════════════════════════════
    pdf.add_page()

    verdes = [i for i in indicadores.values() if i["estado"] == "verde"]
    rojos = [i for i in indicadores.values() if i["estado"] == "rojo"]
    pendientes = [i for i in indicadores.values() if i["estado"] == "pendiente"]

    # Métricas resumen
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*TEXTO)
    pdf.cell(0, 8, "Resumen del mes", ln=True)

    y_start = pdf.get_y()
    box_w = 55
    box_h = 18

    # Verde
    pdf.set_fill_color(*BG_VERDE)
    pdf.rect(10, y_start, box_w, box_h, "F")
    pdf.set_xy(10, y_start + 2)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*VERDE)
    pdf.cell(box_w, 8, str(len(verdes)), align="C")
    pdf.set_xy(10, y_start + 10)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*TEXTO_SEC)
    pdf.cell(box_w, 5, "EN VERDE", align="C")

    # Rojo
    x2 = 10 + box_w + 5
    pdf.set_fill_color(255, 240, 240)
    pdf.rect(x2, y_start, box_w, box_h, "F")
    pdf.set_xy(x2, y_start + 2)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*ROJO)
    pdf.cell(box_w, 8, str(len(rojos)), align="C")
    pdf.set_xy(x2, y_start + 10)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*TEXTO_SEC)
    pdf.cell(box_w, 5, "EN ROJO", align="C")

    # Pendiente
    x3 = x2 + box_w + 5
    pdf.set_fill_color(*BG_CARD)
    pdf.rect(x3, y_start, box_w, box_h, "F")
    pdf.set_xy(x3, y_start + 2)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*GRIS)
    pdf.cell(box_w, 8, str(len(pendientes)), align="C")
    pdf.set_xy(x3, y_start + 10)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*TEXTO_SEC)
    pdf.cell(box_w, 5, "PENDIENTE", align="C")

    pdf.set_y(y_start + box_h + 8)

    # Tabla de indicadores con datos
    con_datos = [i for i in indicadores.values() if i["estado"] != "pendiente"]
    if con_datos:
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*TEXTO)
        pdf.cell(0, 7, "Indicadores con datos", ln=True)
        pdf.ln(2)

        # Header tabla
        col_widths = [55, 25, 25, 25, 20, 40]  # label, pilar, suc, banco, estado, detalle
        headers = ["Indicador", "Pilar", "Sucursal", "Banco", "Estado", "Detalle"]
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_fill_color(*VERDE)
        pdf.set_text_color(*BLANCO)
        for i, h in enumerate(headers):
            pdf.cell(col_widths[i], 6, h, border=0, fill=True, align="C")
        pdf.ln()

        # Filas
        pdf.set_font("Helvetica", "", 7)
        for ind in con_datos:
            color = VERDE if ind["estado"] == "verde" else ROJO
            # Fondo alterno
            pdf.set_fill_color(255, 255, 255)

            pdf.set_text_color(*TEXTO)
            pdf.cell(col_widths[0], 5.5, pdf._safe_text(ind["label"][:30]), border=0)
            pdf.cell(col_widths[1], 5.5, pdf._safe_text(ind["pilar"][:12]), border=0, align="C")

            pdf.set_text_color(*color)
            pdf.cell(col_widths[2], 5.5, pdf._pct(ind["suc_ratio"]), border=0, align="C")

            pdf.set_text_color(*TEXTO_SEC)
            pdf.cell(col_widths[3], 5.5, pdf._pct(ind["banco_ratio"]), border=0, align="C")

            pdf.set_text_color(*color)
            estado_txt = "VERDE" if ind["estado"] == "verde" else "ROJO"
            pdf.cell(col_widths[4], 5.5, estado_txt, border=0, align="C")

            # Detalle: num/den si hay
            detalle = ""
            if ind.get("suc_num") is not None and ind.get("suc_den") is not None:
                detalle = f"{int(ind['suc_num'])}/{int(ind['suc_den'])}"
            pdf.set_text_color(*TEXTO_SEC)
            pdf.cell(col_widths[5], 5.5, detalle, border=0, align="C")
            pdf.ln()

        # Línea separadora
        pdf.set_draw_color(*VERDE)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(3)

    # ═══════════════════════════════════════════════════════════════
    # PÁGINA 2: Pendientes + Micro-objetivos + Sugerencias
    # ═══════════════════════════════════════════════════════════════
    pdf.add_page()

    # Indicadores pendientes
    if pendientes:
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*TEXTO)
        pdf.cell(0, 7, f"Indicadores pendientes ({len(pendientes)})", ln=True)
        pdf.ln(2)

        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(*GRIS)
        # 3 columnas
        col_w = 60
        for i, ind in enumerate(pendientes):
            if i > 0 and i % 3 == 0:
                pdf.ln()
            pdf.cell(col_w, 5, pdf._safe_text(f"* {ind['label']} ({ind['pilar']})"), border=0)
        pdf.ln(8)

    # Micro-objetivos
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*TEXTO)
    pdf.cell(0, 8, "Foco de accion", ln=True)
    pdf.ln(2)

    if objetivos:
        for i, obj in enumerate(objetivos[:5], 1):
            # Limpiar HTML/emojis del texto
            texto = obj.replace("<br>", " ").replace("&rarr;", "->")
            texto = pdf._safe_text(texto)
            # Box verde
            pdf.set_fill_color(*BG_VERDE)
            pdf.set_draw_color(*VERDE)
            y_obj = pdf.get_y()
            pdf.rect(10, y_obj, 190, 10, "DF")
            pdf.set_xy(14, y_obj + 1)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(*VERDE)
            pdf.cell(5, 8, f"{i}.")
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(*TEXTO)
            # Limitar largo
            if len(texto) > 120:
                texto = texto[:117] + "..."
            pdf.cell(180, 8, texto)
            pdf.set_y(y_obj + 12)
    else:
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(*GRIS)
        pdf.cell(0, 8, "No hay indicadores accionables con datos en este momento.", ln=True)

    # Sugerencias de conversión para indicadores rojos
    rojos_simulables = [i for i in indicadores.values()
                        if i["estado"] == "rojo" and i.get("simulable") and i.get("suc_den")]
    if rojos_simulables:
        pdf.ln(5)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*TEXTO)
        pdf.cell(0, 7, "Oportunidades de conversion", ln=True)
        pdf.ln(2)

        for ind in rojos_simulables:
            suc_num = ind.get("suc_num") or 0
            suc_den = ind["suc_den"]
            banco = ind.get("banco_ratio") or 0
            label_num = ind.get("label_num", "acciones")

            # Calcular mínimo para verde
            if banco > 0 and suc_den > 0:
                import math
                necesarios = math.ceil(banco * suc_den - suc_num)
                if necesarios < 0:
                    necesarios = 0
                nuevo_ratio = (suc_num + necesarios) / suc_den if suc_den > 0 else 0

                pdf.set_font("Helvetica", "", 8)
                pdf.set_text_color(*ROJO)
                pdf.cell(5, 5, "*")
                pdf.set_text_color(*TEXTO)
                msg = f"{ind['label']}: necesitas {necesarios} {label_num.lower()} mas"
                msg += f" ({pdf._pct(ind['suc_ratio'])} -> {pdf._pct(nuevo_ratio)})"
                pdf.cell(0, 5, pdf._safe_text(msg), ln=True)

    # ═══════════════════════════════════════════════════════════════
    # PÁGINA 3 (opcional): Predicción ratio banco
    # ═══════════════════════════════════════════════════════════════
    if prediccion and prediccion.get("datos"):
        pdf.add_page()

        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*TEXTO)
        pdf.cell(0, 8, "Prediccion del ratio banco a fin de mes", ln=True)
        pdf.ln(1)

        meses_usados = prediccion.get("meses_usados", 0)
        pdf.set_font("Helvetica", "I", 7.5)
        pdf.set_text_color(*GRIS)
        pdf.cell(0, 5, f"Estimacion basada en {meses_usados} meses historicos", ln=True)
        pdf.ln(3)

        # Tabla predicción
        col_widths_pred = [55, 30, 30, 30, 25, 20]
        headers_pred = ["Indicador", "Suc actual", "Banco actual", "Banco estimado", "Dif. estimada", "Estado est."]
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_fill_color(*VERDE)
        pdf.set_text_color(*BLANCO)
        for i, h in enumerate(headers_pred):
            pdf.cell(col_widths_pred[i], 6, h, border=0, fill=True, align="C")
        pdf.ln()

        pdf.set_font("Helvetica", "", 7)
        for pred in prediccion["datos"]:
            label = pred.get("label", "")[:30]
            suc = pdf._pct(pred.get("suc_ratio"))
            banco_actual = pdf._pct(pred.get("banco_actual"))
            banco_est = pdf._pct(pred.get("banco_estimado"))
            mejora = pred.get("mejora_estimada")
            mejora_str = f"+{mejora*100:.1f}%" if mejora and mejora > 0 else "-"

            # Estado estimado: comparar suc vs banco estimado
            estado_est = "VERDE" if pred.get("estado_estimado") == "verde" else "ROJO" if pred.get("estado_estimado") == "rojo" else "-"
            color_est = VERDE if estado_est == "VERDE" else ROJO if estado_est == "ROJO" else GRIS

            pdf.set_text_color(*TEXTO)
            pdf.cell(col_widths_pred[0], 5.5, label, border=0)
            pdf.cell(col_widths_pred[1], 5.5, suc, border=0, align="C")
            pdf.cell(col_widths_pred[2], 5.5, banco_actual, border=0, align="C")

            pdf.set_text_color(*VERDE)
            pdf.cell(col_widths_pred[3], 5.5, banco_est, border=0, align="C")

            pdf.set_text_color(*TEXTO_SEC)
            pdf.cell(col_widths_pred[4], 5.5, mejora_str, border=0, align="C")

            pdf.set_text_color(*color_est)
            pdf.cell(col_widths_pred[5], 5.5, estado_est, border=0, align="C")
            pdf.ln()

        pdf.set_draw_color(*VERDE)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)

        # Nota
        pdf.set_font("Helvetica", "I", 7)
        pdf.set_text_color(*GRIS)
        pdf.multi_cell(0, 4, "Nota: La prediccion se basa en la mejora promedio historica del ratio banco entre provisorio y cierre final. "
                       "Los valores reales pueden variar. Usar como referencia orientativa.")

    # Firma
    firma_path = str(ASSET_DIR / "firma_pablo.png")
    if Path(firma_path).exists():
        pdf.set_y(-30)
        pdf.image(firma_path, x=80, h=10)

    return bytes(pdf.output())
