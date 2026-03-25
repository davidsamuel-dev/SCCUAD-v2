from fpdf import FPDF
import pandas as pd
from datetime import datetime
import unicodedata

# Função para remover acentos - essencial para evitar que o PDF trave
def normalizar(txt):
    if txt is None or pd.isna(txt): return ""
    txt = str(txt)
    
    # 1. Decompõe acentos (Ex: 'Á' vira 'A' + '´')
    nfkd_form = unicodedata.normalize('NFKD', txt)
    
    # 2. Filtra apenas caracteres que não são acentos (Mn) E que são básicos (ASCII)
    # Isso vai matar o traço longo "–" e trocar por nada, ou você pode tratar antes.
    txt_limpo = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    
    # 3. Garante que o texto final seja compatível com o PDF (ASCII puro)
    return txt_limpo.encode('ascii', 'ignore').decode('ascii').upper().strip()

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.set_text_color(0, 31, 63)
        self.cell(0, 10, normalizar('AD PARAISO - SCCUADP 2026'), 0, 1, 'C')
        self.set_font('Arial', 'I', 9)
        self.cell(0, 5, normalizar('Relatorio Oficial de Inscritos e Logistica'), 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Pagina {self.page_no()} | Gerado em {datetime.now().strftime("%d/%m/%Y %H:%M")}', 0, 0, 'C')

def gerar_pdf_filtrado(df):
    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    
    # Criar cópia para cálculos sem alterar o original
    df_calc = df.copy()
    
    # Criar cópia limpa sem acentos para o texto do PDF
    df_pdf = df.copy()
    for col in df_pdf.columns:
        df_pdf[col] = df_pdf[col].apply(normalizar)

    unidades = df_pdf['unidade'].unique() if 'unidade' in df_pdf.columns else ["GERAL"]

    # --- LISTAGEM POR REGIONAL ---
    for unidade in unidades:
        pdf.add_page()
        pdf.set_fill_color(0, 31, 63)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, f" REGIONAL: {unidade}", 0, 1, 'L', True)
        pdf.ln(2)

        df_unidade = df_pdf[df_pdf['unidade'] == unidade]
        
        # Filtramos os departamentos existentes na unidade
        depts_presentes = df_unidade['departamento'].unique()
        
        for dept in depts_presentes:
            df_dept = df_unidade[df_unidade['departamento'] == dept]
            if not df_dept.empty:
                pdf.set_font('Arial', 'B', 10)
                pdf.set_text_color(0, 31, 63)
                pdf.set_fill_color(230, 245, 255)
                pdf.cell(0, 7, f" > Departamento: {dept}", 0, 1, 'L', True)
                
                # Cabeçalho da Tabela
                pdf.set_font('Arial', 'B', 8)
                pdf.set_text_color(255, 255, 255)
                pdf.set_fill_color(80, 80, 80)
                
                cols = [70, 35, 30, 30, 25]
                # Mudamos 'CUPONS' para 'VALOR'
                headers = ['NOME COMPLETO', 'CPF', 'TRANSPORTE', 'PAGAMENTO', 'VALOR']
                for i in range(len(headers)):
                    pdf.cell(cols[i], 7, headers[i], 1, 0, 'C', True)
                pdf.ln()

                pdf.set_font('Arial', '', 8)
                pdf.set_text_color(0, 0, 0)
                for _, row in df_dept.iterrows():
                    pdf.cell(cols[0], 6, str(row['nome'])[:35], 1, 0, 'L')
                    pdf.cell(cols[1], 6, str(row['cpf']), 1, 0, 'C')
                    pdf.cell(cols[2], 6, str(row['transporte']), 1, 0, 'C')
                    
                    status = str(row['pago'])
                    if status == 'PAGO': pdf.set_text_color(0, 100, 0)
                    else: pdf.set_text_color(150, 0, 0)
                    
                    pdf.cell(cols[3], 6, status, 1, 0, 'C')
                    pdf.set_text_color(0, 0, 0)
                    # CORREÇÃO: Pegamos o valor_total (já normalizado para string)
                    pdf.cell(cols[4], 6, f"R$ {row.get('valor_total', 0)}", 1, 1, 'C')
                pdf.ln(5)

    # --- RESUMO ESTATÍSTICO ---
    pdf.add_page()
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, "CONSOLIDADO LOGISTICO E FINANCEIRO", 0, 1, 'C')
    pdf.ln(5)

    # Cálculos corrigidos usando 'valor_total'
    total_inscritos = len(df_calc)
    vagas_bus = len(df_calc[df_calc['transporte'] == 'Ônibus'])
    vagas_aloj = len(df_calc[df_calc['alojamento'] == 'Sim'])
    
    # Nova lógica de soma financeira
    arrecadacao = pd.to_numeric(df_calc['valor_total'], errors='coerce').fillna(0).sum()
    recebido = pd.to_numeric(df_calc[df_calc['pago'] == 'Pago']['valor_total'], errors='coerce').fillna(0).sum()
    pendente = arrecadacao - recebido

    resumo = [
        ("Total de Inscritos", total_inscritos, "AZUL"),
        ("Vagas de Onibus Ocupadas", vagas_bus, "AZUL"),
        ("Vagas de Alojamento", vagas_aloj, "AZUL"),
        ("Arrecadacao Total Estimada", f"R$ {arrecadacao:.2f}", "AZUL"),
        ("Total Ja Recebido (Confirmado)", f"R$ {recebido:.2f}", "VERDE"),
        ("Total Pendente", f"R$ {pendente:.2f}", "VERMELHO")
    ]

    for label, valor, cor in resumo:
        pdf.set_font('Arial', 'B', 10)
        pdf.set_fill_color(245, 245, 245)
        pdf.cell(100, 10, f" {normalizar(label)}", 1, 0, 'L', True)
        
        if cor == "VERDE": pdf.set_text_color(0, 128, 0)
        elif cor == "VERMELHO": pdf.set_text_color(200, 0, 0)
        else: pdf.set_text_color(0, 31, 63)
        
        pdf.cell(90, 10, str(valor), 1, 1, 'C')
        pdf.set_text_color(0, 0, 0)

    # Assinaturas
    pdf.ln(30)
    y_pos = pdf.get_y()
    pdf.line(20, y_pos, 90, y_pos)
    pdf.line(110, y_pos, 180, y_pos)
    pdf.set_font('Arial', '', 8)
    pdf.set_xy(20, y_pos)
    pdf.cell(70, 5, "Responsavel Local / Regional", 0, 0, 'C')
    pdf.set_xy(110, y_pos)
    pdf.cell(70, 5, "Tesouraria Geral SCCUADP", 0, 0, 'C')

    return bytes(pdf.output())
