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
from sqlalchemy import create_engine
import os

# Funções que representam cada página
def login_form():
    """Exibe o formulário de login com um design aprimorado."""
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("<h2 style='text-align: center; color: #004d99; font-family: \'Arial Black\', sans-serif;'>Lince Distribuidora</h2>", unsafe_allow_html=True)
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
                st.success("Login realizado com sucesso! Redirecionando...")
                st.balloons()
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

    col3, col4 = st.columns(2)
    with col3:
        if st.button("RH", use_container_width=True):
            st.session_state['current_page'] = 'rh'
            st.rerun()
    # A opção "TI" foi removida daqui
    with col4: # Este col4 agora corresponderá ao botão Sítio
        if st.button("Sítio", use_container_width=True):
            st.session_state['current_page'] = 'site'
            st.rerun()
    
    st.markdown("---")

    if st.button("Sair", use_container_width=True):
        st.session_state['is_logged_in'] = False
        st.session_state.pop('username', None)
        st.session_state.pop('current_page', None)
        st.rerun()

# --- Novas funções para o banco de dados ---
def setup_database():
    """Cria a conexão com o banco de dados SQLite."""
    # O arquivo vasilhames.db será criado automaticamente
    engine = create_engine('sqlite:///vasilhames.db')
    return engine

def load_from_db(table_name, engine):
    """Carrega todos os dados de uma tabela do banco de dados."""
    if engine.dialect.has_table(engine.connect(), table_name):
        return pd.read_sql_table(table_name, con=engine)
    return pd.DataFrame()

def logistics_page():
    st.title("Setor de Logística")
    st.markdown("Bem-vindo(a) ao setor de Logística. Abaixo estão os scripts disponíveis para análise.")
    
    script_choice = st.selectbox(
        "Selecione um script para executar:",
        ("Selecione...", "Acurácia", "Validade", "Vasilhames", "Abastecimento")
    )
    
    st.write("---")

    if script_choice == "Acurácia":
        st.subheader("Acurácia de Estoque")
        st.markdown("Calcula a acurácia diária e mensal do estoque a partir de um arquivo Excel.")
        uploaded_file = st.file_uploader("Envie o arquivo 'Acuracia estoque.xlsx'", type=["xlsx"])
        if uploaded_file is not None:
            try:
                df = pd.read_excel(uploaded_file, header=[0, 1], sheet_name=0)
                products_to_remove = ['185039 - Garrafa 0,30l', '471 - Garrafa 0,60l (3 )']
                first_level_cols = [col[0] for col in df.columns]
                second_level_cols = [col[1] for col in df.columns]
                try:
                    prod_cod_col = [col for col in df.columns if col[1] == 'Prod Cód'][0]
                    df_data = df.set_index(prod_cod_col)
                except IndexError:
                    df_data = df.set_index(df.columns[0])
                df_data = df_data[~df_data.index.isin(products_to_remove)].copy()
                df_data = df_data[~df_data.index.astype(str).str.contains('Totais', na=False)].copy()
                data_types = ['Saldo Final', 'Contagem', 'Diferença', 'Acuracidade Estoque']
                unique_dates = sorted(list(set([col for col in first_level_cols if col not in ['Data', 'Prod Cód']])))
                new_rows = []
                for product in df_data.index:
                    for date in unique_dates:
                        row_data = {
                            'Prod Cód': product,
                            'Dia': date,
                        }
                        for data_type in data_types:
                            try:
                                col_name = (date, data_type)
                                value = df_data.loc[product, col_name]
                                if isinstance(value, str) and value == '-':
                                    value = 0
                                row_data[data_type] = pd.to_numeric(value, errors='coerce')
                            except KeyError:
                                row_data[data_type] = np.nan
                        new_rows.append(row_data)
                df_final = pd.DataFrame(new_rows)
                df_final['Saldo Final'] = df_final['Saldo Final'].apply(lambda x: max(0, x))
                df_final['Diferença'] = df_final['Diferença'].abs()
                daily_accuracy = df_final.groupby('Dia').apply(
                    lambda x: (x['Saldo Final'].sum() - x['Diferença'].sum()) / x['Saldo Final'].sum() if x['Saldo Final'].sum() != 0 else 0
                ).reset_index(name='Acurácia Diária')
                total_saldo_final_mes = df_final['Saldo Final'].sum()
                total_diferenca_mes = df_final['Diferença'].sum()
                monthly_accuracy = (total_saldo_final_mes - total_diferenca_mes) / total_saldo_final_mes if total_saldo_final_mes != 0 else 0
                df_final = pd.merge(df_final, daily_accuracy, on='Dia', how='left')
                df_final['Acurácia Mensal'] = monthly_accuracy
                df_final = df_final.sort_values(by=['Dia', 'Prod Cód'])
                df_final['Dia'] = pd.to_datetime(df_final['Dia']).dt.strftime('%Y-%m-%d')
                numeric_cols = ['Saldo Final', 'Contagem', 'Diferença', 'Acuracidade Estoque']
                df_final[numeric_cols] = df_final[numeric_cols].round(2)
                st.subheader("📊 Resultado da Acurácia")
                st.dataframe(df_final)
                excel_data = io.BytesIO()
                df_final.to_excel(excel_data, index=False, engine='xlsxwriter')
                excel_data.seek(0)
                st.download_button(
                    label="📥 Baixar Arquivo Processado",
                    data=excel_data,
                    file_name='Acuracia_estoque_processado.xlsx',
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"Ocorreu um erro no script de Acurácia: {e}")

    elif script_choice == "Validade":
        st.subheader("Controle de Validade")
        st.markdown("Consolida dados de validade de um arquivo Excel e um arquivo de texto, e gera um relatório com status de validade e contagens.")
        def parse_estoque_txt(file_content):
            lines = [line.decode('latin1') for line in file_content.getvalue().splitlines()]
            separator_string = '-' * 116
            separator_indices = [i for i, line in enumerate(lines) if separator_string in line]
            if len(separator_indices) < 2:
                st.warning("Não foi possível localizar os separadores de colunas no arquivo TXT.")
                return pd.DataFrame()
            start_line = separator_indices[1] + 1
            col_names = ['COD.RED.', 'DESCRIÇÃO', 'SLD INICIAL CX', 'SLD INICIAL UN', 'ENTRADAS CX', 'ENTRADAS UN', 'SAÍDAS CX', 'SAÍDAS UN', 'SALDO FÍSICO CX', 'SALDO FÍSICO UN', 'CONT. FÍSICA CX', 'CONT. FÍSICA UN', 'DIFERENÇA CX', 'DIFERENÇA UN']
            data = []
            pattern = re.compile(r'^\s*(\d+)\s+(.+?)\s*(\d*)\s*(\d*)\s*I\s*(\d*)\s*(\d*)\s*I\s*(\d*)\s*(\d*)\s*I\s*(\d*)\s*(\d*)\s*I\s*(\d*)\s*(\d*)\s*I\s*(\d*)\s*(\d*)\s*I')
            for line in lines[start_line:]:
                line = line.strip()
                if not line:
                    continue
                match = pattern.match(line)
                if match:
                    groups = match.groups()
                    row_values = [groups[0], groups[1]]
                    for i in range(2, len(groups), 2):
                        cx = groups[i].strip()
                        un = groups[i+1].strip()
                        row_values.extend([int(cx) if cx else 0, int(un) if un else 0])
                    if len(row_values) == 14:
                        data.append(row_values)
            df_txt_raw = pd.DataFrame(data, columns=col_names)
            return df_txt_raw
        uploaded_excel_file = st.file_uploader("Envie o arquivo Excel 'Controle de Validade.xlsx'", type=["xlsx"])
        uploaded_txt_file = st.file_uploader("Envie o arquivo de texto de estoque", type=["txt"])
        if uploaded_excel_file is not None and uploaded_txt_file is not None:
            try:
                df_validade = pd.read_excel(uploaded_excel_file)
                df_validade.columns = df_validade.columns.str.replace(r'\s+', ' ', regex=True).str.strip()
                df_estoque = parse_estoque_txt(uploaded_txt_file)
                if df_estoque.empty:
                    st.warning("O arquivo TXT está vazio ou não pôde ser processado.")
                validity_cols = ['Validade', 'Validade.1', 'Validade.2', 'Validade.3', 'Validade.4']
                quantity_caixa_cols = ['Quantidade (CAIXA)', 'Quantidade 2 (CAIXA)', 'Quantidade 3 (CAIXA)', 'Quantidade 4 (CAIXA)', 'Quantidade 5 (CAIXA)']
                quantity_unidade_cols = ['Quantidade (UNIDADE)', 'Quantidade 2 (UNIDADE)', 'Quantidade 3 (UNIDADE)', 'Quantidade 4 (UNIDADE)', 'Quantidade 5 (UNIDADE)']
                all_validity_entries = []
                for i in range(len(validity_cols)):
                    cols_to_check = ['Qual Produto ?', validity_cols[i], quantity_caixa_cols[i], quantity_unidade_cols[i]]
                    if all(col in df_validade.columns for col in cols_to_check):
                        temp_df = df_validade[['Qual Produto ?', validity_cols[i], quantity_caixa_cols[i], quantity_unidade_cols[i]]].copy()
                        temp_df.rename(columns={validity_cols[i]: 'Validade', quantity_caixa_cols[i]: 'Quantidade (CAIXA)', quantity_unidade_cols[i]: 'Quantidade (UNIDADE)'}, inplace=True)
                        all_validity_entries.append(temp_df)
                all_validity_entries = [df for df in all_validity_entries if not df.dropna(subset=['Validade']).empty]
                if all_validity_entries:
                    melted_df_validade_all = pd.concat(all_validity_entries, ignore_index=True)
                else:
                    melted_df_validade_all = pd.DataFrame(columns=['Qual Produto ?', 'Validade', 'Quantidade (CAIXA)', 'Quantidade (UNIDADE)'])
                melted_df_validade_all.dropna(subset=['Validade'], inplace=True)
                melted_df_validade_all['Validade'] = pd.to_datetime(melted_df_validade_all['Validade'], errors='coerce')
                melted_df_validade_all.dropna(subset=['Validade'], inplace=True)
                melted_df_validade_all['Quantidade (CAIXA)'] = pd.to_numeric(melted_df_validade_all['Quantidade (CAIXA)'], errors='coerce').fillna(0)
                melted_df_validade_all['Quantidade (UNIDADE)'] = pd.to_numeric(melted_df_validade_all['Quantidade (UNIDADE)'], errors='coerce').fillna(0)
                split_data_validade = melted_df_validade_all['Qual Produto ?'].astype(str).str.split(' - ', n=1, expand=True)
                melted_df_validade_all['Codigo Produto'] = split_data_validade[0].str.strip()
                melted_df_validade_all['Nome Produto'] = split_data_validade[1].str.strip()
                def extract_units_per_box(product_name):
                    product_name = str(product_name).upper().replace(' ', '')
                    match_multiplication = re.search(r'(\d+)X(\d+)(?:UN|U)', product_name)
                    if match_multiplication:
                        factor1 = int(match_multiplication.group(1))
                        factor2 = int(match_multiplication.group(2))
                        return factor1 * factor2
                    match_direct = re.search(r'(\d+)(?:UN|U)', product_name)
                    if match_direct:
                        return int(match_direct.group(1))
                    return 1
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
                st.download_button(
                    label="📥 Baixar Relatório de Validade",
                    data=excel_data,
                    file_name="Controle_Estoque_Completo.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"Ocorreu um erro ao processar os arquivos: {e}")

    elif script_choice == "Vasilhames":
        st.subheader("Controle de Vasilhames")
        st.markdown("Este script consolida dados de vasilhames de diferentes fontes (Excel, TXT, PDF) e gera um relatório unificado.")
        
        # Cria a conexão com o banco de dados
        engine = setup_database()

        def process_txt_file_st(file_content):
            content = file_content.getvalue().decode('latin1')
            filename_date_match = re.search(r'ESTOQUE(\d{4})\.TXT', file_content.name)
            if filename_date_match:
                day = filename_date_match.group(1)[:2]
                month = filename_date_match.group(1)[2:]
                year = datetime.now().year
                effective_date_str = datetime.strptime(f"{day}/{month}/{year}", '%d/%m/%Y').strftime('%d/%m')
            else:
                st.error("Nome do arquivo TXT inválido. O formato deve ser 'ESTOQUEDDMM.TXT'.")
                return None, None
            product_code_to_vasilhame_map = {'563-008': '563-008 - BARRIL INOX 30L', '564-009': '564-009 - BARRIL INOX 50L', '591-002': '591-002 - CAIXA PLASTICA HEINEKEN 330ML', '587-002': '587-002 - CAIXA PLASTICA HEINEKEN 600ML', '550-001': '550-001 - CAIXA PLASTICA 600ML', '555-001': '555-001 - CAIXA PLASTICA 1L', '546-004': '546-004 - CAIXA PLASTICA 24UN 300ML', '565-002': '565-002 - CILINDRO CO2', '550-012': '550-001 - CAIXA PLASTICA 600ML', '803-039': '550-001 - CAIXA PLASTICA 600ML', '803-037': '550-001 - CAIXA PLASTICA 600ML'}
            parsed_data = []
            pattern = re.compile(r'^\s*"?(\d{3}-\d{3})[^"\n]*?"?.*?"?([\d.]+)"?\s*$', re.MULTILINE)
            for line in content.splitlines():
                match = pattern.match(line)
                if match:
                    product_code = match.group(1).strip()
                    quantity = match.group(2).replace('.', '').strip()
                    if product_code in product_code_to_vasilhame_map:
                        parsed_data.append({'PRODUTO_CODE': product_code, 'QUANTIDADE': int(quantity) if quantity.isdigit() else 0})
            if not parsed_data:
                return None, effective_date_str
            df_estoque = pd.DataFrame(parsed_data)
            df_estoque['Vasilhame'] = df_estoque['PRODUTO_CODE'].map(product_code_to_vasilhame_map)
            df_txt_qty = df_estoque.groupby('Vasilhame')['QUANTIDADE'].sum().reset_index()
            df_txt_qty.rename(columns={'QUANTIDADE': 'Qtd. emprestimo'}, inplace=True)
            return df_txt_qty, effective_date_str

        def process_pdf_content(pdf_file, product_map):
            parsed_data = []
            filename_match = re.search(r'([a-zA-Z\s]+)\s+(\d{2}-\d{2}-\d{4})\.pdf', pdf_file.name)
            if not filename_match:
                st.error(f"Erro: Nome de arquivo PDF inválido: {pdf_file.name}. Formato esperado: 'PDV DD-MM-YYYY.pdf'")
                return pd.DataFrame()
            source_name = filename_match.group(1).strip()
            date_str = filename_match.group(2)
            effective_date_str = datetime.strptime(date_str, '%d-%m-%Y').strftime('%d/%m')
            source_to_col_map = {'PONTA GROSSA': 'Ponta Grossa (0328)', 'ARARAQUARA': 'Araraquara (0336)', 'ITU': 'Itu (0002)'}
            col_suffix = source_to_col_map.get(source_name.upper(), source_name)
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_file.getvalue()))
            pdf_content = ""
            for page in pdf_reader.pages:
                pdf_content += page.extract_text()
            data_line_pattern = re.compile(r'^\s*"?(\d{15,})[^"\n]*?"?.*?"?([-+]?[\d.,]+)"?\s*$', re.MULTILINE)
            for line_match in data_line_pattern.finditer(pdf_content):
                material_code = line_match.group(1).strip()
                saldo_str = line_match.group(2).replace('.', '').replace(',', '.').strip()
                try:
                    saldo = float(saldo_str)
                except ValueError:
                    saldo = 0.0
                if material_code in product_map:
                    vasilhame = product_map[material_code]
                    credito = abs(saldo) if saldo < 0 else 0.0
                    debito = saldo if saldo >= 0 else 0.0
                    parsed_data.append({'Vasilhame': vasilhame, 'Dia': effective_date_str, f'Credito {col_suffix}': credito, f'Debito {col_suffix}': debito})
            if not parsed_data:
                st.warning(f"Nenhum dado de PDV encontrado no arquivo: {pdf_file.name}")
                return pd.DataFrame()
            return pd.DataFrame(parsed_data).groupby(['Vasilhame', 'Dia'], as_index=False).sum()
        
        uploaded_txt_files = st.file_uploader("Envie os arquivos TXT de empréstimos (Ex: ESTOQUE0102.TXT)", type=["txt"], accept_multiple_files=True)
        uploaded_excel_contagem = st.file_uploader("Envie o arquivo Excel de contagem (Ex: Contagem Vasilhames.xlsx)", type=["xlsx"])
        uploaded_pdf_files = st.file_uploader("Envie os arquivos PDF de fábrica", type=["pdf"], accept_multiple_files=True)
        
        if st.button("Processar e Consolidar Dados"):
            if uploaded_txt_files and uploaded_excel_contagem is not None:
                try:
                    st.info("Processando e salvando novos dados. Por favor, aguarde...")
                    
                    # --- Processamento e Salvamento dos novos arquivos ---
                    new_txt_data = []
                    for uploaded_txt_file in uploaded_txt_files:
                        df_txt_qty, effective_date_str = process_txt_file_st(uploaded_txt_file)
                        if df_txt_qty is not None:
                            df_txt_qty['Dia'] = effective_date_str
                            new_txt_data.append(df_txt_qty)
                    
                    if new_txt_data:
                        df_new_txt = pd.concat(new_txt_data, ignore_index=True)
                        df_new_txt.to_sql('txt_data', con=engine, if_exists='append', index=False)
                        st.success("Novos dados TXT salvos no banco de dados!")
                    else:
                        st.warning("Nenhum dado TXT para salvar.")

                    new_pdf_data = []
                    if uploaded_pdf_files:
                        pdf_material_code_to_vasilhame_map = {
                            '000000000000215442': '587-002 - CAIXA PLASTICA HEINEKEN 600ML', '000000000000215208': '587-002 - CAIXA PLASTICA HEINEKEN 600ML', '000000000000381411': '591-002 - CAIXA PLASTICA HEINEKEN 330ML', '000000000000107380': '555-001 - CAIXA PLASTICA 1L', '000000000000152598': '546-004 - CAIXA PLASTICA 24UN 300ML', '000000000000000470': '550-001 - CAIXA PLASTICA 600ML'
                        }
                        for pdf_file in uploaded_pdf_files:
                            df_pdf_current = process_pdf_content(pdf_file, pdf_material_code_to_vasilhame_map)
                            if not df_pdf_current.empty:
                                new_pdf_data.append(df_pdf_current)
                    
                    if new_pdf_data:
                        df_new_pdf = pd.concat(new_pdf_data, ignore_index=True)
                        df_new_pdf.to_sql('pdf_data', con=engine, if_exists='append', index=False)
                        st.success("Novos dados PDF salvos no banco de dados!")
                    else:
                        st.warning("Nenhum dado PDF para salvar.")

                    # --- Carregamento dos dados históricos (do banco) ---
                    df_all_processed_txt_data = load_from_db('txt_data', engine)
                    df_all_processed_pdf_data = load_from_db('pdf_data', engine)
                    
                    if df_all_processed_txt_data.empty and df_all_processed_pdf_data.empty:
                        st.warning("Nenhum dado TXT ou PDF encontrado no banco de dados.")
                        return

                    # --- O restante do seu código de consolidação ---
                    df_contagem = pd.read_excel(uploaded_excel_contagem, sheet_name='Respostas ao formulário 1')
                    df_contagem['Carimbo de data/hora'] = pd.to_datetime(df_contagem['Carimbo de data/hora'])
                    df_historical_excel = df_contagem.copy()
                    df_historical_excel['Dia'] = df_historical_excel['Carimbo de data/hora'].dt.strftime('%d/%m')
                    df_excel_daily_counts = df_historical_excel.groupby(['Qual vasilhame ?', 'Dia'])['Total'].sum().reset_index()
                    df_excel_daily_counts.rename(columns={'Qual vasilhame ?': 'Vasilhame', 'Total': 'Contagem'}, inplace=True)
                    
                    df_master_combinations = pd.concat([
                        df_excel_daily_counts[['Vasilhame', 'Dia']],
                        df_all_processed_txt_data[['Vasilhame', 'Dia']] if 'Vasilhame' in df_all_processed_txt_data.columns else pd.DataFrame(columns=['Vasilhame', 'Dia']),
                        df_all_processed_pdf_data[['Vasilhame', 'Dia']] if 'Vasilhame' in df_all_processed_pdf_data.columns else pd.DataFrame(columns=['Vasilhame', 'Dia'])
                    ]).drop_duplicates().reset_index(drop=True)

                    df_final = pd.merge(df_master_combinations, df_excel_daily_counts, on=['Vasilhame', 'Dia'], how='left')
                    df_final = pd.merge(df_final, df_all_processed_txt_data, on=['Vasilhame', 'Dia'], how='left')
                    df_final = pd.merge(df_final, df_all_processed_pdf_data, on=['Vasilhame', 'Dia'], how='left')
                    
                    df_final['Contagem'] = pd.to_numeric(df_final['Contagem'], errors='coerce').fillna(0)
                    df_final['Qtd. emprestimo'] = pd.to_numeric(df_final['Qtd. emprestimo'], errors='coerce').fillna(0)
                    
                    df_final['Total Revenda'] = df_final['Qtd. emprestimo'] + df_final['Contagem'] + df_final.filter(like='Credito').sum(axis=1) - df_final.filter(like='Debito').sum(axis=1)
                    df_final['Diferença'] = df_final.groupby('Vasilhame')['Total Revenda'].diff()
                    
                    st.subheader("✅ Tabela Consolidada de Vasilhames")
                    st.dataframe(df_final)

                    output = io.BytesIO()
                    df_final.to_excel(output, index=False)
                    output.seek(0)
                    st.download_button(
                        label="📥 Baixar Tabela Consolidada",
                        data=output,
                        file_name="Vasilhames_Consolidado.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

                except Exception as e:
                    st.error(f"Ocorreu um erro durante o processamento: {e}")
    
    elif script_choice == "Abastecimento":
        st.subheader("Análise de Abastecimento")
        st.markdown("Este script processa dados de abastecimento e gera relatórios separados para Diesel e Arla, com médias de consumo por KM.")
        
        uploaded_file = st.file_uploader("Envie o arquivo de abastecimento (.xlsx ou .csv)", type=["xlsx", "csv"])
        
        if uploaded_file is not None:
            try:
                st.info("Processando arquivo de abastecimento. Isso pode levar alguns segundos...")
                
                # Tenta carregar o arquivo como Excel
                try:
                    df = pd.read_excel(uploaded_file, engine='openpyxl')
                except Exception as e:
                    # Se falhar, tenta carregar como CSV
                    st.warning(f"Erro ao carregar como Excel: {e}. Tentando como CSV...")
                    uploaded_file.seek(0) # Volta ao início do arquivo para a nova tentativa de leitura
                    df = pd.read_csv(uploaded_file)
                
                # Normalização de colunas
                df.columns = [col.upper().strip().replace('HORA', 'HORÁRIO') for col in df.columns]
                
                # Garante que as colunas de data e hora estão no formato correto
                if 'DATA ABASTECIMENTO' not in df.columns and 'DATA' in df.columns:
                    df['DATA ABASTECIMENTO'] = pd.to_datetime(df['DATA'], errors='coerce')
                else:
                    df['DATA ABASTECIMENTO'] = pd.to_datetime(df['DATA ABASTECIMENTO'], errors='coerce')
                
                if 'HORÁRIO' in df.columns:
                    df['HORÁRIO'] = pd.to_datetime(df['HORÁRIO'], format='%H:%M:%S', errors='coerce').dt.time
                
                if 'MOTORISTA' not in df.columns and 'RESPONSÁVEL' in df.columns:
                    df['MOTORISTA'] = df['RESPONSÁVEL']

                df['KM'] = pd.to_numeric(df['KM'], errors='coerce')
                df['LITROS'] = pd.to_numeric(df['LITROS'], errors='coerce')

                # Define as colunas de saída
                colunas_saida = [
                    'DATA ABASTECIMENTO', 'HORÁRIO', 'TIPO DE ABASTECIMENTO', 
                    'PLACA', 'KM', 'ALERTA KM', 'MOTORISTA', 'LITROS', 'Média de litros por KM'
                ]
                
                df_diesel = df[df['TIPO DE ABASTECIMENTO'] == 'DIESEL'].copy()
                if not df_diesel.empty:
                    excel_data_diesel = io.BytesIO()
                    with pd.ExcelWriter(excel_data_diesel, engine='openpyxl') as writer:
                        placas_diesel = sorted(df_diesel['PLACA'].unique())
                        for placa in placas_diesel:
                            df_placa = df_diesel[df_diesel['PLACA'] == placa].copy()
                            
                            df_placa.sort_values(by=['DATA ABASTECIMENTO', 'HORÁRIO'], ascending=True, inplace=True)
                            
                            df_placa['DISTANCIA_PERCORRIDA'] = df_placa['KM'].diff()
                            df_placa['MEDIA_LITROS_KM'] = df_placa['LITROS'] / df_placa['DISTANCIA_PERCORRIDA']
                            
                            df_placa['ALERTA KM'] = ''
                            df_placa.loc[df_placa['DISTANCIA_PERCORRIDA'] < 0, 'ALERTA KM'] = 'ALERTA: KM menor que o registro anterior!'

                            df_placa['Média de litros por KM'] = df_placa['MEDIA_LITROS_KM'].mean()
                            df_placa.loc[df_placa.index[:-1], 'Média de litros por KM'] = ''
                            
                            df_placa_output = df_placa.rename(columns={'DATA ABASTECIMENTO': 'Data Abastecimento', 'TIPO DE ABASTECIMENTO': 'Tipo de Abastecimento'})
                            
                            df_placa_output[colunas_saida].to_excel(writer, sheet_name=placa, index=False)
                    
                    excel_data_diesel.seek(0)
                    st.success("Planilha de Diesel processada com sucesso!")
                    st.download_button(
                        label="📥 Baixar Planilha de Diesel",
                        data=excel_data_diesel,
                        file_name="planilha_diesel.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.warning("Não foram encontrados dados de 'DIESEL' no arquivo.")
                    
                df_arla = df[df['TIPO DE ABASTECIMENTO'] == 'ARLA'].copy()
                if not df_arla.empty:
                    excel_data_arla = io.BytesIO()
                    with pd.ExcelWriter(excel_data_arla, engine='openpyxl') as writer:
                        placas_arla = sorted(df_arla['PLACA'].unique())
                        for placa in placas_arla:
                            df_placa = df_arla[df_arla['PLACA'] == placa].copy()
                            
                            df_placa.sort_values(by=['DATA ABASTECIMENTO', 'HORÁRIO'], ascending=True, inplace=True)
                            
                            df_placa['DISTANCIA_PERCORRIDA'] = df_placa['KM'].diff()
                            df_placa['MEDIA_LITROS_KM'] = df_placa['LITROS'] / df_placa['DISTANCIA_PERCORRIDA']
                            
                            df_placa['ALERTA KM'] = ''
                            df_placa.loc[df_placa['DISTANCIA_PERCORRIDA'] < 0, 'ALERTA KM'] = 'ALERTA: KM menor que o registro anterior!'
                            
                            df_placa['Média de litros por KM'] = df_placa['MEDIA_LITROS_KM'].mean()
                            df_placa.loc[df_placa.index[:-1], 'Média de litros por KM'] = ''
                            
                            df_placa_output = df_placa.rename(columns={'DATA ABASTECIMENTO': 'Data Abastecimento', 'TIPO DE ABASTECIMENTO': 'Tipo de Abastecimento'})
                            
                            df_placa_output[colunas_saida].to_excel(writer, sheet_name=placa, index=False)
                            
                    excel_data_arla.seek(0)
                    st.success("Planilha de Arla processada com sucesso!")
                    st.download_button(
                        label="📥 Baixar Planilha de Arla",
                        data=excel_data_arla,
                        file_name="planilha_arla.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.warning("Não foram encontrados dados de 'ARLA' no arquivo.")

            except Exception as e:
                st.error(f"Ocorreu um erro ao processar o arquivo: {e}")

    if st.button("Voltar para o Início"):
        st.session_state['current_page'] = 'home'
        st.rerun()

def commercial_page():
    st.title("Setor Comercial")
    st.markdown("Bem-vindo(a) ao setor Comercial. Abaixo estão os scripts disponíveis para análise.")

    script_selection = st.selectbox(
        "Selecione o script que deseja executar:",
        ("Selecione...", "Troca de Canal", "Circuito Execução")
    )

    if script_selection == "Troca de Canal":
        st.write("---")
        st.subheader("Troca de Canal")
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
            """
            Transforma dados de Google Forms, consolidando informações e adicionando
            uma coluna 'Status' com validação de dados.
            """
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
            return final_df

        uploaded_file_1 = st.file_uploader("Envie o arquivo para 'Troca de Canal' (.xlsx)", type=["xlsx"])

        if uploaded_file_1 is not None:
            try:
                df_forms = pd.read_excel(uploaded_file_1)
                st.subheader("📄 Dados Originais (Troca de Canal)")
                st.dataframe(df_forms.head())
                
                final_df_forms = transform_google_forms_data(df_forms)
                
                output = io.BytesIO()
                final_df_forms.to_excel(output, index=False)
                output.seek(0)
                
                workbook = load_workbook(output)
                sheet = workbook.active
                
                dropdown_options_excel = '"Aprovado,Não Aprovado"'
                dv = DataValidation(type="list", formula1=dropdown_options_excel, allow_blank=True)
                dv.error = 'O valor inserido não está na lista.'
                dv.errorTitle = 'Valor Inválido'
                
                try:
                    col_for_dropdown_letter = get_column_letter(final_df_forms.columns.get_loc('Status') + 1)
                    dv.add(f'{col_for_dropdown_letter}2:{col_for_dropdown_letter}{sheet.max_row}')
                    sheet.add_data_validation(dv)
                except KeyError:
                    st.warning("A coluna 'Status' não foi encontrada no DataFrame final.")
                
                output_with_dropdown = io.BytesIO()
                workbook.save(output_with_dropdown)
                output_with_dropdown.seek(0)
                
                st.subheader("✅ Dados Transformados (Troca de Canal)")
                st.dataframe(final_df_forms)
                
                st.download_button(
                    label="📥 Baixar Arquivo de Troca de Canal",
                    data=output_with_dropdown.getvalue(),
                    file_name="troca_canal_processada.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
            except Exception as e:
                st.error(f"Ocorreu um erro durante o processamento de 'Troca de Canal': {e}")

    elif script_selection == "Circuito Execução":
        st.write("---")
        st.subheader("Circuito Execução")
        st.markdown("Este script converte os valores 'Presença' em pontuação, com base no nome das colunas.")

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
                        df_transformed[col] = df_transformed[col].apply(lambda x: points if x == "Presença" else 0)
            return df_transformed

        @st.cache_data
        def convert_df_to_excel(df):
            """Converte DataFrame para um arquivo Excel em memória."""
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                df.to_excel(writer, index=False)
            processed_data = output.getvalue()
            return processed_data

        uploaded_file_2 = st.file_uploader("Envie o arquivo para 'Circuito Execução' (.xlsx)", type=["xlsx"])

        if uploaded_file_2 is not None:
            try:
                df_points = pd.read_excel(uploaded_file_2)
                st.subheader("📄 Dados Originais (Circuito Execução)")
                st.dataframe(df_points)
                
                df_transformed_points = transform_points_columns(df_points)
                
                st.subheader("✅ Dados Transformados (Circuito Execução)")
                st.dataframe(df_transformed_points)
                
                excel_data = convert_df_to_excel(df_transformed_points)
                
                st.download_button(
                    label="📥 Baixar Arquivo de Circuito Execução Transformado",
                    data=excel_data,
                    file_name="circuito_execucao_transformado.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
            except Exception as e:
                st.error(f"Ocorreu um erro durante o processamento de 'Circuito Execução': {e}")
    if st.button("Voltar para o Início"):
        st.session_state['current_page'] = 'home'
        st.rerun()

def rh_page():
    st.title("Setor de RH")
    st.markdown("Bem-vindo(a) ao setor de RH. Abaixo estão os scripts disponíveis para análise.")

    script_choice = st.selectbox(
        "Selecione um script para executar:",
        ("Selecione...", "Controle de Jornada")
    )

    st.write("---")

    if script_choice == "Controle de Jornada":
        st.subheader("Controle de Jornada")
        st.markdown("Este script processa uma planilha de controle de jornada e calcula tempos de viagem, dirigibilidade e paradas.")

        def format_timedelta_as_hms(td):
            if pd.isna(td):
                return pd.NaT
            total_seconds = td.total_seconds()
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

        def format_timedelta_as_dias_hms(td):
            if pd.isna(td):
                return pd.NaT
            total_seconds = td.total_seconds()
            days, remainder = divmod(total_seconds, 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, seconds = divmod(remainder, 60)
            if days > 0:
                return f"{int(days)} dias {int(hours):02}:{int(minutes):02}:{int(seconds):02}"
            else:
                return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

        uploaded_file = st.file_uploader("Envie o arquivo 'Controle de Jornada.xlsx'", type=["xlsx"])

        if uploaded_file is not None:
            try:
                df = pd.read_excel(uploaded_file)
                st.subheader("📄 Dados Originais")
                st.dataframe(df.head())
                
                all_events = []
                for index, row in df.iterrows():
                    motorista = row.get('Motorista')
                    timestamp_str = row.get('Carimbo de data/hora')
                    if pd.isna(timestamp_str) or pd.isna(motorista):
                        continue
                    timestamp = pd.to_datetime(timestamp_str)
                    entry_type = row.get('Qual o tipo de lançamento?')
                    if entry_type == 'Inicio Jornada':
                        date_str = row.get('Dia')
                        time_str = row.get('Horário')
                        if pd.notna(date_str) and pd.notna(time_str):
                            start_time = pd.to_datetime(f"{date_str} {time_str}")
                            all_events.append({'Motorista': motorista, 'Tipo de Lançamento': entry_type, 'Inicio': start_time, 'Fim': None, 'Motivo': None, 'Carimbo de data/hora': timestamp})
                    elif entry_type == 'Inicio de Viagem':
                        date_str = row.get('Dia.1')
                        time_str = row.get('Horário.1')
                        if pd.notna(date_str) and pd.notna(time_str):
                            start_time = pd.to_datetime(f"{date_str} {time_str}")
                            all_events.append({'Motorista': motorista, 'Tipo de Lançamento': entry_type, 'Inicio': start_time, 'Fim': None, 'Motivo': None, 'Carimbo de data/hora': timestamp})
                    elif entry_type == 'Fim da Viagem':
                        time_str = row.get('Fim.5')
                        if pd.notna(time_str):
                            time_str = str(time_str).split(' ')[-1]
                            end_time = pd.to_datetime(f"{timestamp.strftime('%Y-%m-%d')} {time_str}")
                            all_events.append({'Motorista': motorista, 'Tipo de Lançamento': entry_type, 'Inicio': None, 'Fim': end_time, 'Motivo': None, 'Carimbo de data/hora': timestamp})
                    elif entry_type == 'Fim de Jornada':
                        date_str = row.get('Dia.2')
                        time_str = row.get('Horário.3')
                        if pd.notna(date_str) and pd.notna(time_str):
                            end_time = pd.to_datetime(f"{date_str} {time_str}")
                            all_events.append({'Motorista': motorista, 'Tipo de Lançamento': entry_type, 'Inicio': None, 'Fim': end_time, 'Motivo': None, 'Carimbo de data/hora': timestamp})
                    parada_cols_map = {
                        '1': {'inicio': 'Inicio ', 'fim': 'Fim', 'motivo': 'Motivo'},
                        '2': {'inicio': 'Inicio', 'fim': 'Fim.1', 'motivo': 'Motivo.1'},
                        '3': {'inicio': 'Inicio.1', 'fim': 'Fim.2', 'motivo': 'Motivo.2'},
                        '4': {'inicio': 'Inicio.2', 'fim': 'Fim.3', 'motivo': 'Motivo.3'},
                        '5': {'inicio': 'Inicio.3', 'fim': 'Fim.4', 'motivo': 'Motivo.4'}
                    }
                    for i in range(1, 6):
                        cols = parada_cols_map.get(str(i))
                        start_time_str = row.get(cols['inicio'])
                        end_time_str = row.get(cols['fim'])
                        motivo = row.get(cols['motivo'])
                        if pd.notna(start_time_str) and pd.notna(end_time_str) and pd.notna(motivo):
                            date_str = timestamp.strftime('%Y-%m-%d')
                            try:
                                start_time_str = str(start_time_str).split(' ')[-1]
                                end_time_str = str(end_time_str).split(' ')[-1]
                                start_time = pd.to_datetime(f"{date_str} {start_time_str}")
                                end_time = pd.to_datetime(f"{date_str} {end_time_str}")
                                all_events.append({'Motorista': motorista, 'Tipo de Lançamento': f'Parada {i}', 'Inicio': start_time, 'Fim': end_time, 'Motivo': motivo, 'Carimbo de data/hora': timestamp})
                            except ValueError:
                                st.error(f"Erro ao converter data/hora na linha {index} para 'Parada {i}'.")
                                continue
                consolidated_df = pd.DataFrame(all_events)
                consolidated_df.dropna(subset=['Motorista', 'Tipo de Lançamento'], how='all', inplace=True)
                consolidated_df.sort_values(by=['Motorista', 'Carimbo de data/hora'], inplace=True)
                consolidated_df.reset_index(drop=True, inplace=True)
                consolidated_df['Tempo Total de Jornada'] = pd.NaT
                consolidated_df['Tempo Total de Viagem'] = pd.NaT
                consolidated_df['Tempo de Dirigibilidade'] = pd.NaT
                consolidated_df['Tempo Almoço'] = pd.NaT
                consolidated_df['Tempo Carga/Descarga'] = pd.NaT
                consolidated_df['Tempo Liberação N.F.'] = pd.NaT
                consolidated_df['Tempo Repouso'] = pd.NaT
                for (motorista, dia), group in consolidated_df.groupby(['Motorista', consolidated_df['Carimbo de data/hora'].dt.date]):
                    inicio_jornada = group[group['Tipo de Lançamento'] == 'Inicio Jornada']['Inicio'].min()
                    fim_jornada = group[group['Tipo de Lançamento'] == 'Fim de Jornada']['Fim'].max()
                    tempo_jornada = fim_jornada - inicio_jornada if pd.notnull(inicio_jornada) and pd.notnull(fim_jornada) else timedelta(seconds=0)
                    inicio_viagem = group[group['Tipo de Lançamento'] == 'Inicio de Viagem']['Inicio'].min()
                    fim_viagem = group[group['Tipo de Lançamento'] == 'Fim da Viagem']['Fim'].max()
                    tempo_viagem = fim_viagem - inicio_viagem if pd.notnull(inicio_viagem) and pd.notnull(fim_viagem) else timedelta(seconds=0)
                    break_durations = group.dropna(subset=['Motivo']).copy()
                    if not break_durations.empty:
                        break_durations['Duration'] = break_durations['Fim'] - break_durations['Inicio']
                    else:
                        break_durations['Duration'] = timedelta(seconds=0)
                    almoco_duration = break_durations[break_durations['Motivo'] == 'Almoço']['Duration'].sum()
                    carga_descarga_duration = break_durations[break_durations['Motivo'] == 'Carga/Descarga']['Duration'].sum()
                    liberacao_nf_duration = break_durations[break_durations['Motivo'] == 'Liberação de N.F']['Duration'].sum()
                    repouso_duration = break_durations[break_durations['Motivo'] == 'Repouso']['Duration'].sum()
                    total_stop_time = almoco_duration + carga_descarga_duration + liberacao_nf_duration + repouso_duration
                    tempo_dirigibilidade = tempo_viagem - total_stop_time
                    consolidated_df.loc[group[group['Tipo de Lançamento'] == 'Fim de Jornada'].index, 'Tempo Total de Jornada'] = tempo_jornada
                    consolidated_df.loc[group[group['Tipo de Lançamento'] == 'Fim da Viagem'].index, 'Tempo Total de Viagem'] = tempo_viagem
                    consolidated_df.loc[group[group['Tipo de Lançamento'] == 'Fim da Viagem'].index, 'Tempo de Dirigibilidade'] = tempo_dirigibilidade
                    consolidated_df.loc[group[group['Motivo'] == 'Almoço'].index, 'Tempo Almoço'] = almoco_duration
                    consolidated_df.loc[group[group['Motivo'] == 'Carga/Descarga'].index, 'Tempo Carga/Descarga'] = carga_descarga_duration
                    consolidated_df.loc[group[group['Motivo'] == 'Liberação de N.F'].index, 'Tempo Liberação N.F.'] = liberacao_nf_duration
                    consolidated_df.loc[group[group['Motivo'] == 'Repouso'].index, 'Tempo Repouso'] = repouso_duration
                consolidated_df['Tempo Total de Jornada'] = consolidated_df['Tempo Total de Jornada'].apply(format_timedelta_as_dias_hms)
                consolidated_df['Tempo Total de Viagem'] = consolidated_df['Tempo Total de Viagem'].apply(format_timedelta_as_dias_hms)
                consolidated_df['Tempo de Dirigibilidade'] = consolidated_df['Tempo de Dirigibilidade'].apply(format_timedelta_as_hms)
                consolidated_df['Tempo Almoço'] = consolidated_df['Tempo Almoço'].apply(format_timedelta_as_hms)
                consolidated_df['Tempo Carga/Descarga'] = consolidated_df['Tempo Carga/Descarga'].apply(format_timedelta_as_hms)
                consolidated_df['Tempo Liberação N.F.'] = consolidated_df['Tempo Liberação N.F.'].apply(format_timedelta_as_hms)
                consolidated_df['Tempo Repouso'] = consolidated_df['Tempo Repouso'].apply(format_timedelta_as_hms)
                consolidated_df.drop(columns=['Carimbo de data/hora'], inplace=True)
                
                st.subheader("✅ Dados Processados")
                st.dataframe(consolidated_df)
                
                excel_data = io.BytesIO()
                consolidated_df.to_excel(excel_data, sheet_name="Dados Consolidados", index=False)
                excel_data.seek(0)
                
                st.download_button(
                    label="📥 Baixar Arquivo Processado",
                    data=excel_data,
                    file_name="Jornada_Calculo.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"Ocorreu um erro ao processar o arquivo: {e}")

    if st.button("Voltar para o Início"):
        st.session_state['current_page'] = 'home'
        st.rerun()

def commercial_page():
    st.title("Setor Comercial")
    st.markdown("Bem-vindo(a) ao setor Comercial. Abaixo estão os scripts disponíveis para análise.")

    script_selection = st.selectbox(
        "Selecione o script que deseja executar:",
        ("Selecione...", "Troca de Canal", "Circuito Execução")
    )

    if script_selection == "Troca de Canal":
        st.write("---")
        st.subheader("Troca de Canal")
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
            """
            Transforma dados de Google Forms, consolidando informações e adicionando
            uma coluna 'Status' com validação de dados.
            """
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
            return final_df

        uploaded_file_1 = st.file_uploader("Envie o arquivo para 'Troca de Canal' (.xlsx)", type=["xlsx"])

        if uploaded_file_1 is not None:
            try:
                df_forms = pd.read_excel(uploaded_file_1)
                st.subheader("📄 Dados Originais (Troca de Canal)")
                st.dataframe(df_forms.head())
                
                final_df_forms = transform_google_forms_data(df_forms)
                
                output = io.BytesIO()
                final_df_forms.to_excel(output, index=False)
                output.seek(0)
                
                workbook = load_workbook(output)
                sheet = workbook.active
                
                dropdown_options_excel = '"Aprovado,Não Aprovado"'
                dv = DataValidation(type="list", formula1=dropdown_options_excel, allow_blank=True)
                dv.error = 'O valor inserido não está na lista.'
                dv.errorTitle = 'Valor Inválido'
                
                try:
                    col_for_dropdown_letter = get_column_letter(final_df_forms.columns.get_loc('Status') + 1)
                    dv.add(f'{col_for_dropdown_letter}2:{col_for_dropdown_letter}{sheet.max_row}')
                    sheet.add_data_validation(dv)
                except KeyError:
                    st.warning("A coluna 'Status' não foi encontrada no DataFrame final.")
                
                output_with_dropdown = io.BytesIO()
                workbook.save(output_with_dropdown)
                output_with_dropdown.seek(0)
                
                st.subheader("✅ Dados Transformados (Troca de Canal)")
                st.dataframe(final_df_forms)
                
                st.download_button(
                    label="📥 Baixar Arquivo de Troca de Canal",
                    data=output_with_dropdown.getvalue(),
                    file_name="troca_canal_processada.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
            except Exception as e:
                st.error(f"Ocorreu um erro durante o processamento de 'Troca de Canal': {e}")

    elif script_selection == "Circuito Execução":
        st.write("---")
        st.subheader("Circuito Execução")
        st.markdown("Este script converte os valores 'Presença' em pontuação, com base no nome das colunas.")

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
                        df_transformed[col] = df_transformed[col].apply(lambda x: points if x == "Presença" else 0)
            return df_transformed

        @st.cache_data
        def convert_df_to_excel(df):
            """Converte DataFrame para um arquivo Excel em memória."""
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                df.to_excel(writer, index=False)
            processed_data = output.getvalue()
            return processed_data

        uploaded_file_2 = st.file_uploader("Envie o arquivo para 'Circuito Execução' (.xlsx)", type=["xlsx"])

        if uploaded_file_2 is not None:
            try:
                df_points = pd.read_excel(uploaded_file_2)
                st.subheader("📄 Dados Originais (Circuito Execução)")
                st.dataframe(df_points)
                
                df_transformed_points = transform_points_columns(df_points)
                
                st.subheader("✅ Dados Transformados (Circuito Execução)")
                st.dataframe(df_transformed_points)
                
                excel_data = convert_df_to_excel(df_transformed_points)
                
                st.download_button(
                    label="📥 Baixar Arquivo de Circuito Execução Transformado",
                    data=excel_data,
                    file_name="circuito_execucao_transformado.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
            except Exception as e:
                st.error(f"Ocorreu um erro durante o processamento de 'Circuito Execução': {e}")
    if st.button("Voltar para o Início"):
        st.session_state['current_page'] = 'home'
        st.rerun()

def rh_page():
    st.title("Setor de RH")
    st.markdown("Bem-vindo(a) ao setor de RH. Abaixo estão os scripts disponíveis para análise.")

    script_choice = st.selectbox(
        "Selecione um script para executar:",
        ("Selecione...", "Controle de Jornada")
    )

    st.write("---")

    if script_choice == "Controle de Jornada":
        st.subheader("Controle de Jornada")
        st.markdown("Este script processa uma planilha de controle de jornada e calcula tempos de viagem, dirigibilidade e paradas.")

        def format_timedelta_as_hms(td):
            if pd.isna(td):
                return pd.NaT
            total_seconds = td.total_seconds()
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

        def format_timedelta_as_dias_hms(td):
            if pd.isna(td):
                return pd.NaT
            total_seconds = td.total_seconds()
            days, remainder = divmod(total_seconds, 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, seconds = divmod(remainder, 60)
            if days > 0:
                return f"{int(days)} dias {int(hours):02}:{int(minutes):02}:{int(seconds):02}"
            else:
                return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

        uploaded_file = st.file_uploader("Envie o arquivo 'Controle de Jornada.xlsx'", type=["xlsx"])

        if uploaded_file is not None:
            try:
                df = pd.read_excel(uploaded_file)
                st.subheader("📄 Dados Originais")
                st.dataframe(df.head())
                
                all_events = []
                for index, row in df.iterrows():
                    motorista = row.get('Motorista')
                    timestamp_str = row.get('Carimbo de data/hora')
                    if pd.isna(timestamp_str) or pd.isna(motorista):
                        continue
                    timestamp = pd.to_datetime(timestamp_str)
                    entry_type = row.get('Qual o tipo de lançamento?')
                    if entry_type == 'Inicio Jornada':
                        date_str = row.get('Dia')
                        time_str = row.get('Horário')
                        if pd.notna(date_str) and pd.notna(time_str):
                            start_time = pd.to_datetime(f"{date_str} {time_str}")
                            all_events.append({'Motorista': motorista, 'Tipo de Lançamento': entry_type, 'Inicio': start_time, 'Fim': None, 'Motivo': None, 'Carimbo de data/hora': timestamp})
                    elif entry_type == 'Inicio de Viagem':
                        date_str = row.get('Dia.1')
                        time_str = row.get('Horário.1')
                        if pd.notna(date_str) and pd.notna(time_str):
                            start_time = pd.to_datetime(f"{date_str} {time_str}")
                            all_events.append({'Motorista': motorista, 'Tipo de Lançamento': entry_type, 'Inicio': start_time, 'Fim': None, 'Motivo': None, 'Carimbo de data/hora': timestamp})
                    elif entry_type == 'Fim da Viagem':
                        time_str = row.get('Fim.5')
                        if pd.notna(time_str):
                            time_str = str(time_str).split(' ')[-1]
                            end_time = pd.to_datetime(f"{timestamp.strftime('%Y-%m-%d')} {time_str}")
                            all_events.append({'Motorista': motorista, 'Tipo de Lançamento': entry_type, 'Inicio': None, 'Fim': end_time, 'Motivo': None, 'Carimbo de data/hora': timestamp})
                    elif entry_type == 'Fim de Jornada':
                        date_str = row.get('Dia.2')
                        time_str = row.get('Horário.3')
                        if pd.notna(date_str) and pd.notna(time_str):
                            end_time = pd.to_datetime(f"{date_str} {time_str}")
                            all_events.append({'Motorista': motorista, 'Tipo de Lançamento': entry_type, 'Inicio': None, 'Fim': end_time, 'Motivo': None, 'Carimbo de data/hora': timestamp})
                    parada_cols_map = {
                        '1': {'inicio': 'Inicio ', 'fim': 'Fim', 'motivo': 'Motivo'},
                        '2': {'inicio': 'Inicio', 'fim': 'Fim.1', 'motivo': 'Motivo.1'},
                        '3': {'inicio': 'Inicio.1', 'fim': 'Fim.2', 'motivo': 'Motivo.2'},
                        '4': {'inicio': 'Inicio.2', 'fim': 'Fim.3', 'motivo': 'Motivo.3'},
                        '5': {'inicio': 'Inicio.3', 'fim': 'Fim.4', 'motivo': 'Motivo.4'}
                    }
                    for i in range(1, 6):
                        cols = parada_cols_map.get(str(i))
                        start_time_str = row.get(cols['inicio'])
                        end_time_str = row.get(cols['fim'])
                        motivo = row.get(cols['motivo'])
                        if pd.notna(start_time_str) and pd.notna(end_time_str) and pd.notna(motivo):
                            date_str = timestamp.strftime('%Y-%m-%d')
                            try:
                                start_time_str = str(start_time_str).split(' ')[-1]
                                end_time_str = str(end_time_str).split(' ')[-1]
                                start_time = pd.to_datetime(f"{date_str} {start_time_str}")
                                end_time = pd.to_datetime(f"{date_str} {end_time_str}")
                                all_events.append({'Motorista': motorista, 'Tipo de Lançamento': f'Parada {i}', 'Inicio': start_time, 'Fim': end_time, 'Motivo': motivo, 'Carimbo de data/hora': timestamp})
                            except ValueError:
                                st.error(f"Erro ao converter data/hora na linha {index} para 'Parada {i}'.")
                                continue
                consolidated_df = pd.DataFrame(all_events)
                consolidated_df.dropna(subset=['Motorista', 'Tipo de Lançamento'], how='all', inplace=True)
                consolidated_df.sort_values(by=['Motorista', 'Carimbo de data/hora'], inplace=True)
                consolidated_df.reset_index(drop=True, inplace=True)
                consolidated_df['Tempo Total de Jornada'] = pd.NaT
                consolidated_df['Tempo Total de Viagem'] = pd.NaT
                consolidated_df['Tempo de Dirigibilidade'] = pd.NaT
                consolidated_df['Tempo Almoço'] = pd.NaT
                consolidated_df['Tempo Carga/Descarga'] = pd.NaT
                consolidated_df['Tempo Liberação N.F.'] = pd.NaT
                consolidated_df['Tempo Repouso'] = pd.NaT
                for (motorista, dia), group in consolidated_df.groupby(['Motorista', consolidated_df['Carimbo de data/hora'].dt.date]):
                    inicio_jornada = group[group['Tipo de Lançamento'] == 'Inicio Jornada']['Inicio'].min()
                    fim_jornada = group[group['Tipo de Lançamento'] == 'Fim de Jornada']['Fim'].max()
                    tempo_jornada = fim_jornada - inicio_jornada if pd.notnull(inicio_jornada) and pd.notnull(fim_jornada) else timedelta(seconds=0)
                    inicio_viagem = group[group['Tipo de Lançamento'] == 'Inicio de Viagem']['Inicio'].min()
                    fim_viagem = group[group['Tipo de Lançamento'] == 'Fim da Viagem']['Fim'].max()
                    tempo_viagem = fim_viagem - inicio_viagem if pd.notnull(inicio_viagem) and pd.notnull(fim_viagem) else timedelta(seconds=0)
                    break_durations = group.dropna(subset=['Motivo']).copy()
                    if not break_durations.empty:
                        break_durations['Duration'] = break_durations['Fim'] - break_durations['Inicio']
                    else:
                        break_durations['Duration'] = timedelta(seconds=0)
                    almoco_duration = break_durations[break_durations['Motivo'] == 'Almoço']['Duration'].sum()
                    carga_descarga_duration = break_durations[break_durations['Motivo'] == 'Carga/Descarga']['Duration'].sum()
                    liberacao_nf_duration = break_durations[break_durations['Motivo'] == 'Liberação de N.F']['Duration'].sum()
                    repouso_duration = break_durations[break_durations['Motivo'] == 'Repouso']['Duration'].sum()
                    total_stop_time = almoco_duration + carga_descarga_duration + liberacao_nf_duration + repouso_duration
                    tempo_dirigibilidade = tempo_viagem - total_stop_time
                    consolidated_df.loc[group[group['Tipo de Lançamento'] == 'Fim de Jornada'].index, 'Tempo Total de Jornada'] = tempo_jornada
                    consolidated_df.loc[group[group['Tipo de Lançamento'] == 'Fim da Viagem'].index, 'Tempo Total de Viagem'] = tempo_viagem
                    consolidated_df.loc[group[group['Tipo de Lançamento'] == 'Fim da Viagem'].index, 'Tempo de Dirigibilidade'] = tempo_dirigibilidade
                    consolidated_df.loc[group[group['Motivo'] == 'Almoço'].index, 'Tempo Almoço'] = almoco_duration
                    consolidated_df.loc[group[group['Motivo'] == 'Carga/Descarga'].index, 'Tempo Carga/Descarga'] = carga_descarga_duration
                    consolidated_df.loc[group[group['Motivo'] == 'Liberação de N.F'].index, 'Tempo Liberação N.F.'] = liberacao_nf_duration
                    consolidated_df.loc[group[group['Motivo'] == 'Repouso'].index, 'Tempo Repouso'] = repouso_duration
                consolidated_df['Tempo Total de Jornada'] = consolidated_df['Tempo Total de Jornada'].apply(format_timedelta_as_dias_hms)
                consolidated_df['Tempo Total de Viagem'] = consolidated_df['Tempo Total de Viagem'].apply(format_timedelta_as_dias_hms)
                consolidated_df['Tempo de Dirigibilidade'] = consolidated_df['Tempo de Dirigibilidade'].apply(format_timedelta_as_hms)
                consolidated_df['Tempo Almoço'] = consolidated_df['Tempo Almoço'].apply(format_timedelta_as_hms)
                consolidated_df['Tempo Carga/Descarga'] = consolidated_df['Tempo Carga/Descarga'].apply(format_timedelta_as_hms)
                consolidated_df['Tempo Liberação N.F.'] = consolidated_df['Tempo Liberação N.F.'].apply(format_timedelta_as_hms)
                consolidated_df['Tempo Repouso'] = consolidated_df['Tempo Repouso'].apply(format_timedelta_as_hms)
                consolidated_df.drop(columns=['Carimbo de data/hora'], inplace=True)
                
                st.subheader("✅ Dados Processados")
                st.dataframe(consolidated_df)
                
                excel_data = io.BytesIO()
                consolidated_df.to_excel(excel_data, sheet_name="Dados Consolidados", index=False)
                excel_data.seek(0)
                
                st.download_button(
                    label="📥 Baixar Arquivo Processado",
                    data=excel_data,
                    file_name="Jornada_Calculo.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"Ocorreu um erro ao processar o arquivo: {e}")

    if st.button("Voltar para o Início"):
        st.session_state['current_page'] = 'home'
        st.rerun()

def commercial_page():
    st.title("Setor Comercial")
    st.markdown("Bem-vindo(a) ao setor Comercial. Abaixo estão os scripts disponíveis para análise.")

    script_selection = st.selectbox(
        "Selecione o script que deseja executar:",
        ("Selecione...", "Troca de Canal", "Circuito Execução")
    )

    if script_selection == "Troca de Canal":
        st.write("---")
        st.subheader("Troca de Canal")
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
            """
            Transforma dados de Google Forms, consolidando informações e adicionando
            uma coluna 'Status' com validação de dados.
            """
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
            return final_df

        uploaded_file_1 = st.file_uploader("Envie o arquivo para 'Troca de Canal' (.xlsx)", type=["xlsx"])

        if uploaded_file_1 is not None:
            try:
                df_forms = pd.read_excel(uploaded_file_1)
                st.subheader("📄 Dados Originais (Troca de Canal)")
                st.dataframe(df_forms.head())
                
                final_df_forms = transform_google_forms_data(df_forms)
                
                output = io.BytesIO()
                final_df_forms.to_excel(output, index=False)
                output.seek(0)
                
                workbook = load_workbook(output)
                sheet = workbook.active
                
                dropdown_options_excel = '"Aprovado,Não Aprovado"'
                dv = DataValidation(type="list", formula1=dropdown_options_excel, allow_blank=True)
                dv.error = 'O valor inserido não está na lista.'
                dv.errorTitle = 'Valor Inválido'
                
                try:
                    col_for_dropdown_letter = get_column_letter(final_df_forms.columns.get_loc('Status') + 1)
                    dv.add(f'{col_for_dropdown_letter}2:{col_for_dropdown_letter}{sheet.max_row}')
                    sheet.add_data_validation(dv)
                except KeyError:
                    st.warning("A coluna 'Status' não foi encontrada no DataFrame final.")
                
                output_with_dropdown = io.BytesIO()
                workbook.save(output_with_dropdown)
                output_with_dropdown.seek(0)
                
                st.subheader("✅ Dados Transformados (Troca de Canal)")
                st.dataframe(final_df_forms)
                
                st.download_button(
                    label="📥 Baixar Arquivo de Troca de Canal",
                    data=output_with_dropdown.getvalue(),
                    file_name="troca_canal_processada.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
            except Exception as e:
                st.error(f"Ocorreu um erro durante o processamento de 'Troca de Canal': {e}")

    elif script_selection == "Circuito Execução":
        st.write("---")
        st.subheader("Circuito Execução")
        st.markdown("Este script converte os valores 'Presença' em pontuação, com base no nome das colunas.")

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
                        df_transformed[col] = df_transformed[col].apply(lambda x: points if x == "Presença" else 0)
            return df_transformed

        @st.cache_data
        def convert_df_to_excel(df):
            """Converte DataFrame para um arquivo Excel em memória."""
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                df.to_excel(writer, index=False)
            processed_data = output.getvalue()
            return processed_data

        uploaded_file_2 = st.file_uploader("Envie o arquivo para 'Circuito Execução' (.xlsx)", type=["xlsx"])

        if uploaded_file_2 is not None:
            try:
                df_points = pd.read_excel(uploaded_file_2)
                st.subheader("📄 Dados Originais (Circuito Execução)")
                st.dataframe(df_points)
                
                df_transformed_points = transform_points_columns(df_points)
                
                st.subheader("✅ Dados Transformados (Circuito Execução)")
                st.dataframe(df_transformed_points)
                
                excel_data = convert_df_to_excel(df_transformed_points)
                
                st.download_button(
                    label="📥 Baixar Arquivo de Circuito Execução Transformado",
                    data=excel_data,
                    file_name="circuito_execucao_transformado.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
            except Exception as e:
                st.error(f"Ocorreu um erro durante o processamento de 'Circuito Execução': {e}")
    if st.button("Voltar para o Início"):
        st.session_state['current_page'] = 'home'
        st.rerun()

def rh_page():
    st.title("Setor de RH")
    st.markdown("Bem-vindo(a) ao setor de RH. Abaixo estão os scripts disponíveis para análise.")

    script_choice = st.selectbox(
        "Selecione um script para executar:",
        ("Selecione...", "Controle de Jornada")
    )

    st.write("---")

    if script_choice == "Controle de Jornada":
        st.subheader("Controle de Jornada")
        st.markdown("Este script processa uma planilha de controle de jornada e calcula tempos de viagem, dirigibilidade e paradas.")

        def format_timedelta_as_hms(td):
            if pd.isna(td):
                return pd.NaT
            total_seconds = td.total_seconds()
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

        def format_timedelta_as_dias_hms(td):
            if pd.isna(td):
                return pd.NaT
            total_seconds = td.total_seconds()
            days, remainder = divmod(total_seconds, 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, seconds = divmod(remainder, 60)
            if days > 0:
                return f"{int(days)} dias {int(hours):02}:{int(minutes):02}:{int(seconds):02}"
            else:
                return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

        uploaded_file = st.file_uploader("Envie o arquivo 'Controle de Jornada.xlsx'", type=["xlsx"])

        if uploaded_file is not None:
            try:
                df = pd.read_excel(uploaded_file)
                st.subheader("📄 Dados Originais")
                st.dataframe(df.head())
                
                all_events = []
                for index, row in df.iterrows():
                    motorista = row.get('Motorista')
                    timestamp_str = row.get('Carimbo de data/hora')
                    if pd.isna(timestamp_str) or pd.isna(motorista):
                        continue
                    timestamp = pd.to_datetime(timestamp_str)
                    entry_type = row.get('Qual o tipo de lançamento?')
                    if entry_type == 'Inicio Jornada':
                        date_str = row.get('Dia')
                        time_str = row.get('Horário')
                        if pd.notna(date_str) and pd.notna(time_str):
                            start_time = pd.to_datetime(f"{date_str} {time_str}")
                            all_events.append({'Motorista': motorista, 'Tipo de Lançamento': entry_type, 'Inicio': start_time, 'Fim': None, 'Motivo': None, 'Carimbo de data/hora': timestamp})
                    elif entry_type == 'Inicio de Viagem':
                        date_str = row.get('Dia.1')
                        time_str = row.get('Horário.1')
                        if pd.notna(date_str) and pd.notna(time_str):
                            start_time = pd.to_datetime(f"{date_str} {time_str}")
                            all_events.append({'Motorista': motorista, 'Tipo de Lançamento': entry_type, 'Inicio': start_time, 'Fim': None, 'Motivo': None, 'Carimbo de data/hora': timestamp})
                    elif entry_type == 'Fim da Viagem':
                        time_str = row.get('Fim.5')
                        if pd.notna(time_str):
                            time_str = str(time_str).split(' ')[-1]
                            end_time = pd.to_datetime(f"{timestamp.strftime('%Y-%m-%d')} {time_str}")
                            all_events.append({'Motorista': motorista, 'Tipo de Lançamento': entry_type, 'Inicio': None, 'Fim': end_time, 'Motivo': None, 'Carimbo de data/hora': timestamp})
                    elif entry_type == 'Fim de Jornada':
                        date_str = row.get('Dia.2')
                        time_str = row.get('Horário.3')
                        if pd.notna(date_str) and pd.notna(time_str):
                            end_time = pd.to_datetime(f"{date_str} {time_str}")
                            all_events.append({'Motorista': motorista, 'Tipo de Lançamento': entry_type, 'Inicio': None, 'Fim': end_time, 'Motivo': None, 'Carimbo de data/hora': timestamp})
                    parada_cols_map = {
                        '1': {'inicio': 'Inicio ', 'fim': 'Fim', 'motivo': 'Motivo'},
                        '2': {'inicio': 'Inicio', 'fim': 'Fim.1', 'motivo': 'Motivo.1'},
                        '3': {'inicio': 'Inicio.1', 'fim': 'Fim.2', 'motivo': 'Motivo.2'},
                        '4': {'inicio': 'Inicio.2', 'fim': 'Fim.3', 'motivo': 'Motivo.3'},
                        '5': {'inicio': 'Inicio.3', 'fim': 'Fim.4', 'motivo': 'Motivo.4'}
                    }
                    for i in range(1, 6):
                        cols = parada_cols_map.get(str(i))
                        start_time_str = row.get(cols['inicio'])
                        end_time_str = row.get(cols['fim'])
                        motivo = row.get(cols['motivo'])
                        if pd.notna(start_time_str) and pd.notna(end_time_str) and pd.notna(motivo):
                            date_str = timestamp.strftime('%Y-%m-%d')
                            try:
                                start_time_str = str(start_time_str).split(' ')[-1]
                                end_time_str = str(end_time_str).split(' ')[-1]
                                start_time = pd.to_datetime(f"{date_str} {start_time_str}")
                                end_time = pd.to_datetime(f"{date_str} {end_time_str}")
                                all_events.append({'Motorista': motorista, 'Tipo de Lançamento': f'Parada {i}', 'Inicio': start_time, 'Fim': end_time, 'Motivo': motivo, 'Carimbo de data/hora': timestamp})
                            except ValueError:
                                st.error(f"Erro ao converter data/hora na linha {index} para 'Parada {i}'.")
                                continue
                consolidated_df = pd.DataFrame(all_events)
                consolidated_df.dropna(subset=['Motorista', 'Tipo de Lançamento'], how='all', inplace=True)
                consolidated_df.sort_values(by=['Motorista', 'Carimbo de data/hora'], inplace=True)
                consolidated_df.reset_index(drop=True, inplace=True)
                consolidated_df['Tempo Total de Jornada'] = pd.NaT
                consolidated_df['Tempo Total de Viagem'] = pd.NaT
                consolidated_df['Tempo de Dirigibilidade'] = pd.NaT
                consolidated_df['Tempo Almoço'] = pd.NaT
                consolidated_df['Tempo Carga/Descarga'] = pd.NaT
                consolidated_df['Tempo Liberação N.F.'] = pd.NaT
                consolidated_df['Tempo Repouso'] = pd.NaT
                for (motorista, dia), group in consolidated_df.groupby(['Motorista', consolidated_df['Carimbo de data/hora'].dt.date]):
                    inicio_jornada = group[group['Tipo de Lançamento'] == 'Inicio Jornada']['Inicio'].min()
                    fim_jornada = group[group['Tipo de Lançamento'] == 'Fim de Jornada']['Fim'].max()
                    tempo_jornada = fim_jornada - inicio_jornada if pd.notnull(inicio_jornada) and pd.notnull(fim_jornada) else timedelta(seconds=0)
                    inicio_viagem = group[group['Tipo de Lançamento'] == 'Inicio de Viagem']['Inicio'].min()
                    fim_viagem = group[group['Tipo de Lançamento'] == 'Fim da Viagem']['Fim'].max()
                    tempo_viagem = fim_viagem - inicio_viagem if pd.notnull(inicio_viagem) and pd.notnull(fim_viagem) else timedelta(seconds=0)
                    break_durations = group.dropna(subset=['Motivo']).copy()
                    if not break_durations.empty:
                        break_durations['Duration'] = break_durations['Fim'] - break_durations['Inicio']
                    else:
                        break_durations['Duration'] = timedelta(seconds=0)
                    almoco_duration = break_durations[break_durations['Motivo'] == 'Almoço']['Duration'].sum()
                    carga_descarga_duration = break_durations[break_durations['Motivo'] == 'Carga/Descarga']['Duration'].sum()
                    liberacao_nf_duration = break_durations[break_durations['Motivo'] == 'Liberação de N.F']['Duration'].sum()
                    repouso_duration = break_durations[break_durations['Motivo'] == 'Repouso']['Duration'].sum()
                    total_stop_time = almoco_duration + carga_descarga_duration + liberacao_nf_duration + repouso_duration
                    tempo_dirigibilidade = tempo_viagem - total_stop_time
                    consolidated_df.loc[group[group['Tipo de Lançamento'] == 'Fim de Jornada'].index, 'Tempo Total de Jornada'] = tempo_jornada
                    consolidated_df.loc[group[group['Tipo de Lançamento'] == 'Fim da Viagem'].index, 'Tempo Total de Viagem'] = tempo_viagem
                    consolidated_df.loc[group[group['Tipo de Lançamento'] == 'Fim da Viagem'].index, 'Tempo de Dirigibilidade'] = tempo_dirigibilidade
                    consolidated_df.loc[group[group['Motivo'] == 'Almoço'].index, 'Tempo Almoço'] = almoco_duration
                    consolidated_df.loc[group[group['Motivo'] == 'Carga/Descarga'].index, 'Tempo Carga/Descarga'] = carga_descarga_duration
                    consolidated_df.loc[group[group['Motivo'] == 'Liberação de N.F'].index, 'Tempo Liberação N.F.'] = liberacao_nf_duration
                    consolidated_df.loc[group[group['Motivo'] == 'Repouso'].index, 'Tempo Repouso'] = repouso_duration
                consolidated_df['Tempo Total de Jornada'] = consolidated_df['Tempo Total de Jornada'].apply(format_timedelta_as_dias_hms)
                consolidated_df['Tempo Total de Viagem'] = consolidated_df['Tempo Total de Viagem'].apply(format_timedelta_as_dias_hms)
                consolidated_df['Tempo de Dirigibilidade'] = consolidated_df['Tempo de Dirigibilidade'].apply(format_timedelta_as_hms)
                consolidated_df['Tempo Almoço'] = consolidated_df['Tempo Almoço'].apply(format_timedelta_as_hms)
                consolidated_df['Tempo Carga/Descarga'] = consolidated_df['Tempo Carga/Descarga'].apply(format_timedelta_as_hms)
                consolidated_df['Tempo Liberação N.F.'] = consolidated_df['Tempo Liberação N.F.'].apply(format_timedelta_as_hms)
                consolidated_df['Tempo Repouso'] = consolidated_df['Tempo Repouso'].apply(format_timedelta_as_hms)
                consolidated_df.drop(columns=['Carimbo de data/hora'], inplace=True)
                
                st.subheader("✅ Dados Processados")
                st.dataframe(consolidated_df)
                
                excel_data = io.BytesIO()
                consolidated_df.to_excel(excel_data, sheet_name="Dados Consolidados", index=False)
                excel_data.seek(0)
                
                st.download_button(
                    label="📥 Baixar Arquivo Processado",
                    data=excel_data,
                    file_name="Jornada_Calculo.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"Ocorreu um erro ao processar o arquivo: {e}")

    if st.button("Voltar para o Início"):
        st.session_state['current_page'] = 'home'
        st.rerun()

def commercial_page():
    st.title("Setor Comercial")
    st.markdown("Bem-vindo(a) ao setor Comercial. Abaixo estão os scripts disponíveis para análise.")

    script_selection = st.selectbox(
        "Selecione o script que deseja executar:",
        ("Selecione...", "Troca de Canal", "Circuito Execução")
    )

    if script_selection == "Troca de Canal":
        st.write("---")
        st.subheader("Troca de Canal")
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
            """
            Transforma dados de Google Forms, consolidando informações e adicionando
            uma coluna 'Status' com validação de dados.
            """
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
            return final_df

        uploaded_file_1 = st.file_uploader("Envie o arquivo para 'Troca de Canal' (.xlsx)", type=["xlsx"])

        if uploaded_file_1 is not None:
            try:
                df_forms = pd.read_excel(uploaded_file_1)
                st.subheader("📄 Dados Originais (Troca de Canal)")
                st.dataframe(df_forms.head())
                
                final_df_forms = transform_google_forms_data(df_forms)
                
                output = io.BytesIO()
                final_df_forms.to_excel(output, index=False)
                output.seek(0)
                
                workbook = load_workbook(output)
                sheet = workbook.active
                
                dropdown_options_excel = '"Aprovado,Não Aprovado"'
                dv = DataValidation(type="list", formula1=dropdown_options_excel, allow_blank=True)
                dv.error = 'O valor inserido não está na lista.'
                dv.errorTitle = 'Valor Inválido'
                
                try:
                    col_for_dropdown_letter = get_column_letter(final_df_forms.columns.get_loc('Status') + 1)
                    dv.add(f'{col_for_dropdown_letter}2:{col_for_dropdown_letter}{sheet.max_row}')
                    sheet.add_data_validation(dv)
                except KeyError:
                    st.warning("A coluna 'Status' não foi encontrada no DataFrame final.")
                
                output_with_dropdown = io.BytesIO()
                workbook.save(output_with_dropdown)
                output_with_dropdown.seek(0)
                
                st.subheader("✅ Dados Transformados (Troca de Canal)")
                st.dataframe(final_df_forms)
                
                st.download_button(
                    label="📥 Baixar Arquivo de Troca de Canal",
                    data=output_with_dropdown.getvalue(),
                    file_name="troca_canal_processada.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
            except Exception as e:
                st.error(f"Ocorreu um erro durante o processamento de 'Troca de Canal': {e}")

    elif script_selection == "Circuito Execução":
        st.write("---")
        st.subheader("Circuito Execução")
        st.markdown("Este script converte os valores 'Presença' em pontuação, com base no nome das colunas.")

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
                        df_transformed[col] = df_transformed[col].apply(lambda x: points if x == "Presença" else 0)
            return df_transformed

        @st.cache_data
        def convert_df_to_excel(df):
            """Converte DataFrame para um arquivo Excel em memória."""
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                df.to_excel(writer, index=False)
            processed_data = output.getvalue()
            return processed_data

        uploaded_file_2 = st.file_uploader("Envie o arquivo para 'Circuito Execução' (.xlsx)", type=["xlsx"])

        if uploaded_file_2 is not None:
            try:
                df_points = pd.read_excel(uploaded_file_2)
                st.subheader("📄 Dados Originais (Circuito Execução)")
                st.dataframe(df_points)
                
                df_transformed_points = transform_points_columns(df_points)
                
                st.subheader("✅ Dados Transformados (Circuito Execução)")
                st.dataframe(df_transformed_points)
                
                excel_data = convert_df_to_excel(df_transformed_points)
                
                st.download_button(
                    label="📥 Baixar Arquivo de Circuito Execução Transformado",
                    data=excel_data,
                    file_name="circuito_execucao_transformado.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
            except Exception as e:
                st.error(f"Ocorreu um erro durante o processamento de 'Circuito Execução': {e}")
    if st.button("Voltar para o Início"):
        st.session_state['current_page'] = 'home'
        st.rerun()

def rh_page():
    st.title("Setor de RH")
    st.markdown("Bem-vindo(a) ao setor de RH. Abaixo estão os scripts disponíveis para análise.")

    script_choice = st.selectbox(
        "Selecione um script para executar:",
        ("Selecione...", "Controle de Jornada")
    )

    st.write("---")

    if script_choice == "Controle de Jornada":
        st.subheader("Controle de Jornada")
        st.markdown("Este script processa uma planilha de controle de jornada e calcula tempos de viagem, dirigibilidade e paradas.")

        def format_timedelta_as_hms(td):
            if pd.isna(td):
                return pd.NaT
            total_seconds = td.total_seconds()
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

        def format_timedelta_as_dias_hms(td):
            if pd.isna(td):
                return pd.NaT
            total_seconds = td.total_seconds()
            days, remainder = divmod(total_seconds, 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, seconds = divmod(remainder, 60)
            if days > 0:
                return f"{int(days)} dias {int(hours):02}:{int(minutes):02}:{int(seconds):02}"
            else:
                return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

        uploaded_file = st.file_uploader("Envie o arquivo 'Controle de Jornada.xlsx'", type=["xlsx"])

        if uploaded_file is not None:
            try:
                df = pd.read_excel(uploaded_file)
                st.subheader("📄 Dados Originais")
                st.dataframe(df.head())
                
                all_events = []
                for index, row in df.iterrows():
                    motorista = row.get('Motorista')
                    timestamp_str = row.get('Carimbo de data/hora')
                    if pd.isna(timestamp_str) or pd.isna(motorista):
                        continue
                    timestamp = pd.to_datetime(timestamp_str)
                    entry_type = row.get('Qual o tipo de lançamento?')
                    if entry_type == 'Inicio Jornada':
                        date_str = row.get('Dia')
                        time_str = row.get('Horário')
                        if pd.notna(date_str) and pd.notna(time_str):
                            start_time = pd.to_datetime(f"{date_str} {time_str}")
                            all_events.append({'Motorista': motorista, 'Tipo de Lançamento': entry_type, 'Inicio': start_time, 'Fim': None, 'Motivo': None, 'Carimbo de data/hora': timestamp})
                    elif entry_type == 'Inicio de Viagem':
                        date_str = row.get('Dia.1')
                        time_str = row.get('Horário.1')
                        if pd.notna(date_str) and pd.notna(time_str):
                            start_time = pd.to_datetime(f"{date_str} {time_str}")
                            all_events.append({'Motorista': motorista, 'Tipo de Lançamento': entry_type, 'Inicio': start_time, 'Fim': None, 'Motivo': None, 'Carimbo de data/hora': timestamp})
                    elif entry_type == 'Fim da Viagem':
                        time_str = row.get('Fim.5')
                        if pd.notna(time_str):
                            time_str = str(time_str).split(' ')[-1]
                            end_time = pd.to_datetime(f"{timestamp.strftime('%Y-%m-%d')} {time_str}")
                            all_events.append({'Motorista': motorista, 'Tipo de Lançamento': entry_type, 'Inicio': None, 'Fim': end_time, 'Motivo': None, 'Carimbo de data/hora': timestamp})
                    elif entry_type == 'Fim de Jornada':
                        date_str = row.get('Dia.2')
                        time_str = row.get('Horário.3')
                        if pd.notna(date_str) and pd.notna(time_str):
                            end_time = pd.to_datetime(f"{date_str} {time_str}")
                            all_events.append({'Motorista': motorista, 'Tipo de Lançamento': entry_type, 'Inicio': None, 'Fim': end_time, 'Motivo': None, 'Carimbo de data/hora': timestamp})
                    parada_cols_map = {
                        '1': {'inicio': 'Inicio ', 'fim': 'Fim', 'motivo': 'Motivo'},
                        '2': {'inicio': 'Inicio', 'fim': 'Fim.1', 'motivo': 'Motivo.1'},
                        '3': {'inicio': 'Inicio.1', 'fim': 'Fim.2', 'motivo': 'Motivo.2'},
                        '4': {'inicio': 'Inicio.2', 'fim': 'Fim.3', 'motivo': 'Motivo.3'},
                        '5': {'inicio': 'Inicio.3', 'fim': 'Fim.4', 'motivo': 'Motivo.4'}
                    }
                    for i in range(1, 6):
                        cols = parada_cols_map.get(str(i))
                        start_time_str = row.get(cols['inicio'])
                        end_time_str = row.get(cols['fim'])
                        motivo = row.get(cols['motivo'])
                        if pd.notna(start_time_str) and pd.notna(end_time_str) and pd.notna(motivo):
                            date_str = timestamp.strftime('%Y-%m-%d')
                            try:
                                start_time_str = str(start_time_str).split(' ')[-1]
                                end_time_str = str(end_time_str).split(' ')[-1]
                                start_time = pd.to_datetime(f"{date_str} {start_time_str}")
                                end_time = pd.to_datetime(f"{date_str} {end_time_str}")
                                all_events.append({'Motorista': motorista, 'Tipo de Lançamento': f'Parada {i}', 'Inicio': start_time, 'Fim': end_time, 'Motivo': motivo, 'Carimbo de data/hora': timestamp})
                            except ValueError:
                                st.error(f"Erro ao converter data/hora na linha {index} para 'Parada {i}'.")
                                continue
                consolidated_df = pd.DataFrame(all_events)
                consolidated_df.dropna(subset=['Motorista', 'Tipo de Lançamento'], how='all', inplace=True)
                consolidated_df.sort_values(by=['Motorista', 'Carimbo de data/hora'], inplace=True)
                consolidated_df.reset_index(drop=True, inplace=True)
                consolidated_df['Tempo Total de Jornada'] = pd.NaT
                consolidated_df['Tempo Total de Viagem'] = pd.NaT
                consolidated_df['Tempo de Dirigibilidade'] = pd.NaT
                consolidated_df['Tempo Almoço'] = pd.NaT
                consolidated_df['Tempo Carga/Descarga'] = pd.NaT
                consolidated_df['Tempo Liberação N.F.'] = pd.NaT
                consolidated_df['Tempo Repouso'] = pd.NaT
                for (motorista, dia), group in consolidated_df.groupby(['Motorista', consolidated_df['Carimbo de data/hora'].dt.date]):
                    inicio_jornada = group[group['Tipo de Lançamento'] == 'Inicio Jornada']['Inicio'].min()
                    fim_jornada = group[group['Tipo de Lançamento'] == 'Fim de Jornada']['Fim'].max()
                    tempo_jornada = fim_jornada - inicio_jornada if pd.notnull(inicio_jornada) and pd.notnull(fim_jornada) else timedelta(seconds=0)
                    inicio_viagem = group[group['Tipo de Lançamento'] == 'Inicio de Viagem']['Inicio'].min()
                    fim_viagem = group[group['Tipo de Lançamento'] == 'Fim da Viagem']['Fim'].max()
                    tempo_viagem = fim_viagem - inicio_viagem if pd.notnull(inicio_viagem) and pd.notnull(fim_viagem) else timedelta(seconds=0)
                    break_durations = group.dropna(subset=['Motivo']).copy()
                    if not break_durations.empty:
                        break_durations['Duration'] = break_durations['Fim'] - break_durations['Inicio']
                    else:
                        break_durations['Duration'] = timedelta(seconds=0)
                    almoco_duration = break_durations[break_durations['Motivo'] == 'Almoço']['Duration'].sum()
                    carga_descarga_duration = break_durations[break_durations['Motivo'] == 'Carga/Descarga']['Duration'].sum()
                    liberacao_nf_duration = break_durations[break_durations['Motivo'] == 'Liberação de N.F']['Duration'].sum()
                    repouso_duration = break_durations[break_durations['Motivo'] == 'Repouso']['Duration'].sum()
                    total_stop_time = almoco_duration + carga_descarga_duration + liberacao_nf_duration + repouso_duration
                    tempo_dirigibilidade = tempo_viagem - total_stop_time
                    consolidated_df.loc[group[group['Tipo de Lançamento'] == 'Fim de Jornada'].index, 'Tempo Total de Jornada'] = tempo_jornada
                    consolidated_df.loc[group[group['Tipo de Lançamento'] == 'Fim da Viagem'].index, 'Tempo Total de Viagem'] = tempo_viagem
                    consolidated_df.loc[group[group['Tipo de Lançamento'] == 'Fim da Viagem'].index, 'Tempo de Dirigibilidade'] = tempo_dirigibilidade
                    consolidated_df.loc[group[group['Motivo'] == 'Almoço'].index, 'Tempo Almoço'] = almoco_duration
                    consolidated_df.loc[group[group['Motivo'] == 'Carga/Descarga'].index, 'Tempo Carga/Descarga'] = carga_descarga_duration
                    consolidated_df.loc[group[group['Motivo'] == 'Liberação de N.F'].index, 'Tempo Liberação N.F.'] = liberacao_nf_duration
                    consolidated_df.loc[group[group['Motivo'] == 'Repouso'].index, 'Tempo Repouso'] = repouso_duration
                consolidated_df['Tempo Total de Jornada'] = consolidated_df['Tempo Total de Jornada'].apply(format_timedelta_as_dias_hms)
                consolidated_df['Tempo Total de Viagem'] = consolidated_df['Tempo Total de Viagem'].apply(format_timedelta_as_dias_hms)
                consolidated_df['Tempo de Dirigibilidade'] = consolidated_df['Tempo de Dirigibilidade'].apply(format_timedelta_as_hms)
                consolidated_df['Tempo Almoço'] = consolidated_df['Tempo Almoço'].apply(format_timedelta_as_hms)
                consolidated_df['Tempo Carga/Descarga'] = consolidated_df['Tempo Carga/Descarga'].apply(format_timedelta_as_hms)
                consolidated_df['Tempo Liberação N.F.'] = consolidated_df['Tempo Liberação N.F.'].apply(format_timedelta_as_hms)
                consolidated_df['Tempo Repouso'] = consolidated_df['Tempo Repouso'].apply(format_timedelta_as_hms)
                consolidated_df.drop(columns=['Carimbo de data/hora'], inplace=True)
                
                st.subheader("✅ Dados Processados")
                st.dataframe(consolidated_df)
                
                excel_data = io.BytesIO()
                consolidated_df.to_excel(excel_data, sheet_name="Dados Consolidados", index=False)
                excel_data.seek(0)
                
                st.download_button(
                    label="📥 Baixar Arquivo Processado",
                    data=excel_data,
                    file_name="Jornada_Calculo.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"Ocorreu um erro ao processar o arquivo: {e}")

    if st.button("Voltar para o Início"):
        st.session_state['current_page'] = 'home'
        st.rerun()

def site_page():
    st.title("Setor Sítio")
    st.markdown("Bem-vindo(a) ao setor Sítio. Abaixo estão os scripts disponíveis para análise.")
    
    script_choice = st.selectbox(
        "Selecione um script para executar:",
        ("Selecione...", "Sítio Santa Izabel")
    )

    st.write("---")

    if script_choice == "Sítio Santa Izabel":
        st.subheader("Sítio Santa Izabel")
        st.markdown("Este script processa a planilha de controle do Sítio Santa Izabel e a divide em abas com base nos lançamentos.")

        def normalize_columns(columns_list):
            """
            Normaliza uma lista de nomes de colunas, removendo espaços extras,
            caracteres especiais e quebras de linha.
            """
            normalized_list = []
            for col in columns_list:
                col = re.sub(r'\s+', ' ', col).strip()
                col = col.replace('\n', ' ')
                normalized_list.append(col)
            return normalized_list

        uploaded_file = st.file_uploader("Envie o arquivo 'SÍTIO SANTA IZABEL.xlsx'", type=["xlsx"])

        if uploaded_file is not None:
            try:
                df = pd.read_excel(uploaded_file, engine='openpyxl')
                st.subheader("📄 Dados Originais")
                st.dataframe(df.head())

                df.columns = normalize_columns(df.columns)

                planilhas_config = {
                    'Pulverização': [
                        'Carimbo de data/hora', 'Qual lançamento', 'Qual Talhão?',
                        'Diagnóstico e Justificativa', 'Fase Fenológica', 'Previsão colheita',
                        'Problema Alvo (Praga, Doença, Planta Daninha ou Deficiência Nutricional)',
                        'Diagnóstico e Nível de Infestação/Ocorrência (Descrição detalhada)',
                        'Justificativa Técnica para a Recomendação',
                        'PRODUTO (N.C*E I.A.**)','Volume de Calda Recomendado (L/ha)',
                        'Equipamento de aplicação', 'Número de Aplicações Recomendadas',
                        'Intervalo entre Aplicações (dias - se houver mais de uma)', 
                        'Modo de Aplicação','Época/Estádio de Aplicação',
                        'Intervalo de Segurança/Período de Carência (dias)',
                        'Intervalo de Reentrada na Área (horas)',
                        'Equipamento de Proteção Individual (EPI)',
                        'Condições Climáticas Ideais para Aplicação ex: "Evitar ventos acima de 10 km/h, temperatura abaixo de 30°C, umidade relativa acima de 55%"',
                        'Cuidados com a Calda e Descarte de Embalagens ex: "Realizar tríplice lavagem das embalagens e descartá-las em locais indicados"',
                        'Informações sobre Mistura em Tanque (se aplicável)',
                        'Observações Adicionais/Advertências',
                    ],
                    'Controle de Irrigação': [
                        'Carimbo de data/hora', 'Qual lançamento', 'Período', 'Setor/Talhão', 
                        'Hora(s) de irrigação', 'Volume de Água (L)', 'Tipo de Irrigação',
                        'Observações (Clima/Outros)', 'Responsável', 'Próxima Irrigação Sugerida'
                    ],
                    'Controle de Pragas': [
                        'Carimbo de data/hora', 'Qual lançamento', 'DATA (3)', 'PRAGA', 'RECOMENDAÇÃO',
                        'RECEITA', 'MODO DE APLICAÇÃO', 'PERÍODO', 'OBSERVAÇÃO'
                    ],
                    'Pluviômetro - (somente em dias de chuva)': [
                        'Carimbo de data/hora', 'Qual lançamento', 'DATA (1)', 'LEITURA(MM)', 'OBSERVAÇÕES'
                    ],
                    'Hidrômetro': [
                        'Carimbo de data/hora', 'Qual lançamento', 'DATA (2)', 'LEITURA (m³)'
                    ],
                    'Lavagem de EPIs': [
                        'Carimbo de data/hora', 'Qual lançamento', 'Data da Lavagem:', 'Responsável pela Lavagem ',
                        'Local da Lavagem', 'EPI', 'Agente de Limpeza Utilizado:', 'Temperatura da Água', 'Ciclos de enxague',
                        'Condições de Armazenamento'
                    ],
                    'Registro de aplicações': [
                        'Carimbo de data/hora', 'Qual lançamento', 'Cultura e/ou Variedade Tratada',
                        'Local da Aplicação ( Por favor, especifique a zona geográfica, nome/referência da exploração, e o campo de produção, pomar, estufa ou instalação onde a cultura se encontra.)',
                        'Data de Início da Aplicação',
                        'Data de Fim da Aplicação',
                        'Nome Comercial Registrado do Produto',
                        'Intervalo de Segurança Pré-Colheita (PHS)',
                        'Quantidade de Produto Aplicado',
                        'Concentração ou Frequência',
                        'Nome Completo do Aplicador',
                        'Nome Completo da Pessoa Tecnicamente Responsável',
                    ],
                    'Limpeza do Local': [
                        'Carimbo de data/hora', 'Qual lançamento', 'LOCAL', 'Marque com "X" a opção que melhor descreve o estado de limpeza [PISOS]',
                        'Marque com "X" a opção que melhor descreve o estado de limpeza [LIXEIRAS]', 'Marque com "X" a opção que melhor descreve o estado de limpeza [Superfícies (mesas, bancadas)]',
                        'Marque com "X" a opção que melhor descreve o estado de limpeza [Janelas e vidros]', 
                        'Marque com "X" a opção que melhor descreve o estado de limpeza [Banheiros]', 'Marque com "X" a opção que melhor descreve o estado de limpeza [Descarte de resíduos]',
                        'Marque com "X" a opção que melhor descreve o estado de limpeza [Organização geral]',
                        'Problemas encontrados', 'Sugestões para melhoria'
                    ],
                    'Limpeza dos Equipamentos e Dispositivos': [
                        'Qual a Limpeza (7)', 'Data da Lavagem (7)', 'Item Lavado (7)', 'Produto Utilizado (7)', 'Procedimento de Lavagem (Exemplo "submersão" , "pré-lavagem") (7)',
                        'Responsável pela Lavagem (7)', 'Observações (7)' 
                    ]
                }
                
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    for sheet_name, columns in planilhas_config.items():
                        try:
                            normalized_columns = normalize_columns(columns)
                            if sheet_name == 'Pulverização':
                                for col in df.columns:
                                    if re.search(r'\(\d+\)', col) and col not in ['DATA (1)', 'DATA (2)', 'DATA (3)']:
                                        normalized_columns.append(col)
                                normalized_columns = list(dict.fromkeys(normalized_columns))

                            df_filtered = df[df['Qual lançamento'] == sheet_name]
                            existing_columns = [col for col in normalized_columns if col in df_filtered.columns]
                            df_sheet = df_filtered[existing_columns]

                            df_sheet.to_excel(writer, sheet_name=sheet_name, index=False)
                            st.info(f"Aba '{sheet_name}' criada com sucesso.")

                        except KeyError as e:
                            st.warning(f"Aviso: Ocorreu um erro ao filtrar a aba '{sheet_name}'. Verifique se o nome da aba está correto.")
                            continue
                
                output.seek(0)
                st.subheader("✅ Processo Concluído")
                st.success("O arquivo foi processado e está pronto para download.")
                
                st.download_button(
                    label="📥 Baixar Arquivo Processado",
                    data=output,
                    file_name="sitio_santaizabel.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"Ocorreu um erro ao processar o arquivo: {e}")
    
    if st.button("Voltar para o Início"):
        st.session_state['current_page'] = 'home'
        st.rerun()

# Lógica principal da página
if 'is_logged_in' not in st.session_state:
    st.session_state['is_logged_in'] = False # Linha corrigida
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = 'login'
if 'LOGIN_INFO' not in st.session_state:
    st.session_state['LOGIN_INFO'] = {
        "admin": "Joao789",
        "amanda": "12345",
        "marcia": "54321"
    }

# Configurações iniciais da página
st.set_page_config(
    page_title="Lince Distribuidora de Bebidas - Login",
    page_icon="🏠",
    layout="centered"
)

# Adiciona CSS personalizado para um visual mais limpo e profissional
st.markdown("""
<style>
    .stApp {
        background-color: #f0f2f6;
    }
    div.stButton > button:first-child {
        background-color: #007bff;
        color: white;
        border-radius: 5px;
        padding: 10px 20px;
        border: none;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    div.stButton > button:first-child:hover {
        background-color: #0056b3;
        transform: translateY(-2px);
        box-shadow: 0 6px 8px rgba(0, 0, 0, 0.15);
    }
    .stTextInput label, .stForm > div > div > label {
        font-weight: bold;
        color: #333;
    }
    .stTitle {
        text-align: center;
        color: #004d99;
        font-family: 'Arial Black', sans-serif;
    }
    .st-emotion-cache-1c7y3q { /* CSS para o container do formulário */
        background-color: #F8F8F8;
        padding: 30px;
        border-radius: 10px;
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
    }
    .centered-icon {
        text-align: center;
        font-size: 5rem;
    }
    .app-card {
        background-color: #fff;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        text-align: center;
        margin-bottom: 20px;
        cursor: pointer;
        transition: transform 0.2s;
        height: 100%;
    }
    .app-card:hover {
        transform: translateY(-5px);
    }
    .app-card h3 {
        color: #004d99;
        font-size: 1.2rem;
    }
    .app-card p {
        color: #555;
        font-size: 0.9rem;
    }
    .st-emotion-cache-1f81n9p a { /* Estilo para o link do botão para parecer um card */
        text-decoration: none;
        color: inherit;
    }
</style>
""", unsafe_allow_html=True)

if st.session_state.get('is_logged_in', False):
    page_functions = {
        'home': main_page,
        'logistics': logistics_page,
        'commercial': commercial_page,
        'rh': rh_page,
        'site': site_page
    }
    page_functions.get(st.session_state.get('current_page', 'home'), main_page)()
else:
    login_form()
