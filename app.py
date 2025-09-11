import streamlit as st

st.set_page_config(
    page_title="Lince Distribuidora de Bebidas - Login",
    page_icon="🏠",
    layout="centered"
)

# Inicializa session_state
if 'is_logged_in' not in st.session_state:
    st.session_state['is_logged_in'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = ""
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = 'login'

# CSS
st.markdown("""
<style>
    .stApp {
        background-color: #f0f2f6;
    }
    .card {
        background-color: #fff;
        padding: 30px;
        border-radius: 15px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        text-align: center;
        cursor: pointer;
        transition: transform 0.2s, box-shadow 0.2s;
        height: 150px;
    }
    .card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 16px rgba(0,0,0,0.15);
    }
    .card-icon {
        font-size: 2.5rem;
    }
    .card-title {
        margin-top: 10px;
        font-size: 1.1rem;
        color: #004d99;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Credenciais
LOGIN_INFO = {
    "admin": "Joao789",
    "amanda": "12345",
    "marcia": "54321"
}

def login_form():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h2 style='text-align: center; color: #004d99;'>Lince Distribuidora</h2>", unsafe_allow_html=True)
        st.markdown("---")
        with st.form("login_form", clear_on_submit=False):
            st.markdown("Por favor, insira suas credenciais para continuar.")
            username = st.text_input("Usuário", placeholder="Digite seu nome de usuário")
            password = st.text_input("Senha", type="password", placeholder="Digite sua senha")
            submit_button = st.form_submit_button("Entrar", use_container_width=True)

        if submit_button:
            if username in LOGIN_INFO and LOGIN_INFO[username] == password:
                st.session_state['is_logged_in'] = True
                st.session_state['username'] = username
                st.session_state['current_page'] = 'home'
                st.success("Login realizado com sucesso! Redirecionando...")
                st.balloons()
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")

def main_page():
    username = st.session_state.get('username', '')
    st.markdown("<h1 style='text-align: center;'>Página Inicial</h1>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='text-align: center;'>Bem-vindo(a), {username}!</h3>", unsafe_allow_html=True)
    st.markdown("---")

    # Layout em grid de 3 colunas
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🚚 Logística", use_container_width=True):
            st.session_state['current_page'] = 'logistics'
            st.rerun()
    with col2:
        if st.button("📈 Comercial", use_container_width=True):
            st.session_state['current_page'] = 'commercial'
            st.rerun()
    with col3:
        if st.button("👥 RH", use_container_width=True):
            st.session_state['current_page'] = 'rh'
            st.rerun()

    col4, col5 = st.columns(2)
    with col4:
        if st.button("💻 TI", use_container_width=True):
            st.session_state['current_page'] = 'ti'
            st.rerun()
    with col5:
        if st.button("🏠 Sítio", use_container_width=True):
            st.session_state['current_page'] = 'site'
            st.rerun()

    st.markdown("---")
    if st.button("🚪 Sair", use_container_width=True):
        st.session_state['is_logged_in'] = False
        st.session_state['username'] = ""
        st.session_state['current_page'] = 'login'
        st.rerun()

# Páginas de exemplo
def logistics_page(): st.write("📦 Conteúdo da Logística")
def commercial_page(): st.write("💰 Conteúdo do Comercial")
def rh_page(): st.write("👥 Conteúdo de RH")
def ti_page(): st.write("💻 Conteúdo de TI")
def site_page(): st.write("🌱 Conteúdo do Sítio")

# Dispatcher
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
    page_functions.get(current, main_page)()
else:
    login_form()
