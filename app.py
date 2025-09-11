import streamlit as st

st.set_page_config(
    page_title="Lince Distribuidora de Bebidas - Login",
    page_icon="🏠",
    layout="centered",
    initial_sidebar_state="collapsed"
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
        st.markdown("<div class='centered-icon'>🔐</div>", unsafe_allow_html=True)
        st.title("Acesso Restrito")
        st.markdown("<h3 style='text-align: center; color: #555;'>Lince Distribuidora de Bebidas</h3>", unsafe_allow_html=True)
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

def main_page():
    """Exibe a página principal após o login com um layout mais agradável."""
    
    st.markdown("<h1 style='text-align: center;'>Página Inicial</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 3, 1])
    
    with col2:
        st.markdown(f"Bem-vindo(a), **{st.session_state['username']}**!")
        st.info("Agora você pode navegar para as outras páginas do menu lateral.")
        
        st.markdown("---")
        
        # Botão de sair estilizado
        if st.button("Sair", use_container_width=True):
            st.session_state['is_logged_in'] = False
            st.session_state.pop('username', None)
            st.rerun()

# Lógica principal da página
if st.session_state.get('is_logged_in', False):
    main_page()
else:
    login_form()
