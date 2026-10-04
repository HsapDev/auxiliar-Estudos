from fpdf import FPDF
import json
import unicodedata

from logger import log_info, log_sucesso, log_aviso, log_erro


def sanitizar_texto(texto) -> str:
    """
    Remove acentos e caracteres especiais para evitar erros de encode ASCII/latin-1 do FPDF.
    Exemplo: 'Matéria com Atenção' vira 'Materia com Atencao'.
    """
    if not texto:
        return ""
    if not isinstance(texto, str):
        texto = str(texto)

    # Normaliza separando os acentos e remove os diacríticos
    texto_normalizado = unicodedata.normalize('NFD', texto)
    texto_sem_acento = ''.join(c for c in texto_normalizado if unicodedata.category(c) != 'Mn')
    
    # Substituições adicionais de caracteres que possam escapar
    return texto_sem_acento.encode('ascii', 'ignore').decode('ascii')


class ApostilaPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 10, sanitizar_texto("Apostila de Consolidação - Gerada por IA"), border=False, new_x="LMARGIN", new_y="NEXT", align="C")
        self.line(10, 20, 200, 20)
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, sanitizar_texto(f"Pagina {self.page_no()}"), align="C")


def gerar_pdf_apostila(caminho_json: str, caminho_saida_pdf: str):
    log_info(f"Iniciando formatação do PDF a partir de {caminho_json}...", "PDFGenerator")
    try:
        with open(caminho_json, "r", encoding="utf-8") as f:
            dados = json.load(f)

        pdf = ApostilaPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        # Matéria
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, sanitizar_texto(f"Materia: {dados.get('materia', 'Geral')}"), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

        # 1. Resumo Big Picture
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, sanitizar_texto("1. Visao Geral (Big Picture)"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 6, sanitizar_texto(dados.get("resumo_big_picture", "")), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)

        # 2. Alertas de Atenção
        alertas = dados.get("alertas_atencao") or dados.get("alerta_atencao")
        if alertas:
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(200, 0, 0)
            pdf.cell(0, 8, sanitizar_texto("2. Alertas & Erros Frequentes"), new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(0, 0, 0)
            for alerta in alertas:
                pdf.multi_cell(0, 6, sanitizar_texto(f"- {alerta}"), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(5)

        # 3. Fórmulas
        if dados.get("formulas"):
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 8, sanitizar_texto("3. Formulas Principais"), new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 10)
            for f in dados["formulas"]:
                if isinstance(f, dict):
                    nome = sanitizar_texto(f.get('nome', ''))
                    formula = sanitizar_texto(f.get('formula', ''))
                    pdf.multi_cell(0, 6, f"* {nome}: {formula}" if nome else f"* {formula}", new_x="LMARGIN", new_y="NEXT")
                else:
                    pdf.multi_cell(0, 6, f"* {sanitizar_texto(f)}", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(5)

        # 4. Exercícios
        if dados.get("exercicios_resolvidos"):
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 8, sanitizar_texto("4. Exercicios Resolvidos"), new_x="LMARGIN", new_y="NEXT")
            for i, ex in enumerate(dados["exercicios_resolvidos"], 1):
                pdf.set_font("Helvetica", "B", 10)
                if isinstance(ex, dict):
                    enunciado = sanitizar_texto(ex.get('enunciado', ''))
                    pdf.multi_cell(0, 6, f"Exercicio {i}: {enunciado}", new_x="LMARGIN", new_y="NEXT")
                    pdf.set_font("Helvetica", "", 10)
                    passos = ex.get("passos", [])
                    if isinstance(passos, list):
                        for passo in passos:
                            pdf.multi_cell(0, 5, sanitizar_texto(f" -> {passo}"), new_x="LMARGIN", new_y="NEXT")
                    elif passos:
                        pdf.multi_cell(0, 5, sanitizar_texto(f" -> {passos}"), new_x="LMARGIN", new_y="NEXT")
                else:
                    pdf.multi_cell(0, 6, f"Exercicio {i}: {sanitizar_texto(ex)}", new_x="LMARGIN", new_y="NEXT")
                pdf.ln(3)

        pdf.output(caminho_saida_pdf)
        log_sucesso(f"PDF compilado com sucesso ({pdf.page_no()} página(s)) em: {caminho_saida_pdf}", "PDFGenerator")
    except Exception as e:
        log_erro(f"Erro fatal na geração do PDF {caminho_saida_pdf}", "PDFGenerator", exc=e)
        raise e