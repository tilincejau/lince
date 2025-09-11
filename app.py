import streamlit as st
import base64

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
                st.session_state['current_page'] = 'home' # Define a página inicial
                st.success("Login realizado com sucesso! Redirecionando...")
                st.balloons() # Adiciona um efeito visual de balões
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")

def logistics_page():
    st.markdown("<h2 style='text-align: center;'>Logística</h2>", unsafe_allow_html=True)
    st.write("Conteúdo da página de Logística.")
    if st.button("Voltar para o Início"):
        st.session_state['current_page'] = 'home'
        st.rerun()

def commercial_page():
    st.markdown("<h2 style='text-align: center;'>Comercial</h2>", unsafe_allow_html=True)
    st.write("Conteúdo da página de Comercial.")
    if st.button("Voltar para o Início"):
        st.session_state['current_page'] = 'home'
        st.rerun()

def rh_page():
    st.markdown("<h2 style='text-align: center;'>Recursos Humanos</h2>", unsafe_allow_html=True)
    st.write("Conteúdo da página de Recursos Humanos.")
    if st.button("Voltar para o Início"):
        st.session_state['current_page'] = 'home'
        st.rerun()

def ti_page():
    st.markdown("<h2 style='text-align: center;'>TI</h2>", unsafe_allow_html=True)
    st.write("Conteúdo da página de TI.")
    if st.button("Voltar para o Início"):
        st.session_state['current_page'] = 'home'
        st.rerun()

def site_page():
    st.markdown("<h2 style='text-align: center;'>Sítio</h2>", unsafe_allow_html=True)
    st.write("Conteúdo da página do Sítio.")
    if st.button("Voltar para o Início"):
        st.session_state['current_page'] = 'home'
        st.rerun()

def main_page():
    """Exibe a página principal após o login com um layout mais agradável."""
    
    st.markdown("<h1 style='text-align: center;'>Página Inicial</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 3, 1])
    
    with col2:
        st.markdown(f"<h3 style='text-align: center;'>Bem-vindo(a), **{st.session_state['username']}**!</h3>", unsafe_allow_html=True)
        st.markdown("---")
        
        # Define as áreas com ícones e texto
        areas = {
            "Logística": {"icon": "🚚", "help": "Gestão de estoque e rotas.", "key": "logistics"},
            "Comercial": {"icon": "📈", "help": "Acompanhamento de vendas e clientes.", "key": "commercial"},
            "RH": {"icon": "👥", "help": "Recursos Humanos e folha de pagamento.", "key": "rh"},
            "TI": {"icon": "💻", "help": "Suporte técnico e infraestrutura.", "key": "ti"},
            "Sítio": {"icon": "🏠", "help": "Gerenciamento do sítio da empresa.", "key": "site"}
        }

        # Cria os botões em colunas para ficarem um abaixo do outro
        for area, props in areas.items():
            st.button(f"{props['icon']} {area}", help=props['help'], key=props['key'])
            if st.session_state[props['key']]:
                st.session_state['current_page'] = props['key']
                st.rerun()
        
        st.markdown("---")
        
        # Botão de sair estilizado
        if st.button("Sair", use_container_width=True):
            st.session_state['is_logged_in'] = False
            st.session_state.pop('username', None)
            st.session_state.pop('current_page', None)
            st.rerun()

# Lógica principal da página
if st.session_state.get('is_logged_in', False):
    if st.session_state.get('current_page') == 'logistics':
        logistics_page()
    elif st.session_state.get('current_page') == 'commercial':
        commercial_page()
    elif st.session_state.get('current_page') == 'rh':
        rh_page()
    elif st.session_state.get('current_page') == 'ti':
        ti_page()
    elif st.session_state.get('current_page') == 'site':
        site_page()
    else:
        main_page()
else:
    login_form()
