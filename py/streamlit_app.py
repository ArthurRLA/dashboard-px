import streamlit as st
import pandas as pd
# Não precisamos mais importar plotly.express e plotly.graph_objects
# diretamente, pois eles estão encapsulados no módulo charts.

# -------------------------------------------------------------
# IMPORTAÇÕES DOS MÓDULOS MODULARIZADOS
# -------------------------------------------------------------
from data_loader import load_shop_config, load_data 
from kpi_processor import create_dynamic_kpi_dataframe, calculate_kpis_chave
from charts import create_ranking_chart, create_produtos_chart, create_performance_chart, create_penetracao_chart


# ==============================================================================
# 0. DEFINIÇÕES GLOBAIS
# ==============================================================================

MESES = ['Janeiro/25', 'Fevereiro/25', 'Março/25', 'Abril/25']


# -------------------------------------------------------------
# FLUXO DE FILTROS E CARREGAMENTO DE DADOS
# -------------------------------------------------------------

# 1. Configuração da Loja e Filtro Hierárquico (chama data_loader)
shop_config_hierarchical = load_shop_config()
regioes = list(shop_config_hierarchical.keys())

st.sidebar.header('Dashboard POWERX')
st.sidebar.subheader('Seleção de Região e Lojas')

# FILTRO 1: REGIÃO
regiao_selecionada = st.sidebar.selectbox(
    'Selecione a Região',
    options=regioes
)

lojas_da_regiao = list(shop_config_hierarchical[regiao_selecionada].keys())

# FILTRO 2: LOJAS MÚLTIPLAS
lojas_selecionadas = st.sidebar.multiselect(
    'Filtrar Loja(s)',
    options=lojas_da_regiao,
    default=lojas_da_regiao # Seleciona todas por padrão
)

loja_paths = [shop_config_hierarchical[regiao_selecionada][loja] for loja in lojas_selecionadas]


# 2. Carregamento de Dados (chama data_loader)
df_data = load_data(loja_paths, lojas_selecionadas)
df_totais, df_produtos, consultores_da_regiao, KPI_MAP = df_data

titulo_lojas = ', '.join(lojas_selecionadas) if len(lojas_selecionadas) < 4 else f"{len(lojas_selecionadas)} Lojas em {regiao_selecionada}"

if df_totais.empty or not consultores_da_regiao:
    st.error(f"Não foi possível carregar dados para: {titulo_lojas}. Verifique os arquivos.")
    st.stop()
    

# 3. Criação dos DataFrames de Série (chama kpi_processor)
df_kpis_series = {}
for kpi_name, kpi_info in KPI_MAP.items():
    df = create_dynamic_kpi_dataframe(df_totais, consultores_da_regiao, kpi_name, kpi_info)
    df_kpis_series[kpi_name] = df

# 4. Referências e Cálculo dos KPIs Chave (chama kpi_processor)
KPI_DATAFRAME_MAP = {
    name: {'df': df_kpis_series[name], 'col': info['new_col'], 'alias': name}
    for name, info in KPI_MAP.items()
}

df_venda_rs = KPI_DATAFRAME_MAP['VENDA R$']['df']
df_performance = KPI_DATAFRAME_MAP['PERFORMANCE']['df']
df_ticket_medio = KPI_DATAFRAME_MAP['TICKET MÉDIO']['df']
df_produtos_consultor = KPI_DATAFRAME_MAP['TOTAL DE PRODUTOS']['df']

kpis_chave = calculate_kpis_chave(df_venda_rs, df_performance, df_ticket_medio, df_produtos_consultor)


# ==============================================================================
# 5. BARRA LATERAL (SIDEBAR) COM FILTROS DE VISUALIZAÇÃO
# ==============================================================================

st.sidebar.markdown('---') 

st.sidebar.subheader('Métricas e Visualização')

mes_selecionado = st.sidebar.selectbox(
    'Período (Fixo)',
    options=MESES,
    index=3
)

consultor_selecionado = st.sidebar.multiselect(
    'Filtrar Consultor(es)',
    options=consultores_da_regiao, 
    default=consultores_da_regiao 
)

st.sidebar.markdown('---')

st.sidebar.subheader('Métrica de Ranking')
kpi_selecionado = st.sidebar.selectbox(
    'Visualizar Ranking por:',
    options=list(KPI_DATAFRAME_MAP.keys()),
    index=2 
)

plot_height = st.sidebar.slider(
    'Ajustar Altura dos Gráficos',
    250, 500, 350
)

# ==============================================================================
# 6. CORPO PRINCIPAL DO DASHBOARD E GRÁFICOS
# ==============================================================================

st.title(f'📊 Painel de Indicadores de Vendas POWERX')
st.subheader(f'Região: {regiao_selecionada} | Lojas: {titulo_lojas}')
st.caption(f'Dados Consolidados | Período: **{mes_selecionado}**')

st.markdown('---')

# Exibição dos KPIs Chave
col1, col2, col3, col4 = st.columns(4)
kpis = kpis_chave
col1.metric("Venda Total (R$)", f"R$ {kpis['Venda Total (R$)']:,.2f}")
col2.metric("Performance Média", f"{kpis['Performance Média']:.2f} p/p")
col3.metric("Ticket Médio (R$)", f"R$ {kpis['Ticket Médio (R$)']:,.2f}")
col4.metric("Total de Produtos", f"{int(kpis['Total de Produtos'])} un.")

st.markdown('---')

# --------------------------
# GRÁFICO 1: RANKING DINÂMICO REGIONAL (chama charts.py)
# --------------------------

st.subheader(f'Ranking de Vendas: {kpi_selecionado} por Consultor (Agregado)')

selected_kpi_info = KPI_DATAFRAME_MAP[kpi_selecionado]
df_current_kpi = selected_kpi_info['df']
value_col_name = selected_kpi_info['col']

df_ranking_filtered = df_current_kpi[df_current_kpi['Consultor'].isin(consultor_selecionado)]

fig_ranking = create_ranking_chart(df_ranking_filtered, kpi_selecionado, value_col_name, plot_height)
st.plotly_chart(fig_ranking, use_container_width=True)

st.markdown('---')

# --------------------------
# GRÁFICOS 2 & 3: TOTAL DE PRODUTOS/CONSULTOR & PERFORMANCE (chama charts.py)
# --------------------------

# GRÁFICO 2: TOTAL DE PRODUTOS/CONSULTOR 
if kpi_selecionado != 'TOTAL DE PRODUTOS':
    st.subheader('Total de Produtos/consultor (Agregado)')
    fig_produtos = create_produtos_chart(df_produtos_consultor, consultor_selecionado)
    st.plotly_chart(fig_produtos, use_container_width=True)
    st.markdown('---')


# GRÁFICO 3: PERFORMANCE: produtos/passagem
st.subheader('Performance: produtos/passagem (Agregado)')
fig_performance = create_performance_chart(df_performance, consultor_selecionado)
st.plotly_chart(fig_performance, use_container_width=True)

st.markdown('---')

# --------------------------
# GRÁFICO 4: PENETRAÇÃO PRODUTO/OS (chama charts.py)
# --------------------------

st.subheader('Penetração Produto/OS (Share de Produtos Vendidos)')

col_penetracao, col_info = st.columns([2, 1])

with col_penetracao:
    fig_penetracao = create_penetracao_chart(df_produtos)
    st.plotly_chart(fig_penetracao, use_container_width=True)

with col_info:
    st.markdown("##### Informações de Penetração")
    
    st.info(
        "Este gráfico exibe a distribuição baseada na coluna 'Penetracao_Produto' do CSV. "
        "Os dados são agregados de todas as lojas selecionadas."
    )
    if not df_produtos.empty:
        produto_lider = df_produtos.iloc[df_produtos['Penetracao_Produto'].argmax()]
        st.metric("Produto Líder", produto_lider['Produto'], 
                  f"{produto_lider['Penetracao_Produto']:.2f}")
    else:
        st.warning("Dados de produto indisponíveis.")