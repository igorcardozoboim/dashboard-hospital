import streamlit as st
import pandas as pd
import plotly.express as px
import json
import unicodedata

# Configuração da página do dashboard para um layout amplo
st.set_page_config(layout="wide")

# Título do Dashboard
st.title('Dashboard de Gestão Epidemiológica')

# --- Carregamento e Preparação dos Dados ---
@st.cache_data
def carregar_dados():
    # --- MODIFICAÇÃO: Nome do arquivo atualizado para a versão compacta final ---
    try:
        # Tenta ler o novo arquivo .zip com o separador ';'
        df = pd.read_csv('epidemio_2024_2025_compacta.zip', encoding='utf-8', delimiter=';')
    except FileNotFoundError:
        st.error("Arquivo 'epidemio_2024_2025_compacta.zip' não encontrado. Certifique-se de que ele está no repositório do GitHub.")
        return pd.DataFrame()

    # Lógica de conversão de data
    date_series = df['DT_ATENDIMENTO'].astype(str).str.split().str[0]
    df['DT_ATENDIMENTO'] = pd.to_datetime(date_series, format='%d/%m/%Y', errors='coerce')
    
    return df

df = carregar_dados()

# --- Barra Lateral de Filtros ---
st.sidebar.header('Filtros Interativos')

if st.sidebar.button('Limpar Cache e Recarregar Dados'):
    st.cache_data.clear()
    st.rerun()

# Contagem e seleção de CIDs relevantes
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

# Painel de diagnóstico na barra lateral
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

# --- MODIFICAÇÃO 1: KPIs (Indicadores Chave) ---
st.markdown("---")
st.subheader("Resumo do Período e Filtros Selecionados")

# Cálculos dos KPIs
total_atendimentos = len(df_filtrado)
pacientes_unicos = df_filtrado['CD_PACIENTE'].nunique()
media_idade = int(df_filtrado['IDADE'].mean()) if not df_filtrado.empty else 0

# Layout em colunas para os KPIs
col1, col2, col3 = st.columns(3)
col1.metric("Total de Atendimentos", f"{total_atendimentos:,}".replace(",", "."))
col2.metric("Nº de Pacientes Únicos", f"{pacientes_unicos:,}".replace(",", "."))
col3.metric("Média de Idade dos Pacientes", f"{media_idade} anos")
st.markdown("---")

# --- MODIFICAÇÃO 2: Análise de Recursos e Demanda ---

st.subheader("Análise de Recursos e Demanda")
col_esp, col_conv = st.columns(2)

with col_esp:
    # Gráfico de Especialidades
    top_especialidades = df_filtrado['DS_ESPECIALID'].value_counts().nlargest(15).sort_values(ascending=True)
    fig_esp = px.bar(
        top_especialidades,
        x=top_especialidades.values,
        y=top_especialidades.index,
        orientation='h',
        title='Top 15 Especialidades Mais Demandadas',
        labels={'x': 'Nº de Atendimentos', 'y': 'Especialidade'}
    )
    fig_esp.update_layout(showlegend=False)
    st.plotly_chart(fig_esp, use_container_width=True)

with col_conv:
    # Gráfico de Convênios
    top_convenios = df_filtrado['NM_CONVENIO'].value_counts().nlargest(15)
    fig_conv = px.bar(
        top_convenios,
        x=top_convenios.index,
        y=top_convenios.values,
        title='Top 15 Atendimentos por Convênio',
        labels={'x': 'Convênio', 'y': 'Nº de Atendimentos'},
        color_discrete_sequence=px.colors.sequential.Tealgrn
    )
    st.plotly_chart(fig_conv, use_container_width=True)
st.markdown("---")


# --- Gráficos Epidemiológicos (Mapa e Linha do Tempo) ---
st.subheader('Análise Epidemiológica')

# Carregamento do GeoJSON
@st.cache_data
def carregar_geojson():
    try:
        with open('geojson_es.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

geojson_es = carregar_geojson()

# Mapa
if geojson_es is None:
    st.error("Arquivo `geojson_es.json` não encontrado!")
else:
    # Adiciona um ID normalizado ao GeoJSON
    for feature in geojson_es['features']:
        nome_municipio = feature['properties']['name']
        nome_normalizado = unicodedata.normalize('NFKD', nome_municipio).encode('ascii', 'ignore').decode('utf-8')
        feature['id'] = nome_normalizado.upper()
        
    atendimentos_por_municipio = df_filtrado['MUNICIPIO'].value_counts().reset_index()
    atendimentos_por_municipio.columns = ['MUNICIPIO', 'ATENDIMENTOS']
    atendimentos_por_municipio['MUNICIPIO_NORMALIZADO'] = atendimentos_por_municipio['MUNICIPIO'].str.upper().str.normalize('NFKD').str.encode('ascii', 'ignore').str.decode('utf-8')

    fig_mapa = px.choropleth_mapbox(
        atendimentos_por_municipio,
        geojson=geojson_es,
        locations='MUNICIPIO_NORMALIZADO',
        featureidkey="id",
        color='ATENDIMENTOS',
        color_continuous_scale="Redor",
        mapbox_style="open-street-map",
        zoom=7,
        center={"lat": -19.55, "lon": -40.3428},
        opacity=0.7,
        labels={'ATENDIMENTOS': 'Nº de Atendimentos'},
        hover_name='MUNICIPIO'
    )
    fig_mapa.update_layout(title_text='Distribuição Geográfica dos Atendimentos', margin={"r":0, "t":40, "l":0, "b":0}, height=700)
    st.plotly_chart(fig_mapa, use_container_width=True)

# Gráfico de Linha Temporal
st.subheader(f'Volume de Atendimentos por {agregacao}')
df_temporal = df_filtrado.set_index('DT_ATENDIMENTO')
if agregacao == 'Dia':
    dados_agrupados = df_temporal.resample('D').size().reset_index(name='Nº de Atendimentos')
elif agregacao == 'Semana':
    dados_agrupados = df_temporal.resample('W-Mon').size().reset_index(name='Nº de Atendimentos')
else: # Mês
    dados_agrupados = df_temporal.resample('ME').size().reset_index(name='Nº de Atendimentos')

dados_agrupados.rename(columns={'DT_ATENDIMENTO': 'Período'}, inplace=True)
fig_linha = px.line(
    dados_agrupados,
    x='Período',
    y='Nº de Atendimentos',
    title=f'Atendimentos por {agregacao}'
)
fig_linha.update_layout(xaxis_title='Período', yaxis_title='Número de Atendimentos')
st.plotly_chart(fig_linha, use_container_width=True)