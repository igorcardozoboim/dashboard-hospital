import streamlit as st

import pandas as pd

import plotly.express as px

import plotly.graph_objects as go

import json

import unicodedata



# Configuração da página do dashboard

st.set_page_config(layout="wide")



# Título do Dashboard

st.title('Dashboard de Gestão Epidemiológica do Hospital Santa Rita de Cássia - 01/01/2024 a 31/07/2025')



# Injeção de CSS para corrigir a rolagem no Chrome

st.markdown('<style>div.block-container{padding-top:2rem;}</style>', unsafe_allow_html=True)



# --- Carregamento e Preparação dos Dados ---

@st.cache_data

def carregar_dados():

    try:

        df = pd.read_csv('epidemio_2024_2025_compacta.zip', encoding='utf-8', delimiter=';')

    except (UnicodeDecodeError, pd.errors.ParserError):

        df = pd.read_csv('epidemio_2024_2025_compacta.zip', encoding='latin1', delimiter=';')

    except FileNotFoundError:

        st.error("Arquivo 'epidemio_2024_2025_compacta.zip' não encontrado.")

        return pd.DataFrame()



    date_series = df['DT_ATENDIMENTO'].astype(str).str.split().str[0]

    df['DT_ATENDIMENTO'] = pd.to_datetime(date_series, format='%d/%m/%Y', errors='coerce')

   

    if 'SEXO' in df.columns:

        df['SEXO'] = df['SEXO'].astype(str)

   

    return df



df = carregar_dados()

df.dropna(subset=['DT_ATENDIMENTO'], inplace=True)



# --- Barra Lateral de Filtros ---



st.sidebar.subheader("Filtro por Período")

min_data = df['DT_ATENDIMENTO'].min().date()

max_data = df['DT_ATENDIMENTO'].max().date()



data_inicio = st.sidebar.date_input("Data de Início", min_data, min_value=min_data, max_value=max_data)

data_fim = st.sidebar.date_input("Data de Fim", max_data, min_value=min_data, max_value=max_data)



st.sidebar.subheader("Filtro por CID")

cid_counts = df['DESCRICAO_CID'].value_counts()

cids_relevantes = cid_counts[cid_counts >= 1000].index.tolist()

cids_selecionados = st.sidebar.multiselect(

    'Selecione um ou mais CIDs (com >= 1000 casos):',

    options=sorted(cids_relevantes),

    default=[]

)



# --- Lógica de Filtragem ---

start_date = pd.to_datetime(data_inicio)

end_date = pd.to_datetime(data_fim)

df_periodo = df[(df['DT_ATENDIMENTO'] >= start_date) & (df['DT_ATENDIMENTO'] <= end_date)]



if cids_selecionados:

    df_filtrado = df_periodo[df_periodo['DESCRICAO_CID'].isin(cids_selecionados)]

else:

    df_filtrado = df_periodo.copy()



# --- Estrutura de Abas ---

tab1, tab2 = st.tabs(["Resumo Gerencial e Demográfico", "Análise Epidemiológica"])



# --- Conteúdo da Aba 1: Resumo Gerencial e Demográfico ---

with tab1:

    st.subheader("Resumo do Período e Filtros Selecionados")

    col1, col2, col3, col4 = st.columns(4)

    # KPIs e Gráfico de Pizza

    total_atendimentos = len(df_filtrado)

    col1.metric("Total de Atendimentos", f"{total_atendimentos:,}".replace(",", "."))

    pacientes_unicos = df_filtrado['CD_PACIENTE'].nunique()

    col2.metric("Nº de Pacientes Únicos", f"{pacientes_unicos:,}".replace(",", "."))

    media_idade = int(df_filtrado['IDADE'].mean()) if not df_filtrado.empty else 0

    col3.metric("Média de Idade dos Pacientes", f"{media_idade} anos")

    with col4:

        if not df_filtrado.empty and 'SEXO' in df_filtrado.columns:

            sexo_counts = df_filtrado['SEXO'].value_counts()

            fig_sexo = px.pie(sexo_counts, values=sexo_counts.values, names=sexo_counts.index)

            fig_sexo.update_layout(margin=dict(l=0, r=0, t=0, b=0), showlegend=False, height=200)

            fig_sexo.update_traces(textposition='inside', textinfo='percent+label')

            st.plotly_chart(fig_sexo, use_container_width=True)

   

    st.markdown("---")

   

    st.subheader("Análise de Recursos e Demanda")

    col_esp, col_conv = st.columns(2)

    # Gráficos de barra

    with col_esp:

        top_especialidades = df_filtrado['DS_ESPECIALID'].value_counts().nlargest(15).sort_values(ascending=True)

        fig_esp = px.bar(top_especialidades, x=top_especialidades.values, y=top_especialidades.index, orientation='h',

                         title='Top 15 Especialidades Mais Demandadas', labels={'x': 'Nº de Atendimentos', 'y': 'Especialidade'},

                         color_discrete_sequence=px.colors.sequential.Blues_r)

        st.plotly_chart(fig_esp, use_container_width=True)

    with col_conv:

        top_convenios = df_filtrado['NM_CONVENIO'].value_counts().nlargest(15)

        fig_conv = px.bar(top_convenios, x=top_convenios.index, y=top_convenios.values,

                          title='Top 15 Atendimentos por Convênio', labels={'x': 'Convênio', 'y': 'Nº de Atendimentos'},

                          color_discrete_sequence=px.colors.sequential.Blues_r)

        st.plotly_chart(fig_conv, use_container_width=True)

       

    st.markdown("---")

   

    with st.expander("Análise Demográfica por Faixa Etária", expanded=True):

        if not df_filtrado.empty:

            bins = [0, 9, 19, 29, 39, 49, 59, 69, 79, 120]

            labels = ['0-9', '10-19', '20-29', '30-39', '40-49', '50-59', '60-69', '70-79', '80+']

            df_filtrado['Faixa Etaria'] = pd.cut(df_filtrado['IDADE'], bins=bins, labels=labels, right=True)



            df_piramide = df_filtrado.groupby(['Faixa Etaria', 'SEXO']).size().reset_index(name='Contagem')

           

            df_piramide_pivot = df_piramide.pivot(index='Faixa Etaria', columns='SEXO', values='Contagem').fillna(0)

            if 'MASCULINO' in df_piramide_pivot.columns:

                df_piramide_pivot['MASCULINO'] = -1 * df_piramide_pivot['MASCULINO']



            fig_piramide = go.Figure()

            if 'MASCULINO' in df_piramide_pivot.columns:

                fig_piramide.add_trace(go.Bar(

                    y=df_piramide_pivot.index, x=df_piramide_pivot['MASCULINO'],

                    name='Masculino', orientation='h', marker=dict(color="#83c9ff")))

            if 'FEMININO' in df_piramide_pivot.columns:

                fig_piramide.add_trace(go.Bar(

                    y=df_piramide_pivot.index, x=df_piramide_pivot['FEMININO'],

                    name='Feminino', orientation='h', marker=dict(color="#0068c9")))



            max_val = max(abs(df_piramide_pivot.min().min()), abs(df_piramide_pivot.max().max())) if not df_piramide_pivot.empty else 10

            fig_piramide.update_layout(

                title='Pirâmide Etária dos Atendimentos',

                xaxis=dict(

                    tickvals=[-max_val, -max_val/2, 0, max_val/2, max_val],

                    ticktext=[f'{max_val:,.0f}'.replace(",", "."), f'{max_val/2:,.0f}'.replace(",", "."), '0', f'{max_val/2:,.0f}'.replace(",", "."), f'{max_val:,.0f}'.replace(",", ".")],

                    title='Contagem de Pacientes'

                ),

                yaxis_title='Faixa Etária', barmode='overlay', bargap=0.1,

                legend=dict(x=0, y=1.1, orientation="h")

            )

            st.plotly_chart(fig_piramide, use_container_width=True)

        else:

            st.warning("Nenhum dado disponível para gerar a pirâmide etária.")



# --- Conteúdo da Aba 2: Análise Epidemiológica ---

with tab2:

    with st.expander("🗺️ Análise Geográfica por Município", expanded=True):

        @st.cache_data

        def carregar_geojson():

            try:

                with open('geojson_es.json', 'r', encoding='utf-8') as f: return json.load(f)

            except FileNotFoundError: return None

        geojson_es = carregar_geojson()



        if geojson_es:

            for feature in geojson_es['features']:

                nome_municipio = feature['properties']['name']

                nome_normalizado = unicodedata.normalize('NFKD', nome_municipio).encode('ascii', 'ignore').decode('utf-8')

                feature['id'] = nome_normalizado.upper()

           

            atendimentos_por_municipio = df_filtrado['MUNICIPIO'].value_counts().reset_index()

            atendimentos_por_municipio.columns = ['MUNICIPIO', 'ATENDIMENTOS']

            atendimentos_por_municipio['MUNICIPIO_NORMALIZADO'] = atendimentos_por_municipio['MUNICIPIO'].str.upper().str.normalize('NFKD').str.encode('ascii', 'ignore').str.decode('utf-8')



            fig_mapa = px.choropleth_mapbox(

                atendimentos_por_municipio, geojson=geojson_es, locations='MUNICIPIO_NORMALIZADO', featureidkey="id",

                color='ATENDIMENTOS', color_continuous_scale="Redor", mapbox_style="open-street-map",

                zoom=7, center={"lat": -19.55, "lon": -40.3428}, opacity=0.7,

                labels={'ATENDIMENTOS': 'Nº de Atendimentos'}, hover_name='MUNICIPIO')

           

            fig_mapa.update_layout(margin={"r":0, "t":0, "l":0, "b":0}, height=800)

            st.plotly_chart(fig_mapa, use_container_width=True)

        else:

            st.error("Arquivo `geojson_es.json` não encontrado!")



    with st.expander(f"📈 Análise Temporal", expanded=True):

        # --- MODIFICAÇÃO: Filtro de agregação movido para dentro do expander ---

        agregacao = st.radio(

            "Visualizar por:",

            ('Dia', 'Semana', 'Mês'),

            key='agregacao_tempo_tab2',

            horizontal=True # Deixa os botões na horizontal

        )

       

        df_temporal = df_filtrado.set_index('DT_ATENDIMENTO')

        if not df_temporal.empty:

            if agregacao == 'Dia':

                dados_agrupados = df_temporal.resample('D').size().reset_index(name='Nº de Atendimentos')

            elif agregacao == 'Semana':

                dados_agrupados = df_temporal.resample('W-Mon').size().reset_index(name='Nº de Atendimentos')

            else:

                dados_agrupados = df_temporal.resample('ME').size().reset_index(name='Nº de Atendimentos')

            dados_agrupados.rename(columns={'DT_ATENDIMENTO': 'Período'}, inplace=True)

            fig_linha = px.line(dados_agrupados, x='Período', y='Nº de Atendimentos', title=f'Atendimentos por {agregacao}')

            fig_linha.update_layout(xaxis_title='Período', yaxis_title='Número de Atendimentos')

            st.plotly_chart(fig_linha, use_container_width=True)

        else:

            st.warning("Nenhum dado encontrado para o período e filtros selecionados.")
