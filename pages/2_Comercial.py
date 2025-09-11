import streamlit as st
import pandas as pd
import re
import io
from openpyxl import load_workbook
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter

# Setando a configuração da página para ampla
st.set_page_config(layout="wide")

# Verificação de login (simulada). Se não estiver logado, exibe uma mensagem e para o script.
if not st.session_state.get('is_logged_in'):
    st.session_state['is_logged_in'] = True # Simulando login para o script funcionar.
    # Em uma aplicação real, você teria uma lógica de autenticação aqui.

st.title("Setor Comercial")
st.markdown("Bem-vindo(a) ao setor Comercial. Abaixo está o script disponível para análise.")

st.write("---")
st.subheader("📊 Análise de Canal e Pontuação")
st.markdown("Este script transforma e consolida dados de planilhas de Google Forms, e também calcula a pontuação em colunas específicas.")

def normalize_columns(columns_list):
    """Normaliza uma lista de nomes de colunas."""
    normalized_list = []
    for col in columns_list:
        col = re.sub(r'\s+', ' ', col).strip()
        col = col.replace('\n', ' ')
        normalized_list.append(col)
    return normalized_list

def transform_google_forms_data(df):
    """
    Transforma dados de Google Forms, consolidando informações e adicionando
    uma coluna 'Status' com validação de dados.
    """
    processed_records = []
    for index, row in df.iterrows():
        # Tratamento de dados baseado no script original
        data_value = row.iloc[0] if len(row) > 0 else None
        sv_value = row.iloc[1] if len(row) > 1 else None
        
        # Consolidar VD
        vd_consolidated_parts = [str(row.iloc[col_idx]).strip() for col_idx in range(2, min(5, len(row))) if pd.notna(row.iloc[col_idx])]
        vd_final = ' | '.join(vd_consolidated_parts) if vd_consolidated_parts else None
        
        # O valor do 'PARA' é a 28ª coluna (índice 27)
        para_value = row.iloc[27] if len(row) > 27 else None

        for col_idx in range(5, min(27, len(row))):
            cell_content = str(row.iloc[col_idx]).strip()
            if not cell_content or cell_content.lower() == 'nan':
                continue
            
            de_category_match = re.search(r'\((.*?)\)', cell_content)
            de_category_val = de_category_match.group(1).strip() if de_category_match else None
            
            pdv_info_raw = re.sub(r'\s*\([^)]*\)\s*$', '', cell_content).strip()
            pdv_info_val = re.sub(r'^\s*(?:\b\w+\s+)?\d+\s*[\|-]\s*', '', pdv_info_raw, 1).strip() if pdv_info_raw else None
            
            if pdv_info_val or de_category_val:
                processed_records.append({
                    'DATA': data_value,
                    'SV': sv_value,
                    'VD': vd_final,
                    'PDV': pdv_info_val,
                    'DE': de_category_val,
                    'PARA': para_value,
                    'Status': '' 
                })

    final_df = pd.DataFrame(processed_records)
    return final_df

def extract_points(column_name):
    """Função para extrair o valor numérico entre parênteses em uma string de cabeçalho."""
    match = re.search(r"\(\s*(\d+)\s*Pontos\s*\)", column_name)
    return int(match.group(1)) if match else None

def transform_points_columns(df):
    """
    Aplica a transformação de 'Presença' para pontos nas colunas
    que contêm 'Pontos' no nome.
    """
    df_transformed = df.copy()
    for col in df_transformed.columns:
        if "Pontos" in col:
            points = extract_points(col)
            if points is not None:
                # Usa 'apply' para substituir "Presença" pelo valor de pontos e outros por 0
                df_transformed[col] = df_transformed[col].apply(lambda x: points if x == "Presença" else 0)
    return df_transformed

def process_data(uploaded_file):
    """Função principal para processar e consolidar as duas transformações."""
    # Ler o arquivo
    df = pd.read_excel(uploaded_file)
    st.subheader("📄 Dados Originais")
    st.write(df)

    # Aplica a transformação de pontos primeiro
    df_with_points = transform_points_columns(df)

    # Aplica a transformação de formulários do Google no DataFrame com pontos
    final_df = transform_google_forms_data(df_with_points)

    # Adiciona a validação de dados para a coluna 'Status'
    output = io.BytesIO()
    final_df.to_excel(output, index=False)
    output.seek(0)
    
    workbook = load_workbook(output)
    sheet = workbook.active
    dropdown_options = '"Aprovado,Não Aprovado"'
    dv = DataValidation(type="list", formula1=dropdown_options, allow_blank=True)
    dv.error = 'O valor inserido não está na lista.'
    dv.errorTitle = 'Valor Inválido'
    
    # Encontra a coluna "Status" para aplicar a validação
    try:
        col_for_dropdown_letter = get_column_letter(final_df.columns.get_loc('Status') + 1)
        dv.add(f'{col_for_dropdown_letter}2:{col_for_dropdown_letter}{sheet.max_row}')
        sheet.add_data_validation(dv)
    except KeyError:
        st.warning("A coluna 'Status' não foi encontrada no DataFrame final.")
    
    output_with_dropdown = io.BytesIO()
    workbook.save(output_with_dropdown)
    output_with_dropdown.seek(0)
    
    return final_df, output_with_dropdown.getvalue()

uploaded_file = st.file_uploader("Envie o arquivo 'canal.xlsx'", type=["xlsx"])

if uploaded_file is not None:
    try:
        final_df, excel_data = process_data(uploaded_file)
        
        st.subheader("✅ Dados Transformados")
        st.dataframe(final_df)
        
        st.download_button(
            label="📥 Baixar Arquivo Processado",
            data=excel_data,
            file_name="planilha_processada.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    except Exception as e:
        st.error(f"Ocorreu um erro durante o processamento: {e}")
