import streamlit as st

st.set_page_config(
    page_title="Lince Distribuidora de Bebidas - Login",
    page_icon="🏠",
    layout="centered"
)

# Definir as credenciais de login para demonstração
# Em uma aplicação real, a senha deveria ser criptografada e o sistema de
# autenticação mais robusto (ex: com banco de dados).
# As credenciais são: usuário 'admin' e senha '123'
LOGIN_INFO = {
    "admin": "Joao789",
    "amanda": "12345",
    "marcia": "54321"
}

def login_form():
    """Exibe o formulário de login."""
    st.title("🔐 Acesso Restrito")
    st.markdown("Por favor, insira suas credenciais para continuar.")
    
    with st.form("login_form"):
        username = st.text_input("Usuário", key="username_input")
        password = st.text_input("Senha", type="password", key="password_input")
        submit_button = st.form_submit_button("Entrar")
    
    if submit_button:
        if username in LOGIN_INFO and LOGIN_INFO[username] == password:
            st.session_state['is_logged_in'] = True
            st.session_state['username'] = username
            st.success("Login realizado com sucesso! Redirecionando...")
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos.")

def main_page():
    """Exibe a página principal após o login."""
    st.title("Página Inicial - Logado")
    st.markdown(f"Bem-vindo(a), **{st.session_state['username']}**!")
    st.info("Agora você pode navegar para as outras páginas do menu lateral.")
    
    if st.button("Sair"):
        st.session_state['is_logged_in'] = False
        st.session_state.pop('username', None)
        st.rerun()

# Lógica principal da página
if st.session_state.get('is_logged_in', False):
    main_page()
else:
    login_form()
