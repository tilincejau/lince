import streamlit as st
import pandas as pd
import re
import io
from openpyxl import load_workbook
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter

# Verificação de login. Se não estiver logado, exibe uma mensagem e para o script.
if not st.session_state.get('is_logged_in'):
    st.warning("Você precisa estar logado para acessar esta página.")
    st.stop()

st.title("Setor Comercial")
st.markdown("Bem-vindo(a) ao setor Comercial. Abaixo está o script disponível para análise.")

st.write("---")
st.subheader("📊 Análise de Canal")
st.markdown("Este script transforma e consolida dados de planilhas de Google Forms, adicionando uma coluna de status com lista suspensa.")

def normalize_columns(columns_list):
    """Normaliza uma lista de nomes de colunas."""
    normalized_list = []
    for col in columns_list:
        col = re.sub(r'\s+', ' ', col).strip()
        col = col.replace('\n', ' ')
        normalized_list.append(col)
    return normalized_list

def transform_google_forms_data(df):
    processed_records = []
    for index, row in df.iterrows():
        data_value = row.iloc[0] if len(row) > 0 else None
        sv_value = row.iloc[1] if len(row) > 1 else None
        vd_consolidated_parts = [str(row.iloc[col_idx]).strip() for col_idx in range(2, min(5, len(row))) if pd.notna(row.iloc[col_idx])]
        vd_final = ' | '.join(vd_consolidated_parts) if vd_consolidated_parts else None
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
    
    output = io.BytesIO()
    final_df.to_excel(output, index=False)
    output.seek(0)
    
    workbook = load_workbook(output)
    sheet = workbook.active
    dropdown_options = '"Aprovado,Não Aprovado"'
    dv = DataValidation(type="list", formula1=dropdown_options, allow_blank=True)
    dv.error = 'O valor inserido não está na lista.'
    dv.errorTitle = 'Valor Inválido'
    col_for_dropdown_letter = get_column_letter(final_df.columns.get_loc('Status') + 1)
    dv.add(f'{col_for_dropdown_letter}2:{col_for_dropdown_letter}{sheet.max_row}')
    sheet.add_data_validation(dv)
    
    output_with_dropdown = io.BytesIO()
    workbook.save(output_with_dropdown)
    output_with_dropdown.seek(0)
    
    return final_df, output_with_dropdown.getvalue()

uploaded_file = st.file_uploader("Envie o arquivo 'canal.xlsx'", type=["xlsx"])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        st.subheader("📄 Dados Originais")
        st.dataframe(df.head())
        
        final_df, excel_data = transform_google_forms_data(df)
        
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
