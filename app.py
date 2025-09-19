import streamlit as st
import pandas as pd
import io
from datetime import datetime, timedelta

def rh_page():
    st.title("Setor de RH")
    st.markdown("Bem-vindo(a) ao setor de RH. Abaixo estão os scripts disponíveis para análise.")

    script_choice = st.selectbox(
        "Selecione um script para executar:",
        ("Selecione...", "Controle de Jornada")
    )

    st.write("---")

    if script_choice == "Controle de Jornada":
        st.subheader("Controle de Jornada")
        st.markdown("Este script processa uma planilha de controle de jornada e calcula tempos de viagem, dirigibilidade e paradas.")

        def format_timedelta_as_hms(td):
            if pd.isna(td):
                return pd.NaT
            total_seconds = td.total_seconds()
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

        def format_timedelta_as_dias_hms(td):
            if pd.isna(td):
                return pd.NaT
            total_seconds = td.total_seconds()
            days, remainder = divmod(total_seconds, 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, seconds = divmod(remainder, 60)
            if days > 0:
                return f"{int(days)} dias {int(hours):02}:{int(minutes):02}:{int(seconds):02}"
            else:
                return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

        uploaded_file = st.file_uploader("Envie o arquivo 'Controle de Jornada.xlsx'", type=["xlsx", "csv"])

        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)
                
                st.subheader("📄 Dados Originais")
                st.dataframe(df.head())

                all_events = []
                for index, row in df.iterrows():
                    motorista = row.get('Motorista')
                    timestamp_str = row.get('Carimbo de data/hora')
                    if pd.isna(timestamp_str) or pd.isna(motorista):
                        continue
                    timestamp = pd.to_datetime(timestamp_str)
                    entry_type = row.get('Qual o tipo de lançamento?')

                    if entry_type == 'Inicio Jornada':
                        date_str = row.get('Dia')
                        time_str = row.get('Horário')
                        if pd.notna(date_str) and pd.notna(time_str):
                            start_time = pd.to_datetime(f"{date_str} {time_str}")
                            all_events.append({'Motorista': motorista, 'Tipo de Lançamento': 'Inicio Jornada', 'Inicio': start_time, 'Fim': None, 'Motivo': None, 'Carimbo de data/hora': timestamp})
                    elif entry_type == 'Inicio de Viagem':
                        date_str = row.get('Dia.1')
                        time_str = row.get('Horário.1')
                        if pd.notna(date_str) and pd.notna(time_str):
                            start_time = pd.to_datetime(f"{date_str} {time_str}")
                            all_events.append({'Motorista': motorista, 'Tipo de Lançamento': 'Inicio de Viagem', 'Inicio': start_time, 'Fim': None, 'Motivo': None, 'Carimbo de data/hora': timestamp})
                    elif entry_type == 'Fim da Viagem':
                        time_str = row.get('Fim.5')
                        if pd.notna(time_str):
                            time_str = str(time_str).split(' ')[-1]
                            end_time = pd.to_datetime(f"{timestamp.strftime('%Y-%m-%d')} {time_str}")
                            all_events.append({'Motorista': motorista, 'Tipo de Lançamento': 'Fim da Viagem', 'Inicio': None, 'Fim': end_time, 'Motivo': None, 'Carimbo de data/hora': timestamp})
                    elif entry_type == 'Fim de Jornada':
                        date_str = row.get('Dia.2')
                        time_str = row.get('Horário.3')
                        if pd.notna(date_str) and pd.notna(time_str):
                            end_time = pd.to_datetime(f"{date_str} {time_str}")
                            all_events.append({'Motorista': motorista, 'Tipo de Lançamento': 'Fim de Jornada', 'Inicio': None, 'Fim': end_time, 'Motivo': None, 'Carimbo de data/hora': timestamp})
                    
                    parada_cols_map = {
                        '1': {'inicio': 'Inicio ', 'fim': 'Fim', 'motivo': 'Motivo'},
                        '2': {'inicio': 'Inicio', 'fim': 'Fim.1', 'motivo': 'Motivo.1'},
                        '3': {'inicio': 'Inicio.1', 'fim': 'Fim.2', 'motivo': 'Motivo.2'},
                        '4': {'inicio': 'Inicio.2', 'fim': 'Fim.3', 'motivo': 'Motivo.3'},
                        '5': {'inicio': 'Inicio.3', 'fim': 'Fim.4', 'motivo': 'Motivo.4'}
                    }
                    for i in range(1, 6):
                        cols = parada_cols_map.get(str(i))
                        start_time_str = row.get(cols['inicio'])
                        end_time_str = row.get(cols['fim'])
                        motivo = row.get(cols['motivo'])
                        if pd.notna(start_time_str) and pd.notna(end_time_str) and pd.notna(motivo):
                            date_str = timestamp.strftime('%Y-%m-%d')
                            try:
                                start_time = pd.to_datetime(f"{date_str} {str(start_time_str).split(' ')[-1]}")
                                end_time = pd.to_datetime(f"{date_str} {str(end_time_str).split(' ')[-1]}")
                                all_events.append({'Motorista': motorista, 'Tipo de Lançamento': f'Parada {i}', 'Inicio': start_time, 'Fim': end_time, 'Motivo': motivo, 'Carimbo de data/hora': timestamp})
                            except ValueError:
                                st.error(f"Erro ao converter data/hora na linha {index} para 'Parada {i}'.")
                                continue

                consolidated_df = pd.DataFrame(all_events)
                consolidated_df.dropna(subset=['Motorista', 'Tipo de Lançamento'], how='all', inplace=True)
                consolidated_df['Carimbo de data/hora'] = pd.to_datetime(consolidated_df['Carimbo de data/hora'])
                consolidated_df.sort_values(by=['Motorista', 'Carimbo de data/hora'], inplace=True)
                consolidated_df.reset_index(drop=True, inplace=True)

                motoristas = sorted(consolidated_df['Motorista'].unique())
                tabs = st.tabs(motoristas)

                for i, motorista in enumerate(motoristas):
                    with tabs[i]:
                        st.subheader(f"Resumo Diário - {motorista}")
                        
                        df_motorista = consolidated_df[consolidated_df['Motorista'] == motorista].copy()
                        df_motorista['Dia'] = df_motorista['Carimbo de data/hora'].dt.date
                        
                        summary_rows = []
                        for dia, group in df_motorista.groupby('Dia'):
                            inicio_jornada = group[group['Tipo de Lançamento'] == 'Inicio Jornada']['Inicio'].min()
                            fim_jornada = group[group['Tipo de Lançamento'] == 'Fim de Jornada']['Fim'].max()
                            tempo_jornada = fim_jornada - inicio_jornada if pd.notnull(inicio_jornada) and pd.notnull(fim_jornada) else timedelta(seconds=0)

                            inicio_viagem = group[group['Tipo de Lançamento'] == 'Inicio de Viagem']['Inicio'].min()
                            fim_viagem = group[group['Tipo de Lançamento'] == 'Fim da Viagem']['Fim'].max()
                            tempo_viagem = fim_viagem - inicio_viagem if pd.notnull(inicio_viagem) and pd.notnull(fim_viagem) else timedelta(seconds=0)

                            break_durations = group.dropna(subset=['Motivo']).copy()
                            if not break_durations.empty:
                                break_durations['Duration'] = break_durations['Fim'] - break_durations['Inicio']
                                total_stop_time = break_durations['Duration'].sum()
                            else:
                                total_stop_time = timedelta(seconds=0)
                            
                            tempo_dirigibilidade = tempo_viagem - total_stop_time

                            summary_rows.append({
                                'Motorista': motorista,
                                'Dia': dia,
                                'Tempo Total de Jornada': format_timedelta_as_dias_hms(tempo_jornada),
                                'Tempo Total de Viagem': format_timedelta_as_dias_hms(tempo_viagem),
                                'Tempo de Dirigibilidade': format_timedelta_as_hms(tempo_dirigibilidade)
                            })
                        
                        df_summary = pd.DataFrame(summary_rows)
                        st.dataframe(df_summary.set_index('Dia'))
                        
                        st.write("---")
                        st.subheader("Detalhes da Jornada")
                        
                        df_details = df_motorista[['Tipo de Lançamento', 'Inicio', 'Fim', 'Motivo', 'Carimbo de data/hora']].copy()
                        df_details['Duração'] = df_details.apply(lambda row: row['Fim'] - row['Inicio'] if pd.notna(row['Inicio']) and pd.notna(row['Fim']) else pd.NaT, axis=1)
                        df_details['Duração Formatada'] = df_details['Duração'].apply(format_timedelta_as_hms)
                        df_details.drop(columns=['Duração', 'Carimbo de data/hora'], inplace=True)
                        st.dataframe(df_details)

                st.write("---")
                
                excel_data = io.BytesIO()
                consolidated_df.to_excel(excel_data, sheet_name="Dados Consolidados", index=False)
                excel_data.seek(0)
                
                st.download_button(
                    label="📥 Baixar Arquivo Processado",
                    data=excel_data,
                    file_name="Jornada_Calculo.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            
            except Exception as e:
                st.error(f"Ocorreu um erro ao processar o arquivo: {e}")

    if st.button("Voltar para o Início"):
        st.session_state['current_page'] = 'home'
        st.rerun()
