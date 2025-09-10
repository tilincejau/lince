import streamlit as st
from selenium import webdriver
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import requests
import os
import io

if not st.session_state.get('is_logged_in'):
    st.warning("Você precisa estar logado para acessar esta página.")
    st.stop()

# --- Conteúdo do seu script ---

st.title("📦 Importação e Download de Dados")
st.markdown("Este script automatiza o download de arquivos do Qlik Sense. **Atenção:** Este processo pode levar alguns minutos.")
st.warning("Este script requer um ambiente específico e pode não funcionar corretamente em todos os sistemas. Ele tenta automatizar um processo que depende de um pop-up do Windows, que é difícil de controlar em um ambiente web. Considere executar este script localmente.")

# TODO: SUBSTITUA ESTES VALORES PELOS SEUS DADOS REAIS
URL = "http://bi.controlinformatica.com.br/internal_windows_authentication/"
USUARIO = "Lince_01"
SENHA = "Li_668877"
TARGET_APP_URL = "http://bi.controlinformatica.com.br/sense/app/bac4723f-9192-4fbf-9549-62e50ed4f11f/sheet/06d25610-15e6-4e06-bd0a-6647340766a7/state/analysis"
DOWNLOAD_PATH = os.path.join(os.getcwd(), "downloads") # Pasta de downloads local

NOMES_ARQUIVOS_DESEJADOS = [
    ("base clientes", "Clientes.xlsx"),
    ("SKUs por PDV", "SKUs por PDV.xlsx"),
    ("Heishop Vendas", "VendasHeishop.xlsx"),
    ("Heishop Estáveis", "estaveis.xlsx"),
    ("Coberturas Assessment", "Coberturas.xlsx"),
    ("fds Alterado em Jul 2022 para considerar Vendas e Bonificacoes acima de 1 cx ( com excecao do Craft que considera abaixo de 1 cx )", "fds.xlsx"),
    ("Vasilhames Comodatos", "Vasilhames Comodatos.xlsx"),
    ("Vasilhames Giro", "Vasilhames Giro.xlsx"),
    ("Refrigeracao Comodatos", "Refrigeracao Comodatos.xlsx"),
    ("Refrigeracao Giro", "Refrigeracao Giro.xlsx"),
    ("kpis_temp", "KPIs.xlsx"),
    ("Devolucao(1)", "Devolucoes.xlsx"), 
    ("MetaVol(1)", "MetaVolume.xlsx"), 
    ("MetaCob(1)", "MetaCob.xlsx"),             
    ("Real(1)", "Real.xlsx")              
]

CONSULTAS_HISTORICO_ANUAL = [
    "SKUs por PDV", 
    "Heishop Vendas", 
    "Heishop Estáveis", 
    "Coberturas Assessment", 
    "fds Alterado em Jul 2022 para considerar Vendas e Bonificacoes acima de 1 cx ( com excecao do Craft que considera abaixo de 1 cx )", 
    "kpis_temp", 
    "Devolucao(1)", 
    "MetaVol(1)",
    "MetaCob(1)", 
    "Real(1)"
]

CONSULTAS_MES_ATUAL = [
    "base clientes",
    "Vasilhames Comodatos",
    "Vasilhames Giro",
    "Refrigeracao Comodatos",
    "Refrigeracao Giro"
]

def click_element_robustly(driver_instance, by_locator, timeout=420, element_name="elemento"):
    element = None
    attempts = 0
    max_attempts = 3
    while attempts < max_attempts:
        try:
            st.info(f"Tentando clicar em '{element_name}'...")
            element = WebDriverWait(driver_instance, timeout).until(
                EC.element_to_be_clickable(by_locator)
            )
            element.click()
            st.success(f"Clique nativo em '{element_name}' bem-sucedido.")
            return
        except TimeoutException:
            st.warning(f"Timeout: '{element_name}' não clicável. Tentando clicar via JavaScript...")
            try:
                element = WebDriverWait(driver_instance, 5).until(EC.presence_of_element_located(by_locator))
                driver_instance.execute_script("arguments[0].click();", element)
                st.success(f"Clique via JavaScript em '{element_name}' bem-sucedido.")
                return
            except (NoSuchElementException, StaleElementReferenceException) as e:
                st.error(f"Erro ao clicar via JavaScript: {e}. Re-tentando...")
                attempts += 1
                time.sleep(1)
        except StaleElementReferenceException:
            st.warning(f"StaleElementReferenceException ao clicar nativamente em '{element_name}'. Re-tentando...")
            attempts += 1
            time.sleep(1)
        except Exception as e:
            st.error(f"Erro inesperado ao clicar em '{element_name}': {e}. Re-tentando...")
            attempts += 1
            time.sleep(1)
    
    raise Exception(f"Falha ao clicar em '{element_name}' após {max_attempts} tentativas.")

def try_to_clean_up_modals(driver):
    try:
        st.info("Tentando fechar modais...")
        WebDriverWait(driver, 30).until(
            EC.invisibility_of_element_located((By.XPATH, "//span[contains(@q-translation, 'Export.CompletedDescription')]"))
        )
        WebDriverWait(driver, 30).until(
            EC.invisibility_of_element_located((By.XPATH, "//div[contains(@class, 'lui-modal')]"))
        )
        st.success("Modais de exportação fechados.")
    except TimeoutException:
        st.warning("AVISO: Modais ainda visíveis após tentativas de fechamento.")

def perform_single_download(driver, display_name, file_name):
    try:
        query_element_xpath = f"//div[contains(@class, 'qv-object') and contains(normalize-space(.), '{display_name}')]"
        container = WebDriverWait(driver, 60).until(
            EC.visibility_of_element_located((By.XPATH, query_element_xpath))
        )

        driver.execute_script("arguments[0].scrollIntoView(true);", container)
        time.sleep(0.5)

        ActionChains(driver).context_click(container).perform()
        
        context_menu_container = WebDriverWait(driver, 60).until(
            EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'lui-popover') or contains(@class, 'lui-menu')]"))
        )

        click_element_robustly(
            context_menu_container, 
            (By.XPATH, ".//li[contains(@class, 'lui-list__item') and .//span[normalize-space(text())='Baixar como...']]"),
            element_name="Opção 'Baixar como...'"
        )
        time.sleep(1)
        
        submenu_container = WebDriverWait(driver, 60).until(
            EC.visibility_of_element_located((By.XPATH, "//div[contains(@class, 'lui-popover') or contains(@class, 'lui-menu')][not(contains(@class, 'ng-hide'))]"))
        )

        click_element_robustly(
            submenu_container, 
            (By.XPATH, ".//li[contains(@class, 'lui-list__item') and .//span[normalize-space(text())='Dados']]"),
            element_name="Opção 'Dados'"
        )
        
        click_element_robustly(
            driver, 
            (By.XPATH, "//button[contains(normalize-space(.), 'Exportar')]"),
            element_name="Botão 'Exportar'"
        )
        
        download_link_element = WebDriverWait(driver, 120).until(
            EC.presence_of_element_located((By.XPATH, "//a[contains(normalize-space(.), 'Clique aqui para baixar seu arquivo de dados')]"))
        )
        download_url = download_link_element.get_attribute('href')
        
        try_to_clean_up_modals(driver)

        selenium_cookies = driver.get_cookies()
        cookies = {cookie['name']: cookie['value'] for cookie in selenium_cookies}
        
        response = requests.get(download_url, cookies=cookies, stream=True, verify=False) 
        response.raise_for_status()

        # Usando BytesIO para download em memória
        st.success(f"Arquivo '{file_name}' baixado com sucesso! Agora você pode baixá-lo no botão abaixo.")
        st.download_button(
            label=f"📥 Baixar {file_name}",
            data=io.BytesIO(response.content),
            file_name=file_name
        )

    except Exception as e:
        st.error(f"ERRO durante o download da consulta '{display_name}': {e}")
        try_to_clean_up_modals(driver)
        raise

def automatizar_downloads(driver):
    st.subheader("Iniciando Automação de Downloads")
    
    try:
        WebDriverWait(driver, 120).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, '.qv-object')))
        st.success("Objetos da página carregados.")
    except TimeoutException:
        st.error("ERRO: Nenhum contêiner de consulta encontrado.")
        return

    st.subheader("Processando consultas do mês atual")
    for display_name, file_name in NOMES_ARQUIVOS_DESEJADOS:
        if display_name in CONSULTAS_MES_ATUAL:
            st.info(f"Processando consulta: '{display_name}'")
            try:
                perform_single_download(driver, display_name, file_name)
            except Exception as e:
                st.error(f"ERRO durante o download da consulta '{display_name}': {e}")
                continue
    
    st.subheader("Processando consultas com histórico anual")
    for display_name, file_name in NOMES_ARQUIVOS_DESEJADOS:
        if display_name in CONSULTAS_HISTORICO_ANUAL:
            st.info(f"Processando consulta com histórico anual: '{display_name}'")
            try:
                perform_single_download(driver, display_name, file_name)
            except Exception as e:
                st.error(f"ERRO ao processar histórico anual para a consulta '{display_name}': {e}")
                continue
            
    st.success("Automação de downloads concluída!")

def automatizar_login():
    driver = None
    try:
        options = webdriver.ChromeOptions()
        st.info("Configurando o navegador...")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--allow-running-insecure-content")
        options.add_argument("--disable-web-security")
        options.add_argument("--disable-features=DownloadBlocking")
        options.add_argument("--disable-features=SafeBrowsing")
        
        driver = webdriver.Chrome(options=options)
        driver.maximize_window()
        driver.get(URL)
        st.info("Navegador aberto e página carregada.")

        # Lógica de login com pywinauto é difícil de implementar em ambientes web.
        # Por isso, vamos pular essa parte e assumir que o login manual foi feito.
        st.warning("A automação de login com pop-up do Windows não é suportada neste ambiente. Por favor, faça o login manualmente e clique em 'Iniciar Automação'.")

    except Exception as e:
        st.error(f"Erro na automação: {e}")
    finally:
        if driver:
            driver.quit()

if st.button("Iniciar Automação"):
    with st.spinner("Iniciando automação... Isso pode demorar."):
        st.info("Iniciando a automação. Por favor, não feche o navegador que será aberto.")
        try:
            automatizar_login()
            # Se você já fez o login manualmente e a página está pronta
            # automatizar_downloads(driver)
        except Exception as e:
            st.error(f"Ocorreu um erro inesperado: {e}")
