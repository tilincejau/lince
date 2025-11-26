import streamlit as st
import base64
import pandas as pd
import re
import io
import numpy as np
from datetime import datetime, timedelta
import PyPDF2
from openpyxl import load_workbook
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter
from sqlalchemy import create_engine, text
import os
import xlsxwriter

# ====================================================================
# CONFIGURAÇÃO E CONSTANTES GLOBAIS
# ====================================================================

NAME_540_001 = '540-001 - GARRAFA 600ML' 
NAME_550_001 = '550-001 - CAIXA PLASTICA 600ML' # Constante para facilitar agrupamento

CRATE_TO_BOTTLE_MAP = {
    '546-004 - CAIXA PLASTICA 24UN 300ML': '546-001 - GARRAFA 300ML',
    '550-001 - CAIXA PLASTICA 600ML': NAME_540_001, 
    '587-002 - CAIXA PLASTICA HEINEKEN 600ML': '586-001 - GARRAFA HEINEKEN 600ML',
    '591-002 - CAIXA PLASTICA HEINEKEN 330ML': '593-001 - GARRAFA HEINEKEN 330ML',
    '555-001 - CAIXA PLASTICA 1L': '541-002 - GARRAFA 1L'
}

FACTORS = {
    '546-004 - CAIXA PLASTICA 24UN 300ML': 24,
    '550-001 - CAIXA PLASTICA 600ML': 24,
    '587-002 - CAIXA PLASTICA HEINEKEN 600ML': 24,
    '591-002 - CAIXA PLASTICA HEINEKEN 330ML': 24,
    '555-001 - CAIXA PLASTICA 1L': 12
}

# ====================================================================
# LOGIN E PAGINA INICIAL
# ====================================================================

def login_form():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h2 style='text-align: center; color: #004d99; font-family: 'Arial Black', sans-serif;'>Lince Distribuidora</h2>", unsafe_allow_html=True)
        st.markdown("---")
        with st.form("login_form", clear_on_submit=False):
            st.markdown("Por favor, insira suas credenciais para continuar.")
            username = st.text_input("Usuário", key="username_input", placeholder="Digite seu nome de usuário")
            password = st.text_input("Senha", type="password", key="password_input", placeholder="Digite sua senha")
            st.markdown("<br>", unsafe_allow_html=True)
            submit_button = st.form_submit_button("Entrar", use_container_width=True)
        if submit_button:
            if username in st.session_state.LOGIN_INFO and st.session_state.LOGIN_INFO[username] == password:
                st.session_state['is_logged_in'] = True
                st.session_state['username'] = username
                st.session_state['current_page'] = 'home'
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")

def main_page():
    st.markdown(f"<h1 style='text-align: center;'>Página Inicial</h1>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='text-align: center;'>Bem-vindo(a), **{st.session_state['username']}**!</h3>", unsafe_allow_html=True)
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Logística", use_container_width=True):
            st.session_state['current_page'] = 'logistics'
            st.rerun()
    with col2:
        if st.button("Comercial", use_container_width=True):
            st.session_state['current_page'] = 'commercial'
            st.rerun()
    st.markdown("---")
    if st.button("Sair", use_container_width=True):
        st.session_state['is_logged_in'] = False
        st.session_state.pop('username', None)
        st.session_state.pop('current_page', None)
        st.rerun()

def setup_database():
    engine = create_engine('sqlite:///vasilhames.db')
    return engine

def load_from_db(table_name, engine):
    if engine.dialect.has_table(engine.connect(), table_name):
        return pd.read_sql_table(table_name, con=engine)
    return pd.DataFrame()

# ====================================================================
# SETOR DE LOGÍSTICA
# ====================================================================
def logistics_page():
    st.title("Setor de Logística")
    st.markdown("Bem-vindo(a) ao setor de Logística. Abaixo estão os scripts disponíveis para análise.")
    
    script_choice = st.selectbox(
        "Selecione um script para executar:",
        ("Selecione...", "Acurácia", "Validade", "Vasilhames", "Abastecimento"),
        key="log_select" 
    )
    
    st.write("---")

    # --- SCRIPT ACURÁCIA ---
    if script_choice == "Acurácia":
        st.subheader("Acurácia de Estoque")
        uploaded_file = st.file_uploader("Envie o arquivo 'Acuracia estoque' (.csv ou .xlsx)", type=["csv", "xlsx"], key="acuracia_uploader")
        if uploaded_file is not None:
            try:
                df = None
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file, header=[0, 1])
                elif uploaded_file.name.endswith('.xlsx'):
                    df = pd.read_excel(uploaded_file, header=[0, 1], sheet_name=0)
                else:
                    st.error("Formato de arquivo não suportado."); return 
                products_to_remove = ['185039 - Garrafa 0,30l', '471 - Garrafa 0,60l (3 )']
                try:
                    prod_cod_col = df.columns[0]
                    df_data = df.set_index(prod_cod_col)
                except IndexError: st.error("Erro ao definir o índice do DataFrame."); return
                df_data = df_data[~df_data.index.isin(products_to_remove)].copy()
                df_data = df_data[~df_data.index.astype(str).str.contains('Totais', na=False)].copy()
                data_types_from_file = ['Contagem - $', 'Diferença - $', 'Saldo Final - $'] 
                first_level_cols = [col[0] for col in df.columns]
                unique_dates = sorted(list(set([col for col in first_level_cols if col not in ['Data', 'Prod Cód', 'Totais'] and 'Unnamed' not in str(col)])))
                new_rows = []
                for product in df_data.index:
                    for date in unique_dates:
                        row_data = {'Prod Cód': product, 'Dia': date}
                        for data_type in data_types_from_file: 
                            try:
                                col_name = (date, data_type)
                                value = df_data.loc[product, col_name]
                                if isinstance(value, str):
                                    if value.strip() == '-': value = 0
                                row_data[data_type] = pd.to_numeric(value, errors='coerce')
                            except KeyError: row_data[data_type] = np.nan
                        new_rows.append(row_data)
                df_final = pd.DataFrame(new_rows)
                df_final.rename(columns={'Contagem - $': 'Contagem', 'Diferença - $': 'Diferença', 'Saldo Final - $': 'Saldo Final'}, inplace=True)
                df_final['Saldo Final'] = df_final['Saldo Final'].fillna(0).apply(lambda x: max(0, x))
                df_final['Diferença'] = df_final['Diferença'].fillna(0).abs()
                df_final['Contagem'] = df_final['Contagem'].fillna(0)
                df_final = df_final.sort_values(by=['Dia', 'Prod Cód'])
                df_final['Dia'] = pd.to_datetime(df_final['Dia']).dt.strftime('%Y-%m-%d')
                numeric_cols = ['Saldo Final', 'Contagem', 'Diferença'] 
                existing_numeric_cols = [col for col in numeric_cols if col in df_final.columns]
                df_final[existing_numeric_cols] = df_final[existing_numeric_cols].round(2)
                desired_order = ['Prod Cód', 'Dia', 'Contagem', 'Diferença', 'Saldo Final']
                df_final = df_final[desired_order]
                st.subheader("📊 Resultado da Acurácia")
                st.dataframe(df_final)
                excel_data = io.BytesIO()
                df_final.to_excel(excel_data, index=False, engine='xlsxwriter')
                excel_data.seek(0)
                st.download_button(label="📥 Baixar Arquivo Processado", data=excel_data, file_name='Acuracia_estoque_processado.xlsx', mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            except Exception as e:
                st.error(f"Ocorreu um erro no script de Acurácia: {e}")

    elif script_choice == "Validade":
        st.subheader("Controle de Validade")
        def parse_estoque_txt_st(file_content):
            lines = [line.decode('latin1') for line in file_content.getvalue().splitlines()]
            separator_string = '-' * 116
            separator_indices = [i for i, line in enumerate(lines) if separator_string in line]
            if len(separator_indices) < 2: return pd.DataFrame()
            start_line = separator_indices[1] + 1
            col_names = ['COD.RED.', 'DESCRIÇÃO', 'SLD INICIAL CX', 'SLD INICIAL UN', 'ENTRADAS CX', 'ENTRADAS UN', 'SAÍDAS CX', 'SAÍDAS UN', 'SALDO FÍSICO CX', 'SALDO FÍSICO UN', 'CONT. FÍSICA CX', 'CONT. FÍSICA UN', 'DIFERENÇA CX', 'DIFERENÇA UN']
            data = []
            pattern = re.compile(r'^\s*(\d+)\s+(.+?)\s*([-+]?\d*)\s*([-+]?\d*)\s*I\s*([-+]?\d*)\s*([-+]?\d*)\s*I\s*([-+]?\d*)\s*([-+]?\d*)\s*I\s*([-+]?\d*)\s*([-+]?\d*)\s*I\s*([-+]?\d*)\s*([-+]?\d*)\s*I\s*([-+]?\d*)\s*([-+]?\d*)\s*I')
            for line in lines[start_line:]:
                line = line.strip()
                if not line or 'TOTAL GERAL' in line: continue
                match = pattern.match(line)
                if match:
                    groups = list(match.groups())
                    row_values = [groups[0], groups[1].strip()]
                    for i in range(2, len(groups), 2):
                        cx = groups[i].strip() if groups[i] and groups[i].strip() else '0'
                        un = groups[i+1].strip() if groups[i+1] and groups[i+1].strip() else '0'
                        row_values.extend([int(cx), int(un)])
                    if len(row_values) == 14: data.append(row_values)
            return pd.DataFrame(data, columns=col_names)
        def extract_units_per_box(product_name):
            product_name = str(product_name).upper().replace(' ', '')
            match_multiplication = re.search(r'(\d+)X(\d+)(?:UN|U)', product_name)
            if match_multiplication: return int(match_multiplication.group(1)) * int(match_multiplication.group(2))
            match_direct = re.search(r'(\d+)(?:UN|U)', product_name)
            if match_direct: return int(match_direct.group(1)) 
            return 1
        uploaded_excel_file = st.file_uploader("Envie o arquivo Excel 'Controle de Validade.xlsx'", type=["xlsx"], key="validade_excel_uploader") 
        uploaded_txt_file = st.file_uploader("Envie o arquivo de texto de estoque", type=["txt"], key="validade_txt_uploader")
        if uploaded_excel_file is not None and uploaded_txt_file is not None:
            try:
                df_validade = pd.read_excel(uploaded_excel_file)
                df_validade.columns = df_validade.columns.str.replace(r'\s+', ' ', regex=True).str.strip()
                df_estoque = parse_estoque_txt_st(uploaded_txt_file)
                if df_estoque.empty: st.warning("O arquivo TXT está vazio ou não pôde ser processado."); return
                validity_cols = ['Validade', 'Validade.1', 'Validade.2', 'Validade.3', 'Validade.4']
                quantity_caixa_cols = ['Quantidade (CAIXA)', 'Quantidade 2 (CAIXA)', 'Quantidade 3 (CAIXA)', 'Quantidade 4 (CAIXA)', 'Quantidade 5 (CAIXA)']
                quantity_unidade_cols = ['Quantidade (UNIDADE)', 'Quantidade 2 (UNIDADE)', 'Quantidade 3 (UNIDADE)', 'Quantidade 4 (UNIDADE)', 'Quantidade 5 (UNIDADE)']
                all_validity_entries = []
                for i in range(len(validity_cols)):
                    cols_to_check = ['Qual Produto ?', validity_cols[i], quantity_caixa_cols[i], quantity_unidade_cols[i]]
                    if all(col in df_validade.columns for col in cols_to_check):
                        temp_df = df_validade[cols_to_check].copy()
                        temp_df.rename(columns={validity_cols[i]: 'Validade', quantity_caixa_cols[i]: 'Quantidade (CAIXA)', quantity_unidade_cols[i]: 'Quantidade (UNIDADE)'}, inplace=True)
                        all_validity_entries.append(temp_df)
                all_validity_entries = [df for df in all_validity_entries if not df.dropna(subset=['Validade']).empty]
                melted_df_validade_all = pd.concat(all_validity_entries, ignore_index=True) if all_validity_entries else pd.DataFrame(columns=['Qual Produto ?', 'Validade', 'Quantidade (CAIXA)', 'Quantidade (UNIDADE)'])
                melted_df_validade_all.dropna(subset=['Validade'], inplace=True)
                melted_df_validade_all['Validade'] = pd.to_datetime(melted_df_validade_all['Validade'], errors='coerce')
                melted_df_validade_all.dropna(subset=['Validade'], inplace=True)
                melted_df_validade_all['Quantidade (CAIXA)'] = pd.to_numeric(melted_df_validade_all['Quantidade (CAIXA)'], errors='coerce').fillna(0)
                melted_df_validade_all['Quantidade (UNIDADE)'] = pd.to_numeric(melted_df_validade_all['Quantidade (UNIDADE)'], errors='coerce').fillna(0)
                split_data_validade = melted_df_validade_all['Qual Produto ?'].astype(str).str.split(' - ', n=1, expand=True)
                melted_df_validade_all['Codigo Produto'] = split_data_validade[0].str.strip()
                melted_df_validade_all['Nome Produto'] = split_data_validade[1].str.strip()
                melted_df_validade_all['Units_Per_Box_Temp'] = melted_df_validade_all['Nome Produto'].apply(extract_units_per_box)
                grouped = melted_df_validade_all.groupby(['Codigo Produto', 'Nome Produto', 'Validade']).agg({'Quantidade (CAIXA)': 'sum', 'Quantidade (UNIDADE)': 'sum', 'Units_Per_Box_Temp': 'first'}).reset_index()
                def convert_total_units_to_boxes_and_units(row):
                    units_per_box = row['Units_Per_Box_Temp'] or 1
                    total_units = (row['Quantidade (CAIXA)'] * units_per_box) + row['Quantidade (UNIDADE)']
                    row['Quantidade (CAIXA)'] = total_units // units_per_box
                    row['Quantidade (UNIDADE)'] = total_units % units_per_box
                    return row
                grouped = grouped.apply(convert_total_units_to_boxes_and_units, axis=1)
                grouped.drop('Units_Per_Box_Temp', axis=1, inplace=True)
                data_atual = datetime.now()
                grouped['Dias para Vencer'] = (grouped['Validade'] - data_atual).dt.days
                conditions = [grouped['Dias para Vencer'] <= 45, (grouped['Dias para Vencer'] > 45) & (grouped['Dias para Vencer'] <= 60), grouped['Dias para Vencer'] > 60]
                choices = ['VALIDADE CURTA', 'ATENÇÃO', 'OK']
                grouped['Status Validade'] = np.select(conditions, choices, default='Indefinido')
                grouped['Validade_DateOnly'] = grouped['Validade'].dt.date
                sorted_grouped = grouped.sort_values(by=['Codigo Produto', 'Validade']).reset_index(drop=True)
                sorted_grouped['Validade_Rank'] = sorted_grouped.groupby('Codigo Produto')['Validade'].rank(method='first').astype(int)
                final_rows = []
                for product_code, group in sorted_grouped.groupby('Codigo Produto'):
                    row = {'Codigo Produto': product_code, 'Nome Produto': group['Nome Produto'].iloc[0]}
                    for _, r in group.iterrows():
                        i = r['Validade_Rank']
                        row[f'Validade {i}'] = r['Validade_DateOnly']
                        row[f'Quantidade (CAIXA) {i}'] = r['Quantidade (CAIXA)']
                        row[f'Quantidade (UNIDADE) {i}'] = r['Quantidade (UNIDADE)']
                        row[f'Dias para Vencer {i}'] = r['Dias para Vencer']
                        row[f'Status Validade {i}'] = r['Status Validade']
                    final_rows.append(row)
                final_df = pd.DataFrame(final_rows)
                if not df_estoque.empty:
                    df_estoque['COD.RED.'] = df_estoque['COD.RED.'].astype(str)
                    final_df['Codigo Produto'] = final_df['Codigo Produto'].astype(str)
                    df_saldo = df_estoque[['COD.RED.', 'SALDO FÍSICO CX', 'SALDO FÍSICO UN']].drop_duplicates('COD.RED.')
                    df_saldo.rename(columns={'SALDO FÍSICO CX': 'Saldo Físico TXT Caixa', 'SALDO FÍSICO UN': 'Saldo Físico TXT Unidade'}, inplace=True)
                    final_df = pd.merge(final_df, df_saldo, how='left', left_on='Codigo Produto', right_on='COD.RED.')
                    final_df.drop('COD.RED.', axis=1, inplace=True)
                quantidade_caixa_cols = [col for col in final_df.columns if re.match(r'Quantidade \(CAIXA\) \d+', col)]
                quantidade_unidade_cols = [col for col in final_df.columns if re.match(r'Quantidade \(UNIDADE\) \d+', col)]
                final_df['Contagem Fisica CX'] = final_df[quantidade_caixa_cols].sum(axis=1)
                final_df['Contagem Fisica UN'] = final_df[quantidade_unidade_cols].sum(axis=1)
                st.subheader("✅ Relatório de Validade Gerado")
                st.dataframe(final_df)
                excel_data = io.BytesIO()
                final_df.to_excel(excel_data, sheet_name='Controle de Estoque', index=False)
                excel_data.seek(0)
                st.download_button(label="📥 Baixar Relatório de Validade", data=excel_data, file_name="Controle_Estoque_Completo.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            except Exception as e:
                st.error(f"Ocorreu um erro ao processar os arquivos: {e}")

    # --- SCRIPT VASILHAMES FINAL ---
    elif script_choice == "Vasilhames":
        st.subheader("Controle de Vasilhames")
        engine = setup_database()

        st.write("---")
        st.subheader("⚙️ Gerenciamento")
        col_reset, col_info = st.columns([1, 3])
        with col_reset:
            if st.button("🗑️ Limpar Banco de Dados (Reiniciar)", type="primary", help="Cuidado: Isso apaga todo o histórico salvo no banco!"):
                try:
                    with engine.connect() as conn:
                        conn.execute(text("DROP TABLE IF EXISTS txt_data"))
                        conn.execute(text("DROP TABLE IF EXISTS pdf_data"))
                        conn.execute(text("DROP TABLE IF EXISTS vendas_data"))
                        conn.execute(text("DROP TABLE IF EXISTS excel_data"))
                        conn.commit()
                    st.success("Histórico apagado com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao limpar o banco: {e}")
        st.write("---")

        def process_vendas_file(file_content):
            content = file_content.getvalue().decode('latin1')
            filename_date_match = re.search(r'VENDA(\d{4})\.TXT', file_content.name)
            effective_date_str = None
            effective_date_full = None
            
            if filename_date_match:
                day = filename_date_match.group(1)[:2]
                month = filename_date_match.group(1)[2:]
                year = datetime.now().year
                now = datetime.now()
                if now.month == 1 and month == '12': year = year - 1
                effective_date_obj = datetime.strptime(f"{day}/{month}/{year}", '%d/%m/%Y')
                effective_date_str = effective_date_obj.strftime('%d/%m')
                effective_date_full = effective_date_obj.date()
            else:
                 effective_date_obj = datetime.now()
                 effective_date_str = effective_date_obj.strftime('%d/%m')
                 effective_date_full = effective_date_obj.date()

            # MAPA DE VENDAS EXPANDIDO (COM TODOS OS CÓDIGOS RELEVANTES)
            sales_map = {
                # Garrafas (apontam para garrafas)
                '540-001': NAME_540_001,
                '541-002': '541-002 - GARRAFA 1L',
                '586-001': '586-001 - GARRAFA HEINEKEN 600ML',
                '593-001': '593-001 - GARRAFA HEINEKEN 330ML',
                # Caixas (apontam para caixas)
                '555-001': '555-001 - CAIXA PLASTICA 1L',
                '587-002': '587-002 - CAIXA PLASTICA HEINEKEN 600ML',
                '591-002': '591-002 - CAIXA PLASTICA HEINEKEN 330ML',
                # Variantes de Caixa 600ml (TODAS devem apontar para 550-001)
                '550-001': NAME_550_001,
                '550-012': NAME_550_001, 
                '803-025': NAME_550_001,
                '803-036': NAME_550_001,
                '803-037': NAME_550_001,
                '803-039': NAME_550_001  # Caixa Cinza
            }

            parsed_data = []
            lines = content.splitlines()
            
            for line in lines:
                line = line.strip()
                match = re.search(r'^(\d{6}).*?([\d\.]+)\s*\/', line)
                
                if match:
                    raw_code = match.group(1)
                    raw_qty = match.group(2)
                    qty = int(raw_qty.replace('.', ''))
                    formatted_code = f"{raw_code[:3]}-{raw_code[3:]}"
                    
                    if formatted_code in sales_map:
                        vasilhame = sales_map[formatted_code]
                        parsed_data.append({'Vasilhame': vasilhame, 'Vendas': qty, 'Dia': effective_date_str, 'DataCompleta': effective_date_full})

            if not parsed_data: return None
            return pd.DataFrame(parsed_data)

        def process_txt_file_st(file_content):
            content = file_content.getvalue().decode('latin1')
            filename_date_match = re.search(r'ESTOQUE(\d{4})\.TXT', file_content.name)
            effective_date_str = None
            effective_date_full = None
            if filename_date_match:
                day = filename_date_match.group(1)[:2]
                month = filename_date_match.group(1)[2:]
                year = datetime.now().year
                now = datetime.now()
                if now.month == 1 and month == '12': year = year - 1
                effective_date_obj = datetime.strptime(f"{day}/{month}/{year}", '%d/%m/%Y')
                effective_date_str = effective_date_obj.strftime('%d/%m')
                effective_date_full = effective_date_obj.date()
            else: st.error(f"Nome do arquivo TXT inválido: {file_content.name}"); return None, None, None 

            product_code_to_vasilhame_map = {
                '563-008': '563-008 - BARRIL INOX 30L', '564-009': '564-009 - BARRIL INOX 50L', '591-002': '591-002 - CAIXA PLASTICA HEINEKEN 330ML', 
                '587-002': '587-002 - CAIXA PLASTICA HEINEKEN 600ML', '550-001': '550-001 - CAIXA PLASTICA 600ML', '555-001': '555-001 - CAIXA PLASTICA 1L', 
                '546-004': '546-004 - CAIXA PLASTICA 24UN 300ML', '565-002': '565-002 - CILINDRO CO2', 
                '546-001': CRATE_TO_BOTTLE_MAP['546-004 - CAIXA PLASTICA 24UN 300ML'],
                '540-001': NAME_540_001, 
                '541-002': CRATE_TO_BOTTLE_MAP['555-001 - CAIXA PLASTICA 1L'],
                '586-001': CRATE_TO_BOTTLE_MAP['587-002 - CAIXA PLASTICA HEINEKEN 600ML'],
                '593-001': CRATE_TO_BOTTLE_MAP['591-002 - CAIXA PLASTICA HEINEKEN 330ML'],
                '550-012': '550-001 - CAIXA PLASTICA 600ML', '803-025': '550-001 - CAIXA PLASTICA 600ML',
                '803-036': '550-001 - CAIXA PLASTICA 600ML', '803-037': '550-001 - CAIXA PLASTICA 600ML',
                '803-039': '550-001 - CAIXA PLASTICA 600ML' 
            }

            parsed_data = []
            lines = content.splitlines()
            current_code = None
            for line in lines:
                line = line.strip()
                if not line or '---' in line or 'DATA' in line or 'REFERENTE' in line: continue
                code_match = re.search(r'^(\d{3}-\d{3})', line)
                if code_match:
                    current_code = code_match.group(1)
                    qty_match_full = re.search(r'\s+([\d\.]+)\s+[\d\.]+,\d+', line)
                    if qty_match_full:
                        qty_str = qty_match_full.group(1).replace('.', '')
                        if current_code in product_code_to_vasilhame_map:
                            parsed_data.append({'PRODUTO_CODE': current_code, 'QUANTIDADE': int(qty_str)})
                        current_code = None
                    else:
                         qty_match_end = re.search(r'\s+([\d\.]+)$', line)
                         if qty_match_end:
                             qty_str = qty_match_end.group(1).replace('.', '')
                             if current_code in product_code_to_vasilhame_map:
                                 parsed_data.append({'PRODUTO_CODE': current_code, 'QUANTIDADE': int(qty_str)})
                             current_code = None
                elif current_code:
                    qty_match_next = re.search(r'([\d\.]+)\s+[\d\.]+,\d+', line)
                    if qty_match_next:
                        qty_str = qty_match_next.group(1).replace('.', '')
                        if current_code in product_code_to_vasilhame_map:
                            parsed_data.append({'PRODUTO_CODE': current_code, 'QUANTIDADE': int(qty_str)})
                        current_code = None 
            if not parsed_data: return None, effective_date_str, effective_date_full
            df_estoque = pd.DataFrame(parsed_data)
            df_estoque['Vasilhame'] = df_estoque['PRODUTO_CODE'].map(product_code_to_vasilhame_map)
            df_txt_qty = df_estoque.groupby('Vasilhame')['QUANTIDADE'].sum().reset_index()
            df_txt_qty.rename(columns={'QUANTIDADE': 'Qtd_emprestimo'}, inplace=True)
            return df_txt_qty, effective_date_str, effective_date_full

        def process_pdf_content(pdf_file, product_map):
            parsed_data = []
            filename_match = re.search(r'([a-zA-Z\s]+)\s+(\d{2}-\d{2}-\d{4})\.pdf', pdf_file.name)
            if not filename_match: st.error(f"Erro no nome do arquivo PDF: {pdf_file.name}"); return pd.DataFrame()
            source_name = filename_match.group(1).strip()
            date_str = filename_match.group(2) 
            effective_date_obj = datetime.strptime(date_str, '%d-%m-%Y')
            effective_date_str = effective_date_obj.strftime('%d/%m')
            effective_date_full = effective_date_obj.date()
            source_to_col_map = {'PONTA GROSSA': 'Ponta Grossa (0328)', 'ARARAQUARA': 'Araraquara (0336)', 'ITU': 'Itu (0002)'}
            col_suffix = source_to_col_map.get(source_name.upper(), source_name)
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_file.getvalue()))
            pdf_content = ""
            for page in pdf_reader.pages: pdf_content += page.extract_text()
            data_line_pattern = re.compile(r'^\s*"?(\d{15,})[^"\n]*?"?.*?"?([-+]?[\d.,]+)"?\s*$', re.MULTILINE)
            for line_match in data_line_pattern.finditer(pdf_content):
                material_code = line_match.group(1).strip()
                saldo_str = line_match.group(2).replace('.', '').replace(',', '.').strip()
                try: saldo = float(saldo_str)
                except ValueError: saldo = 0.0
                if material_code in product_map:
                    vasilhame = product_map[material_code]
                    credito = abs(saldo) if saldo < 0 else 0.0
                    debito = saldo if saldo >= 0 else 0.0
                    parsed_data.append({'Vasilhame': vasilhame, 'Dia': effective_date_str, 'DataCompleta': effective_date_full, f'Credito {col_suffix}': credito, f'Debito {col_suffix}': debito})
            if not parsed_data: st.warning(f"Nenhum dado encontrado no PDF: {pdf_file.name}"); return pd.DataFrame()
            df_parsed = pd.DataFrame(parsed_data)
            pdf_value_cols = [col for col in df_parsed.columns if 'Credito' in col or 'Debito' in col]
            agg_dict = {col: 'sum' for col in pdf_value_cols}; agg_dict['DataCompleta'] = 'max'
            return df_parsed.groupby(['Vasilhame', 'Dia'], as_index=False).agg(agg_dict)
        
        uploaded_txt_files = st.file_uploader("Envie os arquivos TXT de empréstimos (Ex: ESTOQUE0102.TXT)", type=["txt"], accept_multiple_files=True, key="vasil_txt_uploader") 
        uploaded_vendas_files = st.file_uploader("Envie os arquivos TXT de Vendas (Ex: VENDA2411.TXT) [Opcional]", type=["txt"], accept_multiple_files=True, key="vasil_vendas_uploader")
        uploaded_excel_contagem = st.file_uploader("Envie o arquivo Excel de contagem (Ex: Contagem Vasilhames.xlsx)", type=["xlsx"], key="vasil_excel_uploader")
        uploaded_pdf_files = st.file_uploader("Envie os arquivos PDF de fábrica (Ex: PONTA GROSSA 07-11-2025.pdf)", type=["pdf"], accept_multiple_files=True, key="vasil_pdf_uploader")
        
        if st.button("Processar e Consolidar Dados"):
            if uploaded_txt_files and uploaded_excel_contagem is not None:
                try:
                    st.info("Processando...")
                    
                    df_old_txt_data = load_from_db('txt_data', engine)
                    df_old_pdf_data = load_from_db('pdf_data', engine)
                    df_old_vendas_data = load_from_db('vendas_data', engine)
                    df_old_excel_data = load_from_db('excel_data', engine)

                    new_txt_data_list = []
                    for uploaded_txt_file in uploaded_txt_files:
                        df_txt_qty, effective_date_str, effective_date_full = process_txt_file_st(uploaded_txt_file)
                        if df_txt_qty is not None:
                            df_txt_qty['Dia'] = effective_date_str
                            df_txt_qty['DataCompleta'] = effective_date_full
                            new_txt_data_list.append(df_txt_qty)
                    
                    if new_txt_data_list:
                        df_new_txt = pd.concat(new_txt_data_list, ignore_index=True)
                        df_all_txt_combined = pd.concat([df_old_txt_data, df_new_txt], ignore_index=True)
                        if 'DataCompleta' in df_all_txt_combined.columns: df_all_txt_combined['DataCompleta'] = pd.to_datetime(df_all_txt_combined['DataCompleta'], errors='coerce')
                        df_all_processed_txt_data = df_all_txt_combined.groupby(['Vasilhame', 'Dia']).agg(Qtd_emprestimo=('Qtd_emprestimo', 'sum'), DataCompleta=('DataCompleta', 'max')).reset_index()
                        df_all_processed_txt_data.to_sql('txt_data', con=engine, if_exists='replace', index=False)
                        st.success("Dados TXT atualizados!")
                    else: df_all_processed_txt_data = df_old_txt_data 
                    
                    new_vendas_data_list = []
                    if uploaded_vendas_files:
                        for v_file in uploaded_vendas_files:
                            df_v = process_vendas_file(v_file)
                            if df_v is not None: new_vendas_data_list.append(df_v)
                    
                    if new_vendas_data_list:
                        df_new_vendas = pd.concat(new_vendas_data_list, ignore_index=True)
                        df_all_vendas_combined = pd.concat([df_old_vendas_data, df_new_vendas], ignore_index=True)
                        if 'DataCompleta' in df_all_vendas_combined.columns: df_all_vendas_combined['DataCompleta'] = pd.to_datetime(df_all_vendas_combined['DataCompleta'], errors='coerce')
                        df_all_processed_vendas_data = df_all_vendas_combined.groupby(['Vasilhame', 'Dia']).agg(Vendas=('Vendas', 'sum'), DataCompleta=('DataCompleta', 'max')).reset_index()
                        df_all_processed_vendas_data.to_sql('vendas_data', con=engine, if_exists='replace', index=False)
                        st.success("Dados de Vendas atualizados!")
                    else:
                        df_all_processed_vendas_data = df_old_vendas_data
                    
                    if df_all_processed_vendas_data.empty:
                         df_all_processed_vendas_data = pd.DataFrame(columns=['Vasilhame', 'Dia', 'Vendas', 'DataCompleta'])

                    new_pdf_data_list = []
                    if uploaded_pdf_files:
                        pdf_map = {
                            '000000000000215442': '587-002 - CAIXA PLASTICA HEINEKEN 600ML', 
                            '000000000000215208': '587-002 - CAIXA PLASTICA HEINEKEN 600ML', 
                            '000000000000381411': '591-002 - CAIXA PLASTICA HEINEKEN 330ML', 
                            '000000000000107380': '555-001 - CAIXA PLASTICA 1L', 
                            '000000000000152598': '546-004 - CAIXA PLASTICA 24UN 300ML', 
                            '000000000000000470': '550-001 - CAIXA PLASTICA 600ML',
                            '000000000000048261': '563-008 - BARRIL INOX 30L', 
                            '000000000000048272': '564-009 - BARRIL INOX 50L',
                            '000000000000185039': CRATE_TO_BOTTLE_MAP['546-004 - CAIXA PLASTICA 24UN 300ML'],
                            '000000000000002496': NAME_540_001, 
                            '000000000000107523': CRATE_TO_BOTTLE_MAP['555-001 - CAIXA PLASTICA 1L'],
                            '000000000000152592': CRATE_TO_BOTTLE_MAP['546-004 - CAIXA PLASTICA 24UN 300ML'],
                            '000000000000215443': CRATE_TO_BOTTLE_MAP['587-002 - CAIXA PLASTICA HEINEKEN 600ML'],
                            '000000000000381408': CRATE_TO_BOTTLE_MAP['591-002 - CAIXA PLASTICA HEINEKEN 330ML'],
                            '000000000000152597': CRATE_TO_BOTTLE_MAP['546-004 - CAIXA PLASTICA 24UN 300ML'], 
                            '000000000000000471': NAME_540_001,       
                            '000000000000107522': CRATE_TO_BOTTLE_MAP['555-001 - CAIXA PLASTICA 1L'],        
                            '000000000000215209': CRATE_TO_BOTTLE_MAP['587-002 - CAIXA PLASTICA HEINEKEN 600ML'], 
                            '000000000000381409': CRATE_TO_BOTTLE_MAP['591-002 - CAIXA PLASTICA HEINEKEN 330ML']  
                        }
                        for pdf_file in uploaded_pdf_files:
                            df_pdf_current = process_pdf_content(pdf_file, pdf_map)
                            if not df_pdf_current.empty: new_pdf_data_list.append(df_pdf_current)
                    
                    if new_pdf_data_list:
                        df_new_pdf = pd.concat(new_pdf_data_list, ignore_index=True)
                        df_all_pdf_combined = pd.concat([df_old_pdf_data, df_new_pdf], ignore_index=True)
                        pdf_value_cols = [col for col in df_all_pdf_combined.columns if 'Credito' in col or 'Debito' in col]
                        df_all_pdf_combined[pdf_value_cols] = df_all_pdf_combined[pdf_value_cols].fillna(0)
                        if 'DataCompleta' in df_all_pdf_combined.columns: df_all_pdf_combined['DataCompleta'] = pd.to_datetime(df_all_pdf_combined['DataCompleta'], errors='coerce')
                        agg_dict = {col: 'sum' for col in pdf_value_cols}; agg_dict['DataCompleta'] = 'max' 
                        if pdf_value_cols: df_all_processed_pdf_data = df_all_pdf_combined.groupby(['Vasilhame', 'Dia'], as_index=False).agg(agg_dict)
                        else: df_all_processed_pdf_data = df_all_pdf_combined.groupby(['Vasilhame', 'Dia'], as_index=False).agg(DataCompleta=('DataCompleta', 'max')).reset_index()
                        df_all_processed_pdf_data.to_sql('pdf_data', con=engine, if_exists='replace', index=False)
                        st.success("Dados PDF atualizados!")
                    else: df_all_processed_pdf_data = df_old_pdf_data
                    
                    if df_all_processed_txt_data.empty: df_all_processed_txt_data = pd.DataFrame(columns=['Vasilhame', 'Dia', 'Qtd_emprestimo', 'DataCompleta'])
                    if df_all_processed_pdf_data.empty: df_all_processed_pdf_data = pd.DataFrame(columns=['Vasilhame', 'Dia', 'DataCompleta'])

                    df_contagem = pd.read_excel(uploaded_excel_contagem, sheet_name='Respostas ao formulário 1')
                    df_contagem['Carimbo de data/hora'] = pd.to_datetime(df_contagem['Carimbo de data/hora'])
                    df_contagem['DataCompleta'] = df_contagem['Carimbo de data/hora'].dt.date
                    df_contagem['Dia'] = df_contagem['Carimbo de data/hora'].dt.strftime('%d/%m')
                    
                    def map_excel_names_and_get_target(name):
                        name_upper = str(name).upper()
                        target_crate = name 
                        target_bottle = None
                        factor = 1
                        
                        # GARRAFAS
                        if '063-005' in name_upper: target_bottle = '546-001 - GARRAFA 300ML'; return None, target_bottle, 1
                        if '540-001' in name_upper: target_bottle = NAME_540_001; return None, target_bottle, 1
                        if '541-002' in name_upper: target_bottle = '541-002 - GARRAFA 1L'; return None, target_bottle, 1
                        if '586-001' in name_upper: target_bottle = '586-001 - GARRAFA HEINEKEN 600ML'; return None, target_bottle, 1
                        if '593-001' in name_upper: target_bottle = '593-001 - GARRAFA HEINEKEN 330ML'; return None, target_bottle, 1

                        # CAIXAS
                        if '550-012' in name_upper or 'EISENBAHN' in name_upper or '550-001' in name_upper or 'MISTA' in name_upper or 'AMBEV' in name_upper or 'CINZA' in name_upper:
                             target_crate = NAME_550_001
                        elif '587-002' in name_upper or ('HEINEKEN' in name_upper and '600' in name_upper): target_crate = '587-002 - CAIXA PLASTICA HEINEKEN 600ML'
                        elif '546-004' in name_upper: target_crate = '546-004 - CAIXA PLASTICA 24UN 300ML'
                        elif '591-002' in name_upper: target_crate = '591-002 - CAIXA PLASTICA HEINEKEN 330ML'
                        elif '555-001' in name_upper: target_crate = '555-001 - CAIXA PLASTICA 1L'

                        if target_crate in CRATE_TO_BOTTLE_MAP:
                            target_bottle = CRATE_TO_BOTTLE_MAP[target_crate]
                            factor = FACTORS.get(target_crate, 1)
                            
                        return target_crate, target_bottle, factor

                    def calculate_assets(row):
                        target_crate, target_bottle, factor = map_excel_names_and_get_target(row['Qual vasilhame ?'])
                        garrafa_cheia = 0.0; caixa_vazia = 0.0; caixa_cheia = 0.0
                        
                        if 'Quantidade estoque cheias?' in row.index and pd.notnull(row['Quantidade estoque cheias?']):
                            qtd_cheias = float(row.get('Quantidade estoque cheias?', 0) or 0)
                            qtd_vazias = float(row.get('Quantidade estoque vazias?', 0) or 0)
                            qtd_entrega = float(row.get('Em transito (Entrega)?', 0) or 0)
                            qtd_carreta = float(row.get('Em transito (carreta)?', 0) or 0)

                            total_cheias_fisico = qtd_cheias + qtd_entrega + qtd_carreta
                            total_geral_garrafa = qtd_cheias + qtd_vazias + qtd_entrega + qtd_carreta

                            if target_crate is None and target_bottle is not None:
                                garrafa_cheia = total_geral_garrafa
                                caixa_cheia = 0
                                caixa_vazia = 0
                            elif target_bottle:
                                garrafa_cheia = total_cheias_fisico * factor
                                caixa_vazia = qtd_vazias
                                caixa_cheia = total_cheias_fisico
                            else:
                                caixa_cheia = total_cheias_fisico
                                caixa_vazia = qtd_vazias
                        else:
                            if 'Total' in row.index and pd.notnull(row['Total']): total = float(row['Total'])
                            else: total = float(row.get('Quantidade estoque ?', 0) or 0) + float(row.get('Em transito (Entrega)?', 0) or 0) + float(row.get('Em transito (carreta)?', 0) or 0)
                            if target_crate is None and target_bottle is not None: garrafa_cheia = total
                            elif target_bottle: garrafa_cheia = total * factor; caixa_cheia = total
                            else: caixa_cheia = total

                        return pd.Series([target_crate, target_bottle, garrafa_cheia, caixa_vazia, caixa_cheia], index=['TargetCrate', 'TargetBottle', 'GarrafaCheia', 'CaixaVazia', 'CaixaCheia'])

                    df_contagem[['TargetCrate', 'TargetBottle', 'GarrafaCheia', 'CaixaVazia', 'CaixaCheia']] = df_contagem.apply(calculate_assets, axis=1)

                    df_agg_garrafa = df_contagem.dropna(subset=['TargetBottle']).groupby(['TargetBottle', 'Dia']).agg(ContagemCheias=('GarrafaCheia', 'sum'), DataCompleta=('Carimbo de data/hora', 'max')).reset_index()
                    df_agg_garrafa['Contagem Vazias'] = 0 
                    df_agg_garrafa.rename(columns={'TargetBottle': 'Vasilhame', 'ContagemCheias': 'Contagem Cheias'}, inplace=True)

                    df_agg_caixa = df_contagem.dropna(subset=['TargetCrate']).groupby(['TargetCrate', 'Dia']).agg(ContagemCheias=('CaixaCheia', 'sum'), ContagemVazias=('CaixaVazia', 'sum'), DataCompleta=('Carimbo de data/hora', 'max')).reset_index()
                    df_agg_caixa.rename(columns={'TargetCrate': 'Vasilhame', 'ContagemCheias': 'Contagem Cheias', 'ContagemVazias': 'Contagem Vazias'}, inplace=True)
                    
                    df_excel_agg = pd.concat([df_agg_garrafa, df_agg_caixa], ignore_index=True)
                    df_excel_agg.rename(columns={'DataCompleta': 'DataCompleta_excel'}, inplace=True)

                    # PERSISTÊNCIA EXCEL
                    if not df_old_excel_data.empty:
                         if 'DataCompleta_excel' in df_old_excel_data.columns: df_old_excel_data['DataCompleta_excel'] = pd.to_datetime(df_old_excel_data['DataCompleta_excel'], errors='coerce')
                         df_excel_agg = pd.concat([df_old_excel_data, df_excel_agg]).drop_duplicates(subset=['Vasilhame', 'Dia'], keep='last').reset_index(drop=True)
                    df_excel_agg.to_sql('excel_data', con=engine, if_exists='replace', index=False)

                    required_vasilhames = list(FACTORS.keys()) + list(CRATE_TO_BOTTLE_MAP.values())
                    all_dates = set()
                    if not df_excel_agg.empty: all_dates.update(df_excel_agg['Dia'].unique())
                    if not df_all_processed_txt_data.empty: all_dates.update(df_all_processed_txt_data['Dia'].unique())
                    if not df_all_processed_pdf_data.empty: all_dates.update(df_all_processed_pdf_data['Dia'].unique())
                    if not all_dates: all_dates.add(datetime.now().strftime('%d/%m'))
                    
                    skeleton_rows = []
                    for prod in required_vasilhames:
                        for day in all_dates: skeleton_rows.append({'Vasilhame': prod, 'Dia': day})
                    df_skeleton = pd.DataFrame(skeleton_rows)

                    df_master_combinations = pd.concat([
                        df_excel_agg[['Vasilhame', 'Dia']], 
                        df_all_processed_txt_data[['Vasilhame', 'Dia']], 
                        df_all_processed_pdf_data[['Vasilhame', 'Dia']],
                        df_all_processed_vendas_data[['Vasilhame', 'Dia']],
                        df_skeleton
                    ]).drop_duplicates().reset_index(drop=True)
                    
                    df_final = pd.merge(df_master_combinations, df_excel_agg, on=['Vasilhame', 'Dia'], how='left')
                    df_final = pd.merge(df_final, df_all_processed_txt_data, on=['Vasilhame', 'Dia'], how='left')
                    df_final = pd.merge(df_final, df_all_processed_pdf_data, on=['Vasilhame', 'Dia'], how='left')
                    df_final = pd.merge(df_final, df_all_processed_vendas_data, on=['Vasilhame', 'Dia'], how='left')
                    
                    df_final['DataCompleta'] = df_final['DataCompleta_excel'].fillna(np.nan)
                    if 'DataCompleta_txt' in df_final.columns: df_final['DataCompleta'] = df_final['DataCompleta'].fillna(df_final['DataCompleta_txt'])
                    if 'DataCompleta_pdf' in df_final.columns: df_final['DataCompleta'] = df_final['DataCompleta'].fillna(df_final['DataCompleta_pdf'])
                    
                    def infer_date(row):
                        if pd.isna(row['DataCompleta']):
                            try: return datetime.strptime(f"{row['Dia']}/{datetime.now().year}", "%d/%m/%Y")
                            except: return pd.NaT
                        return row['DataCompleta']
                    df_final['DataCompleta'] = df_final.apply(infer_date, axis=1)

                    cols_to_drop = [col for col in df_final.columns if col.startswith('DataCompleta_')]
                    df_final.drop(cols_to_drop, axis=1, inplace=True)

                    numeric_cols = ['Contagem Cheias', 'Contagem Vazias', 'Qtd_emprestimo', 'Vendas'] + [col for col in df_final.columns if 'Credito' in col or 'Debito' in col]
                    for col in numeric_cols:
                        if col in df_final.columns: df_final[col] = pd.to_numeric(df_final[col], errors='coerce').fillna(0)
                    
                    if 'Vendas' not in df_final.columns: df_final['Vendas'] = 0

                    # SOMA FINAL (AGRUPAMENTO)
                    groupby_cols = ['Vasilhame', 'Dia', 'DataCompleta']
                    cols_to_sum = [c for c in numeric_cols if c in df_final.columns]
                    df_final = df_final.groupby(groupby_cols)[cols_to_sum].sum().reset_index()

                    df_final['Total Revenda'] = df_final['Qtd_emprestimo'] + df_final['Contagem Cheias'] + df_final['Contagem Vazias'] + df_final.filter(like='Credito').sum(axis=1) - df_final.filter(like='Debito').sum(axis=1) + df_final['Vendas']
                    
                    df_final['DataCompleta'] = pd.to_datetime(df_final['DataCompleta'], errors='coerce')
                    df_final.sort_values(by=['Vasilhame', 'DataCompleta'], inplace=True, na_position='first')
                    
                    def calcular_diferenca_regra_negocio(grupo):
                        data_base_travamento = pd.to_datetime('2025-11-05')
                        data_inicio_calculo = pd.to_datetime('2025-11-10')
                        mask_base = grupo['DataCompleta'] >= data_base_travamento
                        dados_base = grupo.loc[mask_base]
                        if not dados_base.empty: estoque_travado = dados_base.iloc[0]['Total Revenda']
                        else: estoque_travado = 0
                        diferencas = pd.Series(0.0, index=grupo.index)
                        mask_calculo = grupo['DataCompleta'] >= data_inicio_calculo
                        if estoque_travado != 0: diferencas[mask_calculo] = grupo.loc[mask_calculo, 'Total Revenda'] - estoque_travado
                        grupo['Diferença'] = diferencas
                        return grupo

                    df_final = df_final.groupby('Vasilhame', group_keys=False).apply(calcular_diferenca_regra_negocio)
                    df_final_output = df_final.drop('DataCompleta', axis=1)

                    # REORDENAÇÃO
                    output_cols = [c for c in df_final_output.columns if c not in ['Diferença', 'Vendas']]
                    df_final_output = df_final_output[output_cols + ['Diferença', 'Vendas']]
                    
                    st.subheader("✅ Tabela Consolidada de Vasilhames")
                    st.dataframe(df_final_output)
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        df_final_output.to_excel(writer, sheet_name='GERAL', index=False)
                        unique_products = df_final_output['Vasilhame'].unique()
                        
                        caixas_list = sorted([p for p in unique_products if 'CAIXA' in str(p).upper() or 'BARRIL' in str(p).upper() or 'CILINDRO' in str(p).upper()])
                        garrafas_list = sorted([p for p in unique_products if 'GARRAFA' in str(p).upper()])
                        outros_list = sorted([p for p in unique_products if p not in caixas_list and p not in garrafas_list])
                        
                        sorted_products = caixas_list + garrafas_list + outros_list

                        for product in sorted_products:
                            df_product = df_final_output[df_final_output['Vasilhame'] == product]
                            safe_sheet_name = str(product).replace('/', '-').replace('\\', '-').replace('?', '').replace('*', '').replace('[', '').replace(']', '').replace(':', '')[:31]
                            df_product.to_excel(writer, sheet_name=safe_sheet_name, index=False)
                            
                    output.seek(0)
                    st.download_button(label="📥 Baixar Tabela Consolidada", data=output, file_name="Vasilhames_Consolidado.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

                except Exception as e:
                    st.error(f"Ocorreu um erro durante o processamento: {e}")
                    import traceback
                    st.error(traceback.format_exc())

    elif script_choice == "Abastecimento":
        st.subheader("Análise de Abastecimento")
        uploaded_file = st.file_uploader("Envie o arquivo de abastecimento (.xlsx ou .csv)", type=["xlsx", "csv"], key="abastec_uploader") 
        if uploaded_file is not None:
            try:
                st.info("Processando...")
                try:
                    if uploaded_file.name.endswith('.csv'): df = pd.read_csv(uploaded_file)
                    elif uploaded_file.name.endswith('.xlsx'): df = pd.read_excel(uploaded_file)
                    else: st.error("Formato não suportado."); return
                except Exception as e: st.error(f"Erro ao ler arquivo: {e}"); return

                df.columns = [col.upper().strip().replace('HORA', 'HORÁRIO') for col in df.columns]
                column_mapping = {
                    'DATA ABASTECIMENTO': ['DATA', 'DATA ABASTECIMENTO', 'DATE', 'DATA_ABASTECIMENTO'],
                    'HORÁRIO': ['HORÁRIO', 'HORA', 'HORA DO ABASTECIMENTO'],
                    'TIPO DE ABASTECIMENTO': ['TIPO DE ABASTECIMENTO', 'TIPO_ABASTECIMENTO', 'COMBUSTÍVEL', 'TIPO'],
                    'PLACA': ['PLACA', 'PLACA_VEICULO'],
                    'KM': ['KM', 'QUILOMETRAGEM'],
                    'LITROS': ['LITROS', 'VOLUME'],
                    'MOTORISTA': ['MOTORISTA', 'RESPONSÁVEL'],
                }
                df_unified = pd.DataFrame()
                for new_name, possible_names in column_mapping.items():
                    for old_name in possible_names:
                        if old_name.upper() in df.columns: df_unified[new_name] = df[old_name.upper()]; break
                    else: st.warning(f"Coluna '{new_name}' não encontrada."); df_unified[new_name] = np.nan
                df = df_unified
                df['DATA ABASTECIMENTO'] = pd.to_datetime(df['DATA ABASTECIMENTO'], errors='coerce').dt.date
                df['HORÁRIO'] = pd.to_datetime(df['HORÁRIO'], format='%H:%M:%S', errors='coerce').dt.time
                df['KM'] = pd.to_numeric(df['KM'], errors='coerce')
                df['LITROS'] = pd.to_numeric(df['LITROS'], errors='coerce')
                df.dropna(subset=['DATA ABASTECIMENTO', 'KM', 'LITROS'], inplace=True)
                
                df_diesel = df[df['TIPO DE ABASTECIMENTO'].str.upper() == 'DIESEL'].copy()
                if not df_diesel.empty:
                    excel_data_diesel = io.BytesIO()
                    with pd.ExcelWriter(excel_data_diesel, engine='xlsxwriter') as writer:
                        placas_diesel = sorted(df_diesel['PLACA'].unique())
                        for placa in placas_diesel:
                            df_placa = df_diesel[df_diesel['PLACA'] == placa].copy()
                            df_placa.sort_values(by=['DATA ABASTECIMENTO', 'HORÁRIO'], ascending=True, inplace=True)
                            df_placa['DISTANCIA_PERCORRIDA'] = df_placa['KM'].diff()
                            df_placa['MEDIA_LITROS_KM'] = df_placa['LITROS'] / df_placa['DISTANCIA_PERCORRIDA']
                            df_placa['ALERTA KM'] = ''
                            df_placa.loc[df_placa['DISTANCIA_PERCORRIDA'] < 0, 'ALERTA KM'] = 'ALERTA: KM menor'
                            df_placa_output = df_placa.rename(columns={'DATA ABASTECIMENTO': 'Data Abastecimento', 'MEDIA_LITROS_KM': 'Média de litros por KM'})
                            df_placa_output.to_excel(writer, sheet_name=placa, index=False)
                    excel_data_diesel.seek(0)
                    st.success("Planilha de Diesel OK!")
                    st.download_button(label="📥 Baixar Diesel", data=excel_data_diesel, file_name="planilha_diesel.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                
                df_arla = df[df['TIPO DE ABASTECIMENTO'].str.upper() == 'ARLA'].copy()
                if not df_arla.empty:
                    excel_data_arla = io.BytesIO()
                    with pd.ExcelWriter(excel_data_arla, engine='xlsxwriter') as writer:
                        placas_arla = sorted(df_arla['PLACA'].unique())
                        for placa in placas_arla:
                            df_placa = df_arla[df_arla['PLACA'] == placa].copy()
                            df_placa.sort_values(by=['DATA ABASTECIMENTO', 'HORÁRIO'], ascending=True, inplace=True)
                            df_placa['DISTANCIA_PERCORRIDA'] = df_placa['KM'].diff()
                            df_placa['MEDIA_LITROS_KM'] = df_placa['LITROS'] / df_placa['DISTANCIA_PERCORRIDA']
                            df_placa['ALERTA KM'] = ''
                            df_placa.loc[df_placa['DISTANCIA_PERCORRIDA'] < 0, 'ALERTA KM'] = 'ALERTA: KM menor'
                            df_placa_output = df_placa.rename(columns={'DATA ABASTECIMENTO': 'Data Abastecimento', 'MEDIA_LITROS_KM': 'Média de litros por KM'})
                            df_placa_output.to_excel(writer, sheet_name=placa, index=False)
                    excel_data_arla.seek(0)
                    st.success("Planilha de Arla OK!")
                    st.download_button(label="📥 Baixar Arla", data=excel_data_arla, file_name="planilha_arla.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

            except Exception as e:
                st.error(f"Ocorreu um erro ao processar o arquivo: {e}")

    if st.button("Voltar para o Início", key="log_voltar"):
        st.session_state['current_page'] = 'home'
        st.rerun()

# ====================================================================
# SETOR COMERCIAL
# ====================================================================
def commercial_page():
    st.title("Setor Comercial")
    st.markdown("Bem-vindo(a) ao setor Comercial. Abaixo estão os scripts disponíveis para análise.")
    script_selection = st.selectbox("Selecione o script:", ("Selecione...", "Troca de Canal", "Circuito Execução"), key="com_select")

    if script_selection == "Troca de Canal":
        st.subheader("Troca de Canal")
        def transform_google_forms_data(df):
            processed_records = []
            if df.empty or len(df.columns) < 28: return pd.DataFrame()
            for index, row in df.iterrows():
                if not isinstance(row, pd.Series) or len(row) < 28: continue
                try:
                    data_value = row.iloc[0]; sv_value = row.iloc[1]
                    vd_consolidated_parts = [str(row.iloc[col_idx]).strip() for col_idx in range(2, min(5, len(row))) if pd.notna(row.iloc[col_idx])]
                    vd_final = ' | '.join(vd_consolidated_parts) if vd_consolidated_parts else None
                    para_value = row.iloc[27]
                    for col_idx in range(5, min(27, len(row))):
                        cell_content = str(row.iloc[col_idx]).strip()
                        if not cell_content or cell_content.lower() == 'nan': continue
                        de_category_match = re.search(r'\((.*?)\)', cell_content)
                        de_category_val = de_category_match.group(1).strip() if de_category_match else None
                        
                        # --- CORREÇÃO AQUI ---
                        # Antes: Removia tudo que fosse número no começo.
                        # Agora: Remove apenas o sufixo entre parenteses (ex: (MINI C/D)) e mantem o inicio (ex: 0020-0024)
                        pdv_info_raw = re.sub(r'\s*\([^)]*\)\s*$', '', cell_content).strip()
                        pdv_info_val = pdv_info_raw if pdv_info_raw else None
                        
                        if pdv_info_val or de_category_val:
                            processed_records.append({'DATA': data_value, 'SV': sv_value, 'VD': vd_final, 'PDV': pdv_info_val, 'DE': de_category_val, 'PARA': para_value, 'Status': ''})
                except IndexError: continue
            return pd.DataFrame(processed_records)
        uploaded_file_1 = st.file_uploader("Envie o arquivo (.xlsx)", type=["xlsx"], key="troca_canal_uploader") 
        if uploaded_file_1 is not None:
            try:
                df_forms = pd.read_excel(uploaded_file_1)
                st.dataframe(df_forms.head())
                final_df_forms = transform_google_forms_data(df_forms)
                if not final_df_forms.empty:
                    output = io.BytesIO(); final_df_forms.to_excel(output, index=False); output.seek(0)
                    workbook = load_workbook(output); sheet = workbook.active
                    dv = DataValidation(type="list", formula1='"Aprovado,Não Aprovado"', allow_blank=True)
                    try:
                        col_letter = get_column_letter(final_df_forms.columns.get_loc('Status') + 1)
                        dv.add(f'{col_letter}2:{col_letter}{sheet.max_row}'); sheet.add_data_validation(dv)
                    except KeyError: pass
                    output_with_dropdown = io.BytesIO(); workbook.save(output_with_dropdown); output_with_dropdown.seek(0)
                    st.dataframe(final_df_forms)
                    st.download_button(label="📥 Baixar Arquivo", data=output_with_dropdown.getvalue(), file_name="troca_canal_processada.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            except Exception as e: st.error(f"Erro: {e}")

    elif script_selection == "Circuito Execução":
        st.subheader("Circuito Execução")
        def extract_points(column_name): match = re.search(r"\(\s*(\d+)\s*Pontos\s*\)", column_name); return int(match.group(1)) if match else None
        def transform_points_columns(df):
            df_transformed = df.copy()
            for col in df_transformed.columns:
                if "Pontos" in col:
                    points = extract_points(col)
                    if points is not None: df_transformed[col] = df_transformed[col].apply(lambda x: points if x == "Presença" else 0)
            return df_transformed
        uploaded_file_2 = st.file_uploader("Envie o arquivo (.xlsx)", type=["xlsx"], key="circuito_exec_uploader") 
        if uploaded_file_2 is not None:
            try:
                df_points = pd.read_excel(uploaded_file_2); st.dataframe(df_points)
                df_transformed = transform_points_columns(df_points); st.dataframe(df_transformed)
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine="xlsxwriter") as writer: df_transformed.to_excel(writer, index=False)
                st.download_button(label="📥 Baixar Arquivo", data=output.getvalue(), file_name="circuito_execucao_transformado.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            except Exception as e: st.error(f"Erro: {e}")
                
    if st.button("Voltar para o Início", key="com_voltar"):
        st.session_state['current_page'] = 'home'
        st.rerun()

if 'is_logged_in' not in st.session_state: st.session_state['is_logged_in'] = False
if 'current_page' not in st.session_state: st.session_state['current_page'] = 'login'
if 'LOGIN_INFO' not in st.session_state: st.session_state['LOGIN_INFO'] = {"admin": "Joao789", "amanda": "12345", "marcia": "54321"}
st.set_page_config(page_title="Lince Distribuidora - Login", page_icon="🏠", layout="centered")
st.markdown("""<style>.stApp { background-color: #f0f2f6; } div.stButton > button:first-child { background-color: #007bff; color: white; border-radius: 5px; } .stTitle { text-align: center; color: #004d99; }</style>""", unsafe_allow_html=True)

if st.session_state.get('is_logged_in', False):
    page_functions = {'home': main_page, 'logistics': logistics_page, 'commercial': commercial_page}
    page_functions.get(st.session_state.get('current_page', 'home'), main_page)()
else: login_form()
