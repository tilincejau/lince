import streamlit as st
import base64

st.set_page_config(
    page_title="Lince Distribuidora de Bebidas - Login",
    page_icon="🏠",
    layout="centered"
)

# Inicializa chaves importantes do session_state (evita KeyError)
if 'is_logged_in' not in st.session_state:
    st.session_state['is_logged_in'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = ""
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = 'login'  # 'login' ou 'home'

# CSS personalizado
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
</style>
""", unsafe_allow_html=True)

# Credenciais de login
LOGIN_INFO = {
    "admin": "Joao789",
    "amanda": "12345",
    "marcia": "54321"
}

def login_form():
    """Exibe o formulário de login com um design aprimorado."""
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h2 style='text-align: center; color: #004d99; font-family: \"Arial Black\", sans-serif;'>Lince Distribuidora</h2>", unsafe_allow_html=True)
        st.markdown("---")
        with st.form("login_form", clear_on_submit=False):
            st.markdown("Por favor, insira suas credenciais para continuar.")
            username = st.text_input("Usuário", key="username_input", placeholder="Digite seu nome de usuário")
            password = st.text_input("Senha", type="password", key="password_input", placeholder="Digite sua senha")
            st.markdown("<br>", unsafe_allow_html=True)
            submit_button = st.form_submit_button("Entrar", use_container_width=True)

        if submit_button:
            if username in LOGIN_INFO and LOGIN_INFO[username] == password:
                st.session_state['is_logged_in'] = True
                st.session_state['username'] = username
                st.session_state['current_page'] = 'home'
                st.success("Login realizado com sucesso! Redirecionando...")
                st.balloons()
                st.rerun()   # ✅ corrigido
            else:
                st.error("Usuário ou senha incorretos.")

def logistics_page():
    st.markdown("<h2 style='text-align: center;'>Logística</h2>", unsafe_allow_html=True)
    st.write("Conteúdo da página de Logística.")
    if st.button("Voltar para o Início"):
        st.session_state['current_page'] = 'home'
        st.rerun()   # ✅ corrigido

def commercial_page():
    st.markdown("<h2 style='text-align: center;'>Comercial</h2>", unsafe_allow_html=True)
    st.write("Conteúdo da página de Comercial.")
    if st.button("Voltar para o Início"):
        st.session_state['current_page'] = 'home'
        st.rerun()   # ✅ corrigido

def rh_page():
    st.markdown("<h2 style='text-align: center;'>Recursos Humanos</h2>", unsafe_allow_html=True)
    st.write("Conteúdo da página de Recursos Humanos.")
    if st.button("Voltar para o Início"):
        st.session_state['current_page'] = 'home'
        st.rerun()   # ✅ corrigido

def ti_page():
    st.markdown("<h2 style='text-align: center;'>TI</h2>", unsafe_allow_html=True)
    st.write("Conteúdo da página de TI.")
    if st.button("Voltar para o Início"):
        st.session_state['current_page'] = 'home'
        st.rerun()   # ✅ corrigido

def site_page():
    st.markdown("<h2 style='text-align: center;'>Sítio</h2>", unsafe_allow_html=True)
    st.write("Conteúdo da página do Sítio.")
    if st.button("Voltar para o Início"):
        st.session_state['current_page'] = 'home'
        st.rerun()   # ✅ corrigido

def main_page():
    """Exibe a página principal após o login com um layout mais agradável."""
    username = st.session_state.get('username', '')
    st.markdown("<h1 style='text-align: center;'>Página Inicial</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        st.markdown(f"<h3 style='text-align: center;'>Bem-vindo(a), **{username}**!</h3>", unsafe_allow_html=True)
        st.markdown("---")
        if st.button("🚚 Logística", use_container_width=True, key="btn_logistics"):
            st.session_state['current_page'] = 'logistics'
            st.rerun()   # ✅ corrigido
        if st.button("📈 Comercial", use_container_width=True, key="btn_commercial"):
            st.session_state['current_page'] = 'commercial'
            st.rerun()   # ✅ corrigido
        if st.button("👥 RH", use_container_width=True, key="btn_rh"):
            st.session_state['current_page'] = 'rh'
            st.rerun()   # ✅ corrigido
        if st.button("💻 TI", use_container_width=True, key="btn_ti"):
            st.session_state['current_page'] = 'ti'
            st.rerun()   # ✅ corrigido
        if st.button("🏠 Sítio", use_container_width=True, key="btn_site"):
            st.session_state['current_page'] = 'site'
            st.rerun()   # ✅ corrigido
        st.markdown("---")
        if st.button("Sair", use_container_width=True, key="btn_logout"):
            st.session_state['is_logged_in'] = False
            st.session_state['username'] = ""
            st.session_state['current_page'] = 'login'
            st.rerun()   # ✅ corrigido

# Dispatcher principal
if st.session_state.get('is_logged_in', False):
    page_functions = {
        'home': main_page,
        'logistics': logistics_page,
        'commercial': commercial_page,
        'rh': rh_page,
        'ti': ti_page,
        'site': site_page
    }
    current = st.session_state.get('current_page') or 'home'
    try:
        page_functions.get(current, main_page)()
    except Exception as e:
        st.error("Erro ao renderizar a página. Veja detalhes abaixo:")
        st.exception(e)
else:
    login_form()
