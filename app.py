import streamlit as st
import pandas as pd
import re
import io
import numpy as np
from datetime import datetime
import PyPDF2
from openpyxl import load_workbook
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter
import xlsxwriter

# --- BIBLIOTECAS PARA GOOGLE SHEETS ---
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread_dataframe import set_with_dataframe, get_as_dataframe

# ====================================================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ====================================================================
st.set_page_config(page_title="Lince Distribuidora - Nuvem", page_icon="☁️", layout="centered")

st.markdown("""
<style>
    .stApp { background-color: #f0f2f6; } 
    div.stButton > button:first-child { background-color: #007bff; color: white; border-radius: 5px; font-weight: bold;} 
    .stTitle { text-align: center; color: #004d99; font-family: 'Arial', sans-serif;}
    h1, h2, h3 { color: #004d99; }
</style>
""", unsafe_allow_html=True)

# ====================================================================
# 2. CONFIGURAÇÃO E CONSTANTES GLOBAIS
# ====================================================================

# ID DA SUA PLANILHA
SPREADSHEET_KEY = '1uFr9yhylYj7dINsDAr-6tECgNDxc21t9QhmC0cxBjhY'

NAME_540_001 = '540-001 - GARRAFA 600ML' 
NAME_550_001 = '550-001 - CAIXA PLASTICA 600ML'

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
# 3. CONEXÃO GOOGLE SHEETS
# ====================================================================

@st.cache_resource
def connect_to_gsheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        else:
            creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_KEY)
        return sheet
    except Exception as e:
        st.error(f"Erro na autenticação do Google: {e}")
        return None

def load_from_gsheets(sheet, tab_name):
    """Lê uma aba da planilha de forma segura."""
    try:
        try:
            worksheet = sheet.worksheet(tab_name)
        except gspread.WorksheetNotFound:
            return pd.DataFrame() 

        # Lê como string para evitar erros de tipo
        df = get_as_dataframe(worksheet, evaluate_formulas=True, dtype=str)
        df = df.dropna(how='all').dropna(axis=1, how='all')
        
        if df.empty: return pd.DataFrame()

        # Limpeza de colunas
        df.columns = df.columns.str.strip()
        
        # Conversão numérica forçada
        cols_ignoradas = ['Vasilhame', 'Dia', 'DataCompleta']
        for col in df.columns:
            if col not in cols_ignoradas:
                df[col] = df[col].astype(str).str.replace(',', '.')
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        return df
    except Exception as e:
        st.error(f"Erro crítico ao ler aba {tab_name}: {e}")
        return pd.DataFrame()

def save_to_gsheets(sheet, tab_name, df):
    try:
        try:
            worksheet = sheet.worksheet(tab_name)
            worksheet.clear()
        except gspread.WorksheetNotFound:
            worksheet = sheet.add_worksheet(title=tab_name, rows="1000", cols="20")
        
        df_export = df.copy()
        # Converte datas para string para o Sheets não bugar
        for col in df_export.select_dtypes(include=['datetime64[ns]']).columns:
             df_export[col] = df_export[col].astype(str).replace('NaT', '')
        
        set_with_dataframe(worksheet, df_export)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar na aba {tab_name}: {e}")
        return False

# ====================================================================
# 4. SISTEMA DE LOGIN E PÁGINA
# ====================================================================

def login_form():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h2 style='text-align: center;'>Lince Distribuidora</h2>", unsafe_allow_html=True)
        st.markdown("---")
        with st.form("login_form"):
            username = st.text_input("Usuário")
            password = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar", use_container_width=True):
                if username in st.session_state.LOGIN_INFO and st.session_state.LOGIN_INFO[username] == password:
                    st.session_state['is_logged_in'] = True
                    st.session_state['username'] = username
                    st.session_state['current_page'] = 'home'
                    st.rerun()
                else:
                    st.error("Dados incorretos.")

def main_page():
    st.markdown(f"<h3 style='text-align: center;'>Bem-vindo(a), {st.session_state['username']}!</h3>", unsafe_allow_html=True)
    st.markdown("---")
    c1, c2 = st.columns(2)
    if c1.button("🚛 Logística", use_container_width=True):
        st.session_state['current_page'] = 'logistics'; st.rerun()
    if c2.button("📈 Comercial", use_container_width=True):
        st.session_state['current_page'] = 'commercial'; st.rerun()
    st.markdown("---")
    if st.button("Sair"):
        st.session_state['is_logged_in'] = False; st.rerun()

# ====================================================================
# 5. LOGÍSTICA
# ====================================================================
def logistics_page():
    st.title("Setor de Logística")
    if st.button("⬅️ Voltar"): st.session_state['current_page'] = 'home'; st.rerun()
    st.markdown("---")
    
    script_choice = st.selectbox("Ferramenta:", ("Selecione...", "Acurácia", "Validade", "Vasilhames", "Abastecimento"))
    st.write("---")

    # --- FUNÇÃO AUXILIAR DE DATA BLINDADA ---
    def padronizar_data(df, col='Dia'):
        """Garante que a data seja YYYY-MM-DD sem inverter dia/mês."""
        if df.empty or col not in df.columns: return df
        
        # 1. Converte para string e limpa
        s = df[col].astype(str).str.strip().str.split(' ').str[0]
        
        # 2. Se já for ISO (2025-11-05), converte direto (sem dayfirst)
        mask_iso = s.str.match(r'^\d{4}-\d{2}-\d{2}')
        dates_iso = pd.to_datetime(s[mask_iso], format='%Y-%m-%d', errors='coerce')
        
        # 3. Se for BR (05/11/2025), converte com dayfirst=True
        dates_br = pd.to_datetime(s[~mask_iso], dayfirst=True, errors='coerce')
        
        # 4. Combina e formata
        combined = dates_iso.reindex(s.index).combine_first(dates_br)
        df[col] = combined.dt.strftime('%Y-%m-%d')
        return df

    # ... (Blocos Acurácia e Validade podem ser copiados do anterior se necessário) ...

    if script_choice == "Vasilhames":
        st.subheader("Controle de Vasilhames (Nuvem ☁️)")
        sheet_client = connect_to_gsheets()
        if not sheet_client: st.stop()

        with st.expander("🗑️ Área de Perigo (Limpar Tudo)"):
            if st.button("Limpar Histórico da Nuvem", type="primary"):
                for tab in ['txt_data', 'pdf_data', 'vendas_data', 'excel_data', 'CONSOLIDADO_GERAL']:
                    try: sheet_client.worksheet(tab).clear()
                    except: pass
                st.success("Tudo limpo! Agora suba os arquivos novamente para corrigir as datas."); st.rerun()

        # --- PROCESSADORES DE ARQUIVO ---
        def process_txt(file):
            content = file.getvalue().decode('latin1')
            match = re.search(r'ESTOQUE(\d{4})\.TXT', file.name)
            if not match: return None, None
            # Fixa formato brasileiro na leitura do nome do arquivo
            dt = datetime.strptime(f"{match.group(1)[:2]}/{match.group(1)[2:]}/{datetime.now().year}", '%d/%m/%Y')
            data_str = dt.strftime('%Y-%m-%d')
            
            parsed = []
            codes = {
                '563-008': '563-008 - BARRIL INOX 30L', '564-009': '564-009 - BARRIL INOX 50L', '591-002': '591-002 - CAIXA PLASTICA HEINEKEN 330ML', 
                '587-002': '587-002 - CAIXA PLASTICA HEINEKEN 600ML', '550-001': '550-001 - CAIXA PLASTICA 600ML', '555-001': '555-001 - CAIXA PLASTICA 1L', 
                '546-004': '546-004 - CAIXA PLASTICA 24UN 300ML', '565-002': '565-002 - CILINDRO CO2', 
                '546-001': CRATE_TO_BOTTLE_MAP['546-004 - CAIXA PLASTICA 24UN 300ML'],
                '540-001': NAME_540_001, '541-002': CRATE_TO_BOTTLE_MAP['555-001 - CAIXA PLASTICA 1L'],
                '586-001': CRATE_TO_BOTTLE_MAP['587-002 - CAIXA PLASTICA HEINEKEN 600ML'], '593-001': CRATE_TO_BOTTLE_MAP['591-002 - CAIXA PLASTICA HEINEKEN 330ML'],
                '550-012': '550-001 - CAIXA PLASTICA 600ML', '803-025': '550-001 - CAIXA PLASTICA 600ML', '803-039': '550-001 - CAIXA PLASTICA 600ML' 
            }
            lines = content.splitlines(); curr = None
            for line in lines:
                line = line.strip()
                if not line or '---' in line: continue
                cm = re.search(r'^(\d{3}-\d{3})', line)
                if cm:
                    curr = cm.group(1)
                    qm = re.search(r'\s+([\d\.]+)\s+[\d\.]+,\d+', line) or re.search(r'\s+([\d\.]+)$', line)
                    if qm and curr in codes: parsed.append({'PRODUTO_CODE': curr, 'Qtd': int(qm.group(1).replace('.', ''))}); curr = None
                elif curr:
                    qm = re.search(r'([\d\.]+)\s+[\d\.]+,\d+', line)
                    if qm and curr in codes: parsed.append({'PRODUTO_CODE': curr, 'Qtd': int(qm.group(1).replace('.', ''))}); curr = None
            
            if not parsed: return None, data_str
            df = pd.DataFrame(parsed)
            df['Vasilhame'] = df['PRODUTO_CODE'].map(codes)
            return df.groupby('Vasilhame')['Qtd'].sum().reset_index().rename(columns={'Qtd': 'Qtd_emprestimo'}), data_str

        def process_vendas(file):
            content = file.getvalue().decode('latin1')
            match = re.search(r'VENDA(\d{4})\.TXT', file.name)
            if not match: return None
            dt = datetime.strptime(f"{match.group(1)[:2]}/{match.group(1)[2:]}/{datetime.now().year}", '%d/%m/%Y')
            data_str = dt.strftime('%Y-%m-%d')
            
            sales_map = {'540-001': NAME_540_001, '541-002': '541-002 - GARRAFA 1L', '586-001': '586-001 - GARRAFA HEINEKEN 600ML', '555-001': '555-001 - CAIXA PLASTICA 1L'}
            parsed = []
            for line in content.splitlines():
                match = re.search(r'^(\d{6}).*?([\d\.]+)\s*\/', line)
                if match:
                    code = f"{match.group(1)[:3]}-{match.group(1)[3:]}"
                    if code in sales_map: parsed.append({'Vasilhame': sales_map[code], 'Vendas': int(match.group(2).replace('.', '')), 'Dia': data_str})
            return pd.DataFrame(parsed) if parsed else None

        def process_pdf(file, product_map):
            content = ""
            try:
                reader = PyPDF2.PdfReader(io.BytesIO(file.getvalue()))
                for page in reader.pages: content += page.extract_text()
            except: return None

            match = re.search(r'([a-zA-Z\s]+)\s+(\d{2}-\d{2}-\d{4})\.pdf', file.name)
            if not match: return None
            
            src = match.group(1).strip().upper()
            dt = datetime.strptime(match.group(2), '%d-%m-%Y').strftime('%Y-%m-%d')
            
            col_map = {'PONTA GROSSA': 'Ponta Grossa (0328)', 'ARARAQUARA': 'Araraquara (0336)', 'ITU': 'Itu (0002)'}
            suffix = col_map.get(src, src)
            
            parsed = []
            for m in re.finditer(r'^\s*"?(\d{15,})[^"\n]*?"?.*?"?([-+]?[\d.,]+)"?\s*$', content, re.MULTILINE):
                code = m.group(1).strip()
                val = float(m.group(2).replace('.', '').replace(',', '.'))
                if code in product_map:
                    cred = abs(val) if val < 0 else 0
                    deb = val if val >= 0 else 0
                    parsed.append({'Vasilhame': product_map[code], 'Dia': dt, f'Credito {suffix}': cred, f'Debito {suffix}': deb})
            
            if not parsed: return None
            df = pd.DataFrame(parsed)
            cols = [c for c in df.columns if 'Credito' in c or 'Debito' in c]
            return df.groupby(['Vasilhame', 'Dia'], as_index=False)[cols].sum()

        # --- INTERFACE DE UPLOAD ---
        up_txt = st.file_uploader("TXT Empréstimo", type=["txt"], accept_multiple_files=True)
        up_vendas = st.file_uploader("TXT Vendas", type=["txt"], accept_multiple_files=True)
        up_excel = st.file_uploader("Excel Contagem", type=["xlsx"])
        up_pdf = st.file_uploader("PDFs", type=["pdf"], accept_multiple_files=True)

        if st.button("Processar e Salvar"):
            if up_txt and up_excel:
                st.info("Iniciando processamento...")
                
                # 1. CARREGAR HISTÓRICO (Com Padronização de Data Blindada)
                try:
                    old_txt = padronizar_data(load_from_gsheets(sheet_client, 'txt_data'))
                    old_vendas = padronizar_data(load_from_gsheets(sheet_client, 'vendas_data'))
                    old_pdf = padronizar_data(load_from_gsheets(sheet_client, 'pdf_data'))
                    old_excel = padronizar_data(load_from_gsheets(sheet_client, 'excel_data'))
                    st.write(f"📊 Linhas recuperadas: TXT({len(old_txt)}) PDF({len(old_pdf)}) Excel({len(old_excel)})")
                except Exception as e: st.error(f"Erro fatal: {e}"); st.stop()

                # 2. PROCESSAR TXT
                new_txt_list = []
                for f in up_txt:
                    df, dia = process_txt(f)
                    if df is not None: df['Dia'] = dia; new_txt_list.append(df)
                
                final_txt = old_txt
                if new_txt_list:
                    new_txt_df = pd.concat(new_txt_list)
                    for c in new_txt_df.columns: 
                        if c not in final_txt.columns: final_txt[c] = 0
                    for c in final_txt.columns: 
                        if c not in new_txt_df.columns: new_txt_df[c] = 0
                    final_txt = pd.concat([final_txt, new_txt_df]).drop_duplicates(subset=['Vasilhame', 'Dia'], keep='last')
                    save_to_gsheets(sheet_client, 'txt_data', final_txt)

                # 3. PROCESSAR VENDAS
                final_vendas = old_vendas
                if up_vendas:
                    nv_list = []
                    for f in up_vendas:
                        df = process_vendas(f)
                        if df is not None: nv_list.append(df)
                    if nv_list:
                        new_v_df = pd.concat(nv_list)
                        for c in new_v_df.columns: 
                            if c not in final_vendas.columns: final_vendas[c] = 0
                        for c in final_vendas.columns: 
                            if c not in new_v_df.columns: new_v_df[c] = 0
                        final_vendas = pd.concat([final_vendas, new_v_df]).drop_duplicates(subset=['Vasilhame', 'Dia'], keep='last')
                        save_to_gsheets(sheet_client, 'vendas_data', final_vendas)

                # 4. PROCESSAR PDF
                final_pdf = old_pdf
                if up_pdf:
                    pdf_map = {
                        '000000000000215442': '587-002 - CAIXA PLASTICA HEINEKEN 600ML', '000000000000215208': '587-002 - CAIXA PLASTICA HEINEKEN 600ML', 
                        '000000000000381411': '591-002 - CAIXA PLASTICA HEINEKEN 330ML', '000000000000107380': '555-001 - CAIXA PLASTICA 1L', 
                        '000000000000152598': '546-004 - CAIXA PLASTICA 24UN 300ML', '000000000000000470': '550-001 - CAIXA PLASTICA 600ML',
                        '000000000000048261': '563-008 - BARRIL INOX 30L', '000000000000048272': '564-009 - BARRIL INOX 50L',
                        '000000000000185039': CRATE_TO_BOTTLE_MAP['546-004 - CAIXA PLASTICA 24UN 300ML'], '000000000000002496': NAME_540_001, 
                        '000000000000107523': CRATE_TO_BOTTLE_MAP['555-001 - CAIXA PLASTICA 1L'], '000000000000152592': CRATE_TO_BOTTLE_MAP['546-004 - CAIXA PLASTICA 24UN 300ML'],
                        '000000000000215443': CRATE_TO_BOTTLE_MAP['587-002 - CAIXA PLASTICA HEINEKEN 600ML'], '000000000000381408': CRATE_TO_BOTTLE_MAP['591-002 - CAIXA PLASTICA HEINEKEN 330ML'],
                        '000000000000152597': CRATE_TO_BOTTLE_MAP['546-004 - CAIXA PLASTICA 24UN 300ML'], '000000000000000471': NAME_540_001,      
                        '000000000000107522': CRATE_TO_BOTTLE_MAP['555-001 - CAIXA PLASTICA 1L'], '000000000000215209': CRATE_TO_BOTTLE_MAP['587-002 - CAIXA PLASTICA HEINEKEN 600ML'], 
                        '000000000000381409': CRATE_TO_BOTTLE_MAP['591-002 - CAIXA PLASTICA HEINEKEN 330ML']  
                    }
                    np_list = []
                    for f in up_pdf:
                        df = process_pdf(f, pdf_map)
                        if df is not None: np_list.append(df)
                    
                    if np_list:
                        new_p_df = pd.concat(np_list).fillna(0)
                        for c in new_p_df.columns: 
                            if c not in final_pdf.columns: final_pdf[c] = 0
                        for c in final_pdf.columns: 
                            if c not in new_p_df.columns: new_p_df[c] = 0
                        final_pdf = pd.concat([final_pdf, new_p_df]).drop_duplicates(subset=['Vasilhame', 'Dia'], keep='last')
                        save_to_gsheets(sheet_client, 'pdf_data', final_pdf)

                # 5. PROCESSAR EXCEL
                df_contagem = pd.read_excel(up_excel, sheet_name='Respostas ao formulário 1')
                df_contagem['Carimbo de data/hora'] = pd.to_datetime(df_contagem['Carimbo de data/hora'])
                df_contagem['Dia'] = df_contagem['Carimbo de data/hora'].dt.strftime('%Y-%m-%d')

                def map_row(row):
                    name = str(row['Qual vasilhame ?']).upper()
                    t_crate = row['Qual vasilhame ?']; t_bottle = None; factor = 1
                    
                    if '063-005' in name: t_bottle = '546-001 - GARRAFA 300ML'; return None, t_bottle, 1
                    if '540-001' in name: t_bottle = NAME_540_001; return None, t_bottle, 1
                    if '541-002' in name: t_bottle = '541-002 - GARRAFA 1L'; return None, t_bottle, 1
                    if '586-001' in name: t_bottle = '586-001 - GARRAFA HEINEKEN 600ML'; return None, t_bottle, 1
                    if '593-001' in name: t_bottle = '593-001 - GARRAFA HEINEKEN 330ML'; return None, t_bottle, 1

                    if '550-012' in name or 'EISENBAHN' in name or '550-001' in name or 'MISTA' in name: t_crate = '550-001 - CAIXA PLASTICA 600ML'
                    elif '587-002' in name: t_crate = '587-002 - CAIXA PLASTICA HEINEKEN 600ML'
                    elif '546-004' in name: t_crate = '546-004 - CAIXA PLASTICA 24UN 300ML'
                    elif '591-002' in name: t_crate = '591-002 - CAIXA PLASTICA HEINEKEN 330ML'
                    elif '555-001' in name: t_crate = '555-001 - CAIXA PLASTICA 1L'

                    if t_crate in CRATE_TO_BOTTLE_MAP:
                        t_bottle = CRATE_TO_BOTTLE_MAP[t_crate]
                        factor = FACTORS.get(t_crate, 1)
                    return t_crate, t_bottle, factor

                def calc_assets(row):
                    tc, tb, f = map_row(row)
                    qc = float(row.get('Quantidade estoque cheias?', 0) or 0)
                    qv = float(row.get('Quantidade estoque vazias?', 0) or 0)
                    trc = float(row.get('Em transito cheias (Entrega)?', 0) or 0)
                    trv = float(row.get('Em transito vazias (Entrega)?', 0) or 0)
                    car = float(row.get('Em transito (carreta)?', 0) or 0)
                    
                    g_qc=0; g_qv=0; g_trc=0; g_trv=0; g_car=0
                    c_qc=0; c_qv=0; c_trc=0; c_trv=0; c_car=0
                    
                    if tc is None and tb is not None:
                        g_qc=qc; g_qv=qv; g_trc=trc; g_trv=trv; g_car=car
                    elif tb:
                        g_qc=qc*f; g_trc=trc*f; g_car=car*f
                        c_qc=qc; c_qv=qv; c_trc=trc; c_trv=trv; c_car=car
                    else:
                        c_qc=qc; c_qv=qv; c_trc=trc; c_trv=trv; c_car=car
                        
                    return pd.Series([tc, tb, g_qc, g_qv, g_trc, g_trv, g_car, c_qc, c_qv, c_trc, c_trv, c_car],
                                     index=['TC', 'TB', 'G_QC', 'G_QV', 'G_TRC', 'G_TRV', 'G_CAR', 'C_QC', 'C_QV', 'C_TRC', 'C_TRV', 'C_CAR'])

                df_contagem[['TC', 'TB', 'G_QC', 'G_QV', 'G_TRC', 'G_TRV', 'G_CAR', 'C_QC', 'C_QV', 'C_TRC', 'C_TRV', 'C_CAR']] = df_contagem.apply(calc_assets, axis=1)

                agg_g = {'G_QC':'sum', 'G_QV':'sum', 'G_TRC':'sum', 'G_TRV':'sum', 'G_CAR':'sum'}
                df_g = df_contagem.dropna(subset=['TB']).groupby(['TB', 'Dia']).agg(agg_g).reset_index()
                df_g.rename(columns={'TB': 'Vasilhame', 'G_QC': 'Quantidade estoque cheias', 'G_QV': 'Quantidade estoque vazias', 'G_TRC': 'Em transito cheias (Entrega)', 'G_TRV': 'Em transito vazias (Entrega)', 'G_CAR': 'Em transito (carreta)'}, inplace=True)
                
                agg_c = {'C_QC':'sum', 'C_QV':'sum', 'C_TRC':'sum', 'C_TRV':'sum', 'C_CAR':'sum'}
                df_c = df_contagem.dropna(subset=['TC']).groupby(['TC', 'Dia']).agg(agg_c).reset_index()
                df_c.rename(columns={'TC': 'Vasilhame', 'C_QC': 'Quantidade estoque cheias', 'C_QV': 'Quantidade estoque vazias', 'C_TRC': 'Em transito cheias (Entrega)', 'C_TRV': 'Em transito vazias (Entrega)', 'C_CAR': 'Em transito (carreta)'}, inplace=True)
                
                new_excel_df = pd.concat([df_g, df_c])
                new_excel_df['Contagem Cheias'] = new_excel_df['Quantidade estoque cheias'] + new_excel_df['Em transito cheias (Entrega)'] + new_excel_df['Em transito (carreta)']
                new_excel_df['Contagem Vazias'] = new_excel_df['Quantidade estoque vazias'] + new_excel_df['Em transito vazias (Entrega)']

                final_excel = old_excel
                if not new_excel_df.empty:
                    for c in new_excel_df.columns: 
                        if c not in final_excel.columns: final_excel[c] = 0
                    for c in final_excel.columns: 
                        if c not in new_excel_df.columns: new_excel_df[c] = 0
                    final_excel = pd.concat([final_excel, new_excel_df]).drop_duplicates(subset=['Vasilhame', 'Dia'], keep='last')
                    save_to_gsheets(sheet_client, 'excel_data', final_excel)

                # 6. CONSOLIDAÇÃO FINAL
                skeleton_dates = set(final_excel['Dia'].unique()) | set(final_txt['Dia'].unique())
                if not skeleton_dates: skeleton_dates.add(datetime.now().strftime('%Y-%m-%d'))
                
                skeleton = []
                for p in list(FACTORS.keys()) + list(CRATE_TO_BOTTLE_MAP.values()):
                    for d in skeleton_dates: skeleton.append({'Vasilhame': p, 'Dia': d})
                df_skel = pd.DataFrame(skeleton)

                # Merge Master
                df_final = pd.merge(df_skel, final_excel, on=['Vasilhame', 'Dia'], how='left')
                df_final = pd.merge(df_final, final_txt, on=['Vasilhame', 'Dia'], how='left')
                df_final = pd.merge(df_final, final_pdf, on=['Vasilhame', 'Dia'], how='left')
                df_final = pd.merge(df_final, final_vendas, on=['Vasilhame', 'Dia'], how='left')
                
                cols_num = ['Contagem Cheias', 'Contagem Vazias', 'Qtd_emprestimo', 'Vendas']
                for c in df_final.columns:
                    if c in cols_num or 'Credito' in c or 'Debito' in c or 'Quantidade' in c or 'transito' in c:
                        df_final[c] = pd.to_numeric(df_final[c], errors='coerce').fillna(0)

                df_final['Total Revenda'] = (
                    df_final['Qtd_emprestimo'] + 
                    df_final['Contagem Cheias'] + 
                    df_final['Contagem Vazias'] + 
                    df_final.filter(like='Credito').sum(axis=1) - 
                    df_final.filter(like='Debito').sum(axis=1) + 
                    df_final.get('Vendas', 0)
                )

                def calc_diff(g):
                    base_dt = '2025-11-05'
                    try:
                        base_val = g[g['Dia'] >= base_dt].sort_values('Dia').iloc[0]['Total Revenda']
                    except: base_val = 0
                    
                    g['Diferença'] = 0.0
                    mask = g['Dia'] >= '2025-11-10'
                    if base_val != 0:
                        g.loc[mask, 'Diferença'] = g.loc[mask, 'Total Revenda'] - base_val
                    return g

                df_final = df_final.groupby('Vasilhame', group_keys=False).apply(calc_diff)
                
                cols_order = ['Vasilhame', 'Dia', 'Total Revenda', 'Diferença'] + [c for c in df_final.columns if c not in ['Vasilhame', 'Dia', 'Total Revenda', 'Diferença']]
                df_final = df_final[cols_order].sort_values(['Vasilhame', 'Dia'])
                
                st.success("✅ Dados processados e salvos!")
                st.dataframe(df_final)
                save_to_gsheets(sheet_client, 'CONSOLIDADO_GERAL', df_final)

                out = io.BytesIO()
                with pd.ExcelWriter(out, engine='xlsxwriter') as w:
                    df_final.to_excel(w, sheet_name='GERAL', index=False)
                st.download_button("📥 Baixar Planilha Consolidada", out.getvalue(), "Consolidado.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

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

# ====================================================================
# 6. SETOR COMERCIAL
# ====================================================================
def commercial_page():
    st.title("Setor Comercial")
    
    col_voltar, col_vazio = st.columns([1, 5])
    with col_voltar:
        if st.button("⬅️ Voltar"):
            st.session_state['current_page'] = 'home'
            st.rerun()

    st.markdown("---")
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
                        pdv_info_raw = re.sub(r'\s*\([^)]*\)\s*$', '', cell_content).strip()
                        pdv_info_val = re.sub(r'^\s*(?:\b\w+\s+)?\d+\s*[\|-]\s*', '', pdv_info_raw, 1).strip() if pdv_info_raw else None
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

# ====================================================================
# 7. EXECUÇÃO PRINCIPAL
# ====================================================================

if 'is_logged_in' not in st.session_state: st.session_state['is_logged_in'] = False
if 'current_page' not in st.session_state: st.session_state['current_page'] = 'login'
if 'LOGIN_INFO' not in st.session_state: st.session_state['LOGIN_INFO'] = {"admin": "Joao789", "amanda": "12345", "marcia": "54321"}

if st.session_state.get('is_logged_in', False):
    page_functions = {'home': main_page, 'logistics': logistics_page, 'commercial': commercial_page}
    page_functions.get(st.session_state.get('current_page', 'home'), main_page)()
else:
    login_form()
