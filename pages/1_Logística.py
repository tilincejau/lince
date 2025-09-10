import streamlit as st
import pandas as pd
import re
import io
import numpy as np
from datetime import datetime, timedelta
import PyPDF2
from openpyxl import load_workbook
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter

# Imports do Firebase Admin SDK
import firebase_admin
from firebase_admin import credentials, firestore
import json

# Verificação de login. Se não estiver logado, exibe uma mensagem e para o script.
if not st.session_state.get('is_logged_in'):
    st.warning("Você precisa estar logado para acessar esta página.")
    st.stop()

# --- Conexão e Funções do Firestore ---
# Inicializa o Firebase se ainda não foi feito.
# As credenciais são carregadas do `st.secrets`.
@st.cache_resource
def get_db():
    try:
        cred_dict = dict(st.secrets["firebase"])
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        return firestore.client()
    except Exception as e:
        st.error(f"Erro ao conectar com Firebase: {e}")
        st.stop()

db = get_db()

def save_vasilhames_to_db(df):
    """Salva o DataFrame de vasilhames no Firestore."""
    st.info("Salvando dados no Firestore...")
    collection_ref = db.collection("vasilhames")
    for _, row in df.iterrows():
        row_dict = row.to_dict()
        for key, value in row_dict.items():
            if pd.isna(value):
                row_dict[key] = None
        doc_ref = collection_ref.document()
        doc_ref.set(row_dict)
    st.success("Dados de vasilhames salvos com sucesso!")

def load_vasilhames_from_db():
    """Carrega o DataFrame de vasilhames do Firestore."""
    st.info("Carregando dados do Firestore...")
    collection_ref = db.collection("vasilhames")
    docs = collection_ref.stream()
    data = [doc.to_dict() for doc in docs]
    if data:
        df = pd.DataFrame(data)
        st.success("Dados carregados com sucesso!")
        return df
    else:
        st.warning("Nenhum dado encontrado no banco de dados.")
        return pd.DataFrame()


st.title("Setor de Logística")
st.markdown("Bem-vindo(a) ao setor de Logística. Abaixo estão os scripts disponíveis para análise.")

script_choice = st.selectbox(
    "Selecione um script para executar:",
    ("Acurácia", "Validade", "Vasilhames")
)

st.write("---")

if script_choice == "Acurácia":
    st.subheader("📈 Acurácia de Estoque")
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
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        except Exception as e:
            st.error(f"Ocorreu um erro no script de Acurácia: {e}")

elif script_choice == "Validade":
    st.subheader("🛒 Controle de Validade")
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
    st.subheader("💧 Controle de Vasilhames")
    st.markdown("Este script consolida dados de vasilhames de diferentes fontes (Excel, TXT, PDF) e gera um relatório unificado.")
    
    uploaded_txt_file = st.file_uploader("Envie o arquivo TXT de empréstimos (Ex: ESTOQUE0102.TXT)", type=["txt"])
    uploaded_excel_contagem = st.file_uploader("Envie o arquivo Excel de contagem (Ex: Contagem Vasilhames.xlsx)", type=["xlsx"])
    uploaded_pdf_files = st.file_uploader("Envie os arquivos PDF de fábrica", type=["pdf"], accept_multiple_files=True)
    
    if uploaded_txt_file is not None and uploaded_excel_contagem is not None:
        try:
            st.info("Processando arquivos. Por favor, aguarde...")
            
            # Funções de processamento dos arquivos
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
            
            # --- Carregamento dos dados ---
            df_txt_qty, effective_date_str = process_txt_file_st(uploaded_txt_file)
            if df_txt_qty is None:
                st.stop()
            df_txt_qty['Dia'] = effective_date_str
            df_contagem = pd.read_excel(uploaded_excel_contagem, sheet_name='Respostas ao formulário 1')
            df_contagem['Carimbo de data/hora'] = pd.to_datetime(df_contagem['Carimbo de data/hora'])
            df_historical_excel = df_contagem.copy()
            df_historical_excel['Dia'] = df_historical_excel['Carimbo de data/hora'].dt.strftime('%d/%m')
            df_historical_excel.rename(columns={'Qual vasilhame ?': 'Vasilhame', 'Total': 'Contagem'}, inplace=True)
            df_excel_daily_counts = df_historical_excel.groupby(['Vasilhame', 'Dia'])['Contagem'].sum().reset_index()

            all_pdf_data = []
            if uploaded_pdf_files:
                pdf_material_code_to_vasilhame_map = {'000000000000215442': '587-002 - CAIXA PLASTICA HEINEKEN 600ML', '000000000000215208': '587-002 - CAIXA PLASTICA HEINEKEN 600ML', '000000000000381411': '591-002 - CAIXA PLASTICA HEINEKEN 330ML', '000000000000107380': '555-001 - CAIXA PLASTICA 1L', '000000000000152598': '546-004 - CAIXA PLASTICA 24UN 300ML', '000000000000000470': '550-001 - CAIXA PLASTICA 600ML'}
                for pdf_file in uploaded_pdf_files:
                    df_pdf_current = process_pdf_content(pdf_file, pdf_material_code_to_vasilhame_map)
                    if not df_pdf_current.empty:
                        all_pdf_data.append(df_pdf_current)
            
            if all_pdf_data:
                df_all_processed_pdf_data = pd.concat(all_pdf_data, ignore_index=True)
                df_all_processed_pdf_data = df_all_processed_pdf_data.groupby(['Vasilhame', 'Dia']).sum().reset_index()
            else:
                df_all_processed_pdf_data = pd.DataFrame(columns=['Vasilhame', 'Dia', 'Credito Ponta Grossa (0328)', 'Debito Ponta Grossa (0328)', 'Credito Araraquara (0336)', 'Debito Araraquara (0336)', 'Credito Itu (0002)', 'Debito Itu (0002)'])
            
            # Consolidação
            df_master_combinations = pd.concat([
                df_excel_daily_counts[['Vasilhame', 'Dia']],
                df_txt_qty[['Vasilhame', 'Dia']],
                df_all_processed_pdf_data[['Vasilhame', 'Dia']]
            ]).drop_duplicates().reset_index(drop=True)
            
            df_final = pd.merge(df_master_combinations, df_excel_daily_counts, on=['Vasilhame', 'Dia'], how='left')
            df_final = pd.merge(df_final, df_txt_qty, on=['Vasilhame', 'Dia'], how='left')
            df_final = pd.merge(df_final, df_all_processed_pdf_data, on=['Vasilhame', 'Dia'], how='left')
            
            # Cálculo final
            df_final['Contagem'] = pd.to_numeric(df_final['Contagem'], errors='coerce').fillna(0)
            df_final['Qtd. emprestimo'] = pd.to_numeric(df_final['Qtd. emprestimo'], errors='coerce').fillna(0)
            df_final['Total Revenda'] = df_final['Qtd. emprestimo'] + df_final['Contagem'] + df_final['Credito Ponta Grossa (0328)'].fillna(0) + df_final['Credito Araraquara (0336)'].fillna(0) + df_final['Credito Itu (0002)'].fillna(0) - (df_final['Debito Ponta Grossa (0328)'].fillna(0) + df_final['Debito Araraquara (0336)'].fillna(0) + df_final['Debito Itu (0002)'].fillna(0))
            df_final['Diferença'] = df_final.groupby('Vasilhame')['Total Revenda'].diff()

            st.subheader("✅ Tabela Consolidada de Vasilhames")
            st.dataframe(df_final)

            # --- Adicionado: Botão para Salvar no Firestore ---
            if st.button("Salvar no Banco de Dados"):
                save_vasilhames_to_db(df_final)
            
            # --- Adicionado: Botão para Carregar do Firestore ---
            if st.button("Carregar do Banco de Dados"):
                df_from_db = load_vasilhames_from_db()
                if not df_from_db.empty:
                    st.subheader("Dados Carregados do Firestore")
                    st.dataframe(df_from_db)

            # Download
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
