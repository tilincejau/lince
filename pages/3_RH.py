import streamlit as st
import pandas as pd
from datetime import timedelta
import io

# Verificação de login. Se não estiver logado, exibe uma mensagem e para o script.
if not st.session_state.get('is_logged_in'):
    st.warning("Você precisa estar logado para acessar esta página.")
    st.stop()

st.title("Setor de RH")
st.markdown("Bem-vindo(a) ao setor de RH. Abaixo está o script disponível para análise.")

st.write("---")
st.subheader("⏳ Controle de Jornada")
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

uploaded_file = st.file_uploader("Envie o arquivo 'Controle de Jornada.xlsx'", type=["xlsx"])

if uploaded_file is not None:
    try:
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
                    all_events.append({'Motorista': motorista, 'Tipo de Lançamento': entry_type, 'Inicio': start_time, 'Fim': None, 'Motivo': None, 'Carimbo de data/hora': timestamp})
            elif entry_type == 'Inicio de Viagem':
                date_str = row.get('Dia.1')
                time_str = row.get('Horário.1')
                if pd.notna(date_str) and pd.notna(time_str):
                    start_time = pd.to_datetime(f"{date_str} {time_str}")
                    all_events.append({'Motorista': motorista, 'Tipo de Lançamento': entry_type, 'Inicio': start_time, 'Fim': None, 'Motivo': None, 'Carimbo de data/hora': timestamp})
            elif entry_type == 'Fim da Viagem':
                time_str = row.get('Fim.5')
                if pd.notna(time_str):
                    time_str = str(time_str).split(' ')[-1]
                    end_time = pd.to_datetime(f"{timestamp.strftime('%Y-%m-%d')} {time_str}")
                    all_events.append({'Motorista': motorista, 'Tipo de Lançamento': entry_type, 'Inicio': None, 'Fim': end_time, 'Motivo': None, 'Carimbo de data/hora': timestamp})
            elif entry_type == 'Fim de Jornada':
                date_str = row.get('Dia.2')
                time_str = row.get('Horário.3')
                if pd.notna(date_str) and pd.notna(time_str):
                    end_time = pd.to_datetime(f"{date_str} {time_str}")
                    all_events.append({'Motorista': motorista, 'Tipo de Lançamento': entry_type, 'Inicio': None, 'Fim': end_time, 'Motivo': None, 'Carimbo de data/hora': timestamp})
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
                        start_time_str = str(start_time_str).split(' ')[-1]
                        end_time_str = str(end_time_str).split(' ')[-1]
                        start_time = pd.to_datetime(f"{date_str} {start_time_str}")
                        end_time = pd.to_datetime(f"{date_str} {end_time_str}")
                        all_events.append({'Motorista': motorista, 'Tipo de Lançamento': f'Parada {i}', 'Inicio': start_time, 'Fim': end_time, 'Motivo': motivo, 'Carimbo de data/hora': timestamp})
                    except ValueError:
                        st.error(f"Erro ao converter data/hora na linha {index} para 'Parada {i}'.")
                        continue
        consolidated_df = pd.DataFrame(all_events)
        consolidated_df.dropna(subset=['Motorista', 'Tipo de Lançamento'], how='all', inplace=True)
        consolidated_df.sort_values(by=['Motorista', 'Carimbo de data/hora'], inplace=True)
        consolidated_df.reset_index(drop=True, inplace=True)
        consolidated_df['Tempo Total de Jornada'] = pd.NaT
        consolidated_df['Tempo Total de Viagem'] = pd.NaT
        consolidated_df['Tempo de Dirigibilidade'] = pd.NaT
        consolidated_df['Tempo Almoço'] = pd.NaT
        consolidated_df['Tempo Carga/Descarga'] = pd.NaT
        consolidated_df['Tempo Liberação N.F.'] = pd.NaT
        consolidated_df['Tempo Repouso'] = pd.NaT
        for (motorista, dia), group in consolidated_df.groupby(['Motorista', consolidated_df['Carimbo de data/hora'].dt.date]):
            inicio_jornada = group[group['Tipo de Lançamento'] == 'Inicio Jornada']['Inicio'].min()
            fim_jornada = group[group['Tipo de Lançamento'] == 'Fim de Jornada']['Fim'].max()
            tempo_jornada = fim_jornada - inicio_jornada if pd.notnull(inicio_jornada) and pd.notnull(fim_jornada) else timedelta(seconds=0)
            inicio_viagem = group[group['Tipo de Lançamento'] == 'Inicio de Viagem']['Inicio'].min()
            fim_viagem = group[group['Tipo de Lançamento'] == 'Fim da Viagem']['Fim'].max()
            tempo_viagem = fim_viagem - inicio_viagem if pd.notnull(inicio_viagem) and pd.notnull(fim_viagem) else timedelta(seconds=0)
            break_durations = group.dropna(subset=['Motivo']).copy()
            if not break_durations.empty:
                break_durations['Duration'] = break_durations['Fim'] - break_durations['Inicio']
            else:
                break_durations['Duration'] = timedelta(seconds=0)
            almoco_duration = break_durations[break_durations['Motivo'] == 'Almoço']['Duration'].sum()
            carga_descarga_duration = break_durations[break_durations['Motivo'] == 'Carga/Descarga']['Duration'].sum()
            liberacao_nf_duration = break_durations[break_durations['Motivo'] == 'Liberação de N.F']['Duration'].sum()
            repouso_duration = break_durations[break_durations['Motivo'] == 'Repouso']['Duration'].sum()
            total_stop_time = almoco_duration + carga_descarga_duration + liberacao_nf_duration + repouso_duration
            tempo_dirigibilidade = tempo_viagem - total_stop_time
            consolidated_df.loc[group[group['Tipo de Lançamento'] == 'Fim de Jornada'].index, 'Tempo Total de Jornada'] = tempo_jornada
            consolidated_df.loc[group[group['Tipo de Lançamento'] == 'Fim da Viagem'].index, 'Tempo Total de Viagem'] = tempo_viagem
            consolidated_df.loc[group[group['Tipo de Lançamento'] == 'Fim da Viagem'].index, 'Tempo de Dirigibilidade'] = tempo_dirigibilidade
            consolidated_df.loc[group[group['Motivo'] == 'Almoço'].index, 'Tempo Almoço'] = almoco_duration
            consolidated_df.loc[group[group['Motivo'] == 'Carga/Descarga'].index, 'Tempo Carga/Descarga'] = carga_descarga_duration
            consolidated_df.loc[group[group['Motivo'] == 'Liberação de N.F'].index, 'Tempo Liberação N.F.'].iloc[0] = liberacao_nf_duration
            consolidated_df.loc[group[group['Motivo'] == 'Repouso'].index, 'Tempo Repouso'].iloc[0] = repouso_duration
        consolidated_df['Tempo Total de Jornada'] = consolidated_df['Tempo Total de Jornada'].apply(format_timedelta_as_dias_hms)
        consolidated_df['Tempo Total de Viagem'] = consolidated_df['Tempo Total de Viagem'].apply(format_timedelta_as_dias_hms)
        consolidated_df['Tempo de Dirigibilidade'] = consolidated_df['Tempo de Dirigibilidade'].apply(format_timedelta_as_hms)
        consolidated_df['Tempo Almoço'] = consolidated_df['Tempo Almoço'].apply(format_timedelta_as_hms)
        consolidated_df['Tempo Carga/Descarga'] = consolidated_df['Tempo Carga/Descarga'].apply(format_timedelta_as_hms)
        consolidated_df['Tempo Liberação N.F.'] = consolidated_df['Tempo Liberação N.F.'].apply(format_timedelta_as_hms)
        consolidated_df['Tempo Repouso'] = consolidated_df['Tempo Repouso'].apply(format_timedelta_as_hms)
        consolidated_df.drop(columns=['Carimbo de data/hora'], inplace=True)
        
        st.subheader("✅ Dados Processados")
        st.dataframe(consolidated_df)
        
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
