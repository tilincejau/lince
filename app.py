import streamlit as st
import base64

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

# Define as credenciais de login para demonstração
LOGIN_INFO = {
    "admin": "Joao789",
    "amanda": "12345",
    "marcia": "54321"
}

def login_form():
    """Exibe o formulário de login com um design aprimorado."""
    
    # Usa colunas para centralizar o formulário na página
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Adiciona o nome da empresa em um título
        st.markdown("<h2 style='text-align: center; color: #004d99; font-family: \'Arial Black\', sans-serif;'>Lince Distribuidora</h2>", unsafe_allow_html=True)
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
                st.success("Login realizado com sucesso! Redirecionando...")
                st.balloons() # Adiciona um efeito visual de balões
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")

# Lógica principal da página
if 'is_logged_in' not in st.session_state:
    st.session_state['is_logged_in'] = False

if st.session_state.get('is_logged_in', False):
    st.markdown(f"<h1 style='text-align: center;'>Página Inicial</h1>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='text-align: center;'>Bem-vindo(a), **{st.session_state['username']}**!</h3>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("Use o menu de navegação à esquerda para acessar as páginas dos setores.")
    
    if st.button("Sair", use_container_width=True):
        st.session_state['is_logged_in'] = False
        st.session_state.pop('username', None)
        st.rerun()
else:
    login_form()
