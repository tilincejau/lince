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
import xlsxwriter

# Funções que representam cada página
def login_form():
    """Exibe o formulário de login com um design aprimorado."""
    
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
        
        # FUNÇÃO CORRIGIDA PARA LER O TXT
        def parse_estoque_txt_st(file_content):
            """
            Analisa o arquivo TXT lendo linha por linha, extraindo dados 
            de forma robusta, ignorando o espaçamento inconsistente.
            """
            lines = [line.decode('latin1') for line in file_content.getvalue().splitlines()]
            
            separator_string = '-' * 116
            separator_indices = [i for i, line in enumerate(lines) if separator_string in line]
            if len(separator_indices) < 2:
                st.warning("Não foi possível localizar os separadores de colunas no arquivo TXT.")
                return pd.DataFrame()

            start_line = separator_indices[1] + 1
            
            col_names = [
                'COD.RED.', 'DESCRIÇÃO',
                'SLD INICIAL CX', 'SLD INICIAL UN',
                'ENTRADAS CX', 'ENTRADAS UN',
                'SAÍDAS CX', 'SAÍDAS UN',
                'SALDO FÍSICO CX', 'SALDO FÍSICO UN',
                'CONT. FÍSICA CX', 'CONT. FÍSICA UN',
                'DIFERENÇA CX', 'DIFERENÇA UN'
            ]
            data = []
            
            # Regex para capturar campos individuais de forma flexível
            pattern = re.compile(
                r'^\s*(\d+)\s+'
                r'(.+?)'
                r'\s*([-+]?\d*)\s*([-+]?\d*)\s*I'
                r'\s*([-+]?\d*)\s*([-+]?\d*)\s*I'
                r'\s*([-+]?\d*)\s*([-+]?\d*)\s*I'
                r'\s*([-+]?\d*)\s*([-+]?\d*)\s*I'
                r'\s*([-+]?\d*)\s*([-+]?\d*)\s*I'
                r'\s*([-+]?\d*)\s*([-+]?\d*)\s*I'
            )

            for line in lines[start_line:]:
                line = line.strip()
                if not line or 'TOTAL GERAL' in line:
                    continue
                
                match = pattern.match(line)
                if match:
                    groups = list(match.groups())
                    
                    row_values = [groups[0], groups[1].strip()]
                    
                    # Extrai os 6 pares de CX e UN e converte para inteiros
                    for i in range(2, len(groups), 2):
                        cx = groups[i].strip() if groups[i] and groups[i].strip() else '0'
                        un = groups[i+1].strip() if groups[i+1] and groups[i+1].strip() else '0'
                        row_values.extend([int(cx), int(un)])
                    
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
                df_estoque = parse_estoque_txt_st(uploaded_txt_file)

                if df_estoque.empty:
                    st.warning("O arquivo TXT está vazio ou não pôde ser processado.")
                    return

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
                        df_all_processed_pdf_data[['Vasilhame', 'Dia']] if 'Vasilhame' in df_all_processed_pdf_data.columns else pd.DataFrame(columns=['Vasilhames', 'Dia'])
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
                
                # Lógica de leitura baseada na extensão do arquivo
                file_extension = os.path.splitext(uploaded_file.name)[1].lower()

                if file_extension == '.xlsx':
                    df = pd.read_excel(uploaded_file, engine='openpyxl')
                elif file_extension == '.csv':
                    df = pd.read_csv(uploaded_file)
                else:
                    st.error("Formato de arquivo não suportado. Por favor, envie um arquivo .xlsx ou .csv.")
                    return
                
                # Mapeamento de nomes de colunas para lidar com variações
                column_mapping = {
                    'DATA ABASTECIMENTO': ['Carimbo de data/hora', 'DATA', 'DATA ABASTECIMENTO', 'DATE'],
                    'HORÁRIO': ['Carimbo de data/hora'],
                    'TIPO DE ABASTECIMENTO': ['Qual o tipo de abastecimento?', 'TIPO', 'COMBUSTÍVEL'],
                    'PLACA': ['PLACA'],
                    'KM': ['KM', 'QUILOMETRAGEM'],
                    'LITROS': ['LITROS', 'VOLUME'],
                    'MOTORISTA': ['MOTORISTA', 'RESPONSÁVEL'],
                }
                
                # Crie uma cópia para evitar ChainAssignmentError
                df_temp = df.copy()

                # Normaliza os nomes das colunas para facilitar o mapeamento
                df_temp.columns = [col.strip().upper() for col in df_temp.columns]

                # Renomeia as colunas do DataFrame com base no mapeamento
                df_renamed = pd.DataFrame()
                for new_name, possible_names in column_mapping.items():
                    found_col = None
                    for old_name in possible_names:
                        # Busca por nomes de coluna que contenham a palavra-chave principal
                        if old_name.upper().strip() in df_temp.columns:
                            found_col = old_name.upper().strip()
                            break
                    
                    if found_col:
                        df_renamed[new_name] = df_temp[found_col]
                    else:
                        st.warning(f"Aviso: Coluna essencial '{new_name}' não foi encontrada. O processamento pode estar incompleto.")
                        df_renamed[new_name] = np.nan
                
                df = df_renamed

                # Garante que as colunas de data e hora estão no formato correto
                df['DATA ABASTECIMENTO'] = pd.to_datetime(df['DATA ABASTECIMENTO'], errors='coerce').dt.date
                df['HORÁRIO'] = pd.to_datetime(df['HORÁRIO'], errors='coerce').dt.time
                
                # Mapeamento dos valores numéricos para strings
                df['TIPO DE ABASTECIMENTO'] = df['TIPO DE ABASTECIMENTO'].astype(str).replace({'0': 'DIESEL', '1': 'ARLA', 'nan': np.nan})

                # Converte outras colunas para o tipo numérico e remove linhas com valores faltantes
                df['KM'] = pd.to_numeric(df['KM'], errors='coerce')
                df['LITROS'] = pd.to_numeric(df['LITROS'], errors='coerce')
                df.dropna(subset=['DATA ABASTECIMENTO', 'KM', 'LITROS'], inplace=True)
                
                # Define as colunas de saída
                colunas_saida = [
                    'DATA ABASTECIMENTO', 'HORÁRIO', 'TIPO DE ABASTECIMENTO', 
                    'PLACA', 'KM', 'ALERTA KM', 'MOTORISTA', 'LITROS', 'Média de litros por KM'
                ]
                
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
            if df.empty or len(df.columns) < 28:
                st.error("A planilha não contém o número mínimo de colunas esperado para este script.")
                return pd.DataFrame()

            for index, row in df.iterrows():
                # Verificação de segurança para garantir que 'row' é um Series.
                if not isinstance(row, pd.Series):
                    st.warning(f"Aviso: A linha {index} não é um Series e foi ignorada.")
                    continue
                
                # Verificação de segurança para o tamanho da linha
                if len(row) < 28:
                    st.warning(f"Aviso: A linha {index} tem menos de 28 colunas e será ignorada.")
                    continue

                try:
                    data_value = row.iloc[0]
                    sv_value = row.iloc[1]
                    
                    vd_consolidated_parts = [str(row.iloc[col_idx]).strip() for col_idx in range(2, min(5, len(row))) if pd.notna(row.iloc[col_idx])]
                    vd_final = ' | '.join(vd_consolidated_parts) if vd_consolidated_parts else None
                    
                    para_value = row.iloc[27]

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
                except IndexError:
                    st.error(f"Erro: Estrutura de coluna inesperada na linha {index}. A linha será ignorada.")
                    continue

            final_df = pd.DataFrame(processed_records)
            return final_df

        uploaded_file_1 = st.file_uploader("Envie o arquivo para 'Troca de Canal' (.xlsx)", type=["xlsx"])

        if uploaded_file_1 is not None:
            try:
                df_forms = pd.read_excel(uploaded_file_1)
                st.subheader("📄 Dados Originais (Troca de Canal)")
                st.dataframe(df_forms.head())
                
                final_df_forms = transform_google_forms_data(df_forms)
                
                if not final_df_forms.empty:
                    output = io.Bytes-
