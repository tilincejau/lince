# Arquivo: lince_app_home.py
# Este será o arquivo principal da sua aplicação.

import streamlit as st

st.set_page_config(
    page_title="Lince Distribuidora de Bebidas",
    page_icon="🏠",
    layout="centered"
)

# Adiciona CSS personalizado
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
    .st-emotion-cache-1c7y3q {
        background-color: #F8F8F8;
        padding: 30px;
        border-radius: 10px;
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
    }
</style>
""", unsafe_allow_html=True)

# Define as credenciais de login para demonstração
LOGIN_INFO = {
    "admin": "Joao789",
    "amanda": "12345",
    "marcia": "54321"
}

# Lógica principal do login
if 'is_logged_in' not in st.session_state:
    st.session_state['is_logged_in'] = False

if st.session_state.get('is_logged_in', False):
    # Conteúdo da página principal (depois do login)
    st.markdown("<h1 style='text-align: center;'>Página Inicial</h1>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='text-align: center;'>Bem-vindo(a), **{st.session_state['username']}**!</h3>", unsafe_allow_html=True)
    st.markdown("---")

    st.write("Use a barra lateral para navegar entre as páginas dos departamentos.")

    if st.button("Sair", use_container_width=True, key="btn_logout"):
        st.session_state['is_logged_in'] = False
        st.session_state.pop('username', None)
        st.rerun()

else:
    # Formulário de login
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
            if username in LOGIN_INFO and LOGIN_INFO[username] == password:
                st.session_state['is_logged_in'] = True
                st.session_state['username'] = username
                st.success("Login realizado com sucesso! Redirecionando...")
                st.balloons()
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")
