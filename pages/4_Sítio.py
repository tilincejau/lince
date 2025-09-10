import streamlit as st
import pandas as pd
import openpyxl
import re
import io
from openpyxl import load_workbook

# Verificação de login. Se não estiver logado, exibe uma mensagem e para o script.
if not st.session_state.get('is_logged_in'):
    st.warning("Você precisa estar logado para acessar esta página.")
    st.stop()

st.title("Setor Sítio")
st.markdown("Bem-vindo(a) ao setor Sítio. Abaixo está o script disponível para análise.")

st.write("---")
st.subheader("🏡 Sítio Santa Izabel")
st.markdown("Este script processa a planilha de controle do Sítio Santa Izabel e a divide em abas com base nos lançamentos.")

def normalize_columns(columns_list):
    """
    Normaliza uma lista de nomes de colunas, removendo espaços extras,
    caracteres especiais e quebras de linha.
    """
    normalized_list = []
    for col in columns_list:
        col = re.sub(r'\s+', ' ', col).strip()
        col = col.replace('\n', ' ')
        normalized_list.append(col)
    return normalized_list

uploaded_file = st.file_uploader("Envie o arquivo 'SÍTIO SANTA IZABEL.xlsx'", type=["xlsx"])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file, engine='openpyxl')
        st.subheader("📄 Dados Originais")
        st.dataframe(df.head())

        df.columns = normalize_columns(df.columns)

        planilhas_config = {
            'Pulverização': [
                'Carimbo de data/hora', 'Qual lançamento', 'Qual Talhão?',
                'Diagnóstico e Justificativa', 'Fase Fenológica', 'Previsão colheita',
                'Problema Alvo (Praga, Doença, Planta Daninha ou Deficiência Nutricional)',
                'Diagnóstico e Nível de Infestação/Ocorrência (Descrição detalhada)',
                'Justificativa Técnica para a Recomendação',
                'PRODUTO (N.C*E I.A.**)','Volume de Calda Recomendado (L/ha)',
                'Equipamento de aplicação', 'Número de Aplicações Recomendadas',
                'Intervalo entre Aplicações (dias - se houver mais de uma)', 
                'Modo de Aplicação','Época/Estádio de Aplicação',
                'Intervalo de Segurança/Período de Carência (dias)',
                'Intervalo de Reentrada na Área (horas)',
                'Equipamento de Proteção Individual (EPI)',
                'Condições Climáticas Ideais para Aplicação ex: "Evitar ventos acima de 10 km/h, temperatura abaixo de 30°C, umidade relativa acima de 55%"',
                'Cuidados com a Calda e Descarte de Embalagens ex: "Realizar tríplice lavagem das embalagens e descartá-las em locais indicados"',
                'Informações sobre Mistura em Tanque (se aplicável)',
                'Observações Adicionais/Advertências',
            ],
            'Controle de Irrigação': [
                'Carimbo de data/hora', 'Qual lançamento', 'Período', 'Setor/Talhão', 
                'Hora(s) de irrigação', 'Volume de Água (L)', 'Tipo de Irrigação',
                'Observações (Clima/Outros)', 'Responsável', 'Próxima Irrigação Sugerida'
            ],
            'Controle de Pragas': [
                'Carimbo de data/hora', 'Qual lançamento', 'DATA (3)', 'PRAGA', 'RECOMENDAÇÃO',
                'RECEITA', 'MODO DE APLICAÇÃO', 'PERÍODO', 'OBSERVAÇÃO'
            ],
            'Pluviômetro - (somente em dias de chuva)': [
                'Carimbo de data/hora', 'Qual lançamento', 'DATA (1)', 'LEITURA(MM)', 'OBSERVAÇÕES'
            ],
            'Hidrômetro': [
                'Carimbo de data/hora', 'Qual lançamento', 'DATA (2)', 'LEITURA (m³)'
            ],
            'Lavagem de EPIs': [
                'Carimbo de data/hora', 'Qual lançamento', 'Data da Lavagem:', 'Responsável pela Lavagem ',
                'Local da Lavagem', 'EPI', 'Agente de Limpeza Utilizado:', 'Temperatura da Água', 'Ciclos de enxague',
                'Condições de Armazenamento'
            ],
            'Registro de aplicações': [
                'Carimbo de data/hora', 'Qual lançamento', 'Cultura e/ou Variedade Tratada',
                'Local da Aplicação  ( Por favor, especifique a zona geográfica, nome/referência da exploração, e o campo de produção, pomar, estufa ou instalação onde a cultura se encontra.)',
                'Data de Início da Aplicação',
                'Data de Fim da Aplicação',
                'Nome Comercial Registrado do Produto',
                'Intervalo de Segurança Pré-Colheita (PHS)',
                'Quantidade de Produto Aplicado',
                'Concentração ou Frequência',
                'Nome Completo do Aplicador',
                'Nome Completo da Pessoa Tecnicamente Responsável',
            ],
            'Limpeza do Local': [
                'Carimbo de data/hora', 'Qual lançamento', 'LOCAL', '  Marque com "X" a opção que melhor descreve o estado de limpeza   [PISOS]',
                '  Marque com "X" a opção que melhor descreve o estado de limpeza   [LIXEIRAS]', '  Marque com "X" a opção que melhor descreve o estado de limpeza   [Superfícies (mesas, bancadas)]',
                '  Marque com "X" a opção que melhor descreve o estado de limpeza   [Janelas e vidros]', 
                '  Marque com "X" a opção que melhor descreve o estado de limpeza   [Banheiros]', '  Marque com "X" a opção que melhor descreve o estado de limpeza   [Descarte de resíduos]',
                '  Marque com "X" a opção que melhor descreve o estado de limpeza   [Organização geral]',
                'Problemas encontrados', 'Sugestões para melhoria'
            ],
            'Limpeza dos Equipamentos e Dispositivos': [
                'Qual a Limpeza (7)', 'Data da Lavagem  (7)', 'Item Lavado  (7)', 'Produto Utilizado  (7)', 'Procedimento de Lavagem  (Exemplo  "submersão" , "pré-lavagem") (7)',
                'Responsável pela Lavagem (7)', 'Observações  (7)' 
            ]
        }
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for sheet_name, columns in planilhas_config.items():
                try:
                    normalized_columns = normalize_columns(columns)
                    if sheet_name == 'Pulverização':
                        for col in df.columns:
                            if re.search(r'\(\d+\)', col) and col not in ['DATA (1)', 'DATA (2)', 'DATA (3)']:
                                normalized_columns.append(col)
                        normalized_columns = list(dict.fromkeys(normalized_columns))

                    df_filtered = df[df['Qual lançamento'] == sheet_name]
                    existing_columns = [col for col in normalized_columns if col in df_filtered.columns]
                    df_sheet = df_filtered[existing_columns]

                    df_sheet.to_excel(writer, sheet_name=sheet_name, index=False)
                    st.info(f"Aba '{sheet_name}' criada com sucesso.")

                except KeyError as e:
                    st.warning(f"Aviso: Ocorreu um erro ao filtrar a aba '{sheet_name}'. Verifique se o nome da aba está correto.")
                    continue
        
        output.seek(0)
        st.subheader("✅ Processo Concluído")
        st.success("O arquivo foi processado e está pronto para download.")
        
        st.download_button(
            label="📥 Baixar Arquivo Processado",
            data=output,
            file_name="sitio_santaizabel.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        st.error(f"Ocorreu um erro ao processar o arquivo: {e}")
