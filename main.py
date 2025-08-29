import streamlit as st
import pandas as pd
import plotly.express as px
import json
import unicodedata

# Configuração da página do dashboard
st.set_page_config(layout="wide")

# Título do Dashboard
st.title('Dashboard de Gestão Epidemiológica')
st.title('Dashboard de Gestão Epidemiológica do Hospital Santa Rita de Cássia do período de 01/01/2024 a 31/07/2025')

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

    return df

df = carregar_dados()

# --- Barra Lateral de Filtros ---
st.sidebar.header('Filtros Interativos')
if st.sidebar.button('Limpar Cache e Recarregar Dados'):
    st.cache_data.clear()
    st.rerun()

cid_counts = df['DESCRICAO_CID'].value_counts()
cids_relevantes = cid_counts[cid_counts >= 1000].index.tolist()
cids_selecionados = st.sidebar.multiselect(
    'Selecione um ou mais CIDs (com >= 1000 casos):',
    options=sorted(cids_relevantes), 
    default=[]
)
agregacao = st.sidebar.radio(
    "Agregar dados de tempo por:",
    ('Dia', 'Semana', 'Mês'),
    key='agregacao_tempo'
)
with st.sidebar.expander("Diagnóstico de Dados"):
    df_datas_validas = df.dropna(subset=['DT_ATENDIMENTO'])
    st.write(f"Total de registros: **{len(df)}**")
    if not df_datas_validas.empty:
        min_date = df_datas_validas['DT_ATENDIMENTO'].min().date()
        max_date = df_datas_validas['DT_ATENDIMENTO'].max().date()
        st.write(f"Período identificado: **{min_date.strftime('%d/%m/%Y')}** a **{max_date.strftime('%d/%m/%Y')}**")

# --- Lógica de Filtragem ---
if cids_selecionados:
    df_filtrado = df[df['DESCRICAO_CID'].isin(cids_selecionados)]
else:
    df_filtrado = df.copy()
df_filtrado = df_filtrado.dropna(subset=['DT_ATENDIMENTO'])

# --- KPIs e Novo Gráfico de Pizza ---
st.markdown("---")
st.subheader("Resumo do Período e Filtros Selecionados")

# --- MODIFICAÇÃO: Layout alterado para 4 colunas ---
col1, col2, col3, col4 = st.columns(4)

# Coluna 1: Total de Atendimentos
total_atendimentos = len(df_filtrado)
col1.metric("Total de Atendimentos", f"{total_atendimentos:,}".replace(",", "."))

# Coluna 2: Pacientes Únicos
pacientes_unicos = df_filtrado['CD_PACIENTE'].nunique()
col2.metric("Nº de Pacientes Únicos", f"{pacientes_unicos:,}".replace(",", "."))

# Coluna 3: Média de Idade
media_idade = int(df_filtrado['IDADE'].mean()) if not df_filtrado.empty else 0
col3.metric("Média de Idade dos Pacientes", f"{media_idade} anos")

# Coluna 4 com o novo gráfico de pizza
with col4:
    if not df_filtrado.empty:
        sexo_counts = df_filtrado['SEXO'].value_counts()
        fig_sexo = px.pie(
            sexo_counts,
            values=sexo_counts.values,
            names=sexo_counts.index,
            color_discrete_sequence=["#B9A6FF", "#4038A8"] # Rosa e Azul
        )
        # Ajustes para deixar o gráfico mais compacto
        fig_sexo.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            showlegend=False,
            height=200 # Define uma altura menor
        )
        # Adiciona os percentuais dentro das fatias
        fig_sexo.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_sexo, use_container_width=True)

st.markdown("---")


# --- Análise de Recursos e Demanda ---
st.subheader("Análise de Recursos e Demanda")
col_esp, col_conv = st.columns(2)
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

# --- Análise Epidemiológica Detalhada ---
st.subheader('Análise Epidemiológica Detalhada')

# Expander para o Mapa Geográfico
with st.expander("🗺️ Análise Geográfica por Município", expanded=True):
    # Carregamento do GeoJSON
    @st.cache_data
    def carregar_geojson():
        try:
            with open('geojson_es.json', 'r', encoding='utf-8') as f: return json.load(f)
        except FileNotFoundError: return None
    geojson_es = carregar_geojson()

    if geojson_es:
        # ... (código do mapa continua o mesmo) ...
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
        fig_mapa.update_layout(margin={"r":0, "t":0, "l":0, "b":0}, height=700) # Mantemos a altura aqui, pois o expander controla a rolagem
        st.plotly_chart(fig_mapa, use_container_width=True)
    else:
        st.error("Arquivo `geojson_es.json` não encontrado!")

with st.expander(f"📈 Análise Temporal por {agregacao}", expanded=True):
    df_temporal = df_filtrado.set_index('DT_ATENDIMENTO')
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
