"""
Dashboard PowerX - Versão XLSX
Adaptado para trabalhar com dados transacionais do Excel.
"""

import streamlit as st
import pandas as pd

# Imports dos novos módulos
from data_loader import load_shop_config, load_data
from kpi_processor import (
    create_kpi_dataframe_map,
    calculate_kpis_chave,
    get_consultores_list,
    filter_metricas_por_consultor
)
from charts import (
    create_ranking_chart,
    create_produtos_chart,
    create_performance_chart,
    create_penetracao_chart
)

# ==============================================================================
# 0. CONFIGURAÇÃO
# ==============================================================================

MESES = ['Janeiro/25', 'Fevereiro/25', 'Março/25', 'Abril/25']

# ==============================================================================
# 1. SIDEBAR - FILTROS DE REGIÃO E LOJAS
# ==============================================================================

st.sidebar.header('Dashboard POWERX')
st.sidebar.subheader('Seleção de Região e Lojas')

# Carrega configuração de lojas
shop_config_hierarchical = load_shop_config()
regioes = list(shop_config_hierarchical.keys())

# Filtro 1: Região
regiao_selecionada = st.sidebar.selectbox(
    'Selecione a Região',
    options=regioes
)

lojas_da_regiao = list(shop_config_hierarchical[regiao_selecionada].keys())

# Filtro 2: Lojas Múltiplas
lojas_selecionadas = st.sidebar.multiselect(
    'Filtrar Loja(s)',
    options=lojas_da_regiao,
    default=lojas_da_regiao
)

# Prepara configurações para carregar dados
loja_configs = []
for loja in lojas_selecionadas:
    config = shop_config_hierarchical[regiao_selecionada][loja].copy()
    config['name'] = loja
    loja_configs.append(config)

# ==============================================================================
# 2. CARREGAMENTO DE DADOS
# ==============================================================================

if not loja_configs:
    st.warning("⚠️ Selecione pelo menos uma loja para visualizar os dados.")
    st.stop()

# Carrega dados (com cache)
df_metricas_vendedor, df_metricas_produto, lista_consultores = load_data(loja_configs)

# Título para exibição
titulo_lojas = ', '.join(lojas_selecionadas) if len(lojas_selecionadas) < 4 else f"{len(lojas_selecionadas)} Lojas em {regiao_selecionada}"

# Validação
if df_metricas_vendedor.empty:
    st.error(f"❌ Não foi possível carregar dados para: {titulo_lojas}")
    st.stop()

# ==============================================================================
# 3. PROCESSAMENTO DE KPIs
# ==============================================================================

# Cria mapeamento de KPIs (formato compatível com código antigo)
KPI_DATAFRAME_MAP = create_kpi_dataframe_map(df_metricas_vendedor)

# Extrai DataFrames individuais de KPI
df_venda_rs = KPI_DATAFRAME_MAP['TOTAL VENDA RS']['df']
df_performance = KPI_DATAFRAME_MAP['PERFORMANCE']['df']
df_ticket_medio = KPI_DATAFRAME_MAP['TKT MÉDIO SELL OUT']['df']
df_produtos_consultor = KPI_DATAFRAME_MAP['TOTAL DE PRODUTOS']['df']

# Calcula KPIs principais (cards do topo)
kpis_chave = calculate_kpis_chave(df_metricas_vendedor)

# ==============================================================================
# 4. SIDEBAR - FILTROS DE VISUALIZAÇÃO
# ==============================================================================

st.sidebar.markdown('---')
st.sidebar.subheader('Métricas e Visualização')

mes_selecionado = st.sidebar.selectbox(
    'Período (Fixo)',
    options=MESES,
    index=3
)

# Filtro de consultores (agora baseado nos dados reais)
consultor_selecionado = st.sidebar.multiselect(
    'Filtrar Consultor(es)',
    options=lista_consultores,
    default=lista_consultores
)

st.sidebar.markdown('---')

st.sidebar.subheader('Métrica de Ranking')
kpi_selecionado = st.sidebar.selectbox(
    'Visualizar Ranking por:',
    options=list(KPI_DATAFRAME_MAP.keys()),
    index=2  # Default: VENDA RS
)

plot_height = st.sidebar.slider(
    'Ajustar Altura dos Gráficos',
    250, 500, 350
)

# ==============================================================================
# 5. CORPO PRINCIPAL - CABEÇALHO
# ==============================================================================

st.title(f'📊 Painel de Indicadores de Vendas POWERX')
st.subheader(f'Região: {regiao_selecionada} | Lojas: {titulo_lojas}')
st.caption(f'Dados Consolidados | Período: **{mes_selecionado}**')

st.markdown('---')

# ==============================================================================
# 6. KPIs PRINCIPAIS (Cards do Topo)
# ==============================================================================

col1, col2, col3, col4 = st.columns(4)

venda_total = kpis_chave.get('Venda Total (R$)', 0)
performance_media = kpis_chave.get('Performance Média', 0)
ticket_medio = kpis_chave.get('Ticket Médio (R$)', 0)
total_produtos = kpis_chave.get('Total de Produtos', 0)

# Formatação brasileira de moeda
def format_brl(valor):
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

col1.metric("Venda Total (R$)", format_brl(venda_total))
col2.metric("Performance Média", f"{performance_media:.2f} p/p")
col3.metric("Ticket Médio (R$)", format_brl(ticket_medio))
col4.metric("Total de Produtos", f"{int(total_produtos)} un.")

# Alerta se valores estão zerados
if venda_total == 0 and performance_media == 0 and ticket_medio == 0:
    st.warning("⚠️ Os KPIs principais estão zerados. Verifique os dados carregados.")

st.markdown('---')

# ==============================================================================
# 7. GRÁFICO 1: RANKING DINÂMICO
# ==============================================================================

st.subheader(f'Ranking de Vendas: {kpi_selecionado} por Consultor (Agregado)')

selected_kpi_info = KPI_DATAFRAME_MAP[kpi_selecionado]
df_current_kpi = selected_kpi_info['df']
value_col_name = selected_kpi_info['col']

# Filtra por consultores selecionados
df_ranking_filtered = df_current_kpi[df_current_kpi['Consultor'].isin(consultor_selecionado)]

if not df_ranking_filtered.empty:
    fig_ranking = create_ranking_chart(df_ranking_filtered, kpi_selecionado, value_col_name, plot_height)
    st.plotly_chart(fig_ranking, use_container_width=True)
else:
    st.info("ℹ️ Nenhum dado disponível para os filtros selecionados.")

st.markdown('---')

# ==============================================================================
# 8. GRÁFICO 2: TOTAL DE PRODUTOS POR CONSULTOR
# ==============================================================================

if kpi_selecionado != 'TOTAL DE PRODUTOS':
    st.subheader('Total de Produtos/consultor (Agregado)')
    
    df_produtos_filtered = df_produtos_consultor[df_produtos_consultor['Consultor'].isin(consultor_selecionado)]
    
    if not df_produtos_filtered.empty:
        fig_produtos = create_produtos_chart(df_produtos_filtered, consultor_selecionado)
        st.plotly_chart(fig_produtos, use_container_width=True)
    
    st.markdown('---')

# ==============================================================================
# 9. GRÁFICO 3: PERFORMANCE (produtos/passagem)
# ==============================================================================

st.subheader('Performance: produtos/passagem (Agregado)')

df_performance_filtered = df_performance[df_performance['Consultor'].isin(consultor_selecionado)]

if not df_performance_filtered.empty:
    fig_performance = create_performance_chart(df_performance_filtered, consultor_selecionado)
    st.plotly_chart(fig_performance, use_container_width=True)
else:
    st.info("ℹ️ Nenhum dado de performance disponível.")

st.markdown('---')

# ==============================================================================
# 10. GRÁFICO 4: PENETRAÇÃO DE PRODUTOS
# ==============================================================================

st.subheader('Penetração Produto/OS (Share de Produtos Vendidos)')

col_penetracao, col_info = st.columns([2, 1])

with col_penetracao:
    if not df_metricas_produto.empty:
        # Renomeia colunas para compatibilidade com função de chart
        df_produtos_chart = df_metricas_produto[['Descricao', 'Penetracao_Produto']].copy()
        
        fig_penetracao = create_penetracao_chart(df_produtos_chart)
        st.plotly_chart(fig_penetracao, use_container_width=True)
    else:
        st.info("ℹ️ Nenhum dado de produto disponível.")

with col_info:
    st.markdown("##### Informações de Penetração")
    
    st.info(
        "Este gráfico exibe a distribuição de produtos vendidos. "
        "Os dados são agregados de todas as lojas selecionadas."
    )
    
    if not df_metricas_produto.empty:
        produto_lider = df_metricas_produto.loc[df_metricas_produto['Penetracao_Produto'].idxmax()]
        st.metric(
            "Produto Líder",
            produto_lider['Descricao'],
            f"{produto_lider['Penetracao_Produto']:.2f}%"
        )
    else:
        st.warning("Dados de produto indisponíveis.")

# ==============================================================================
# 11. SEÇÃO DE DEBUG (Expansível)
# ==============================================================================

with st.expander("🔍 Debug: Métricas Detalhadas", expanded=False):
    st.write("### Métricas por Vendedor")
    st.dataframe(df_metricas_vendedor)
    
    st.write("### Top 10 Produtos")
    st.dataframe(df_metricas_produto.head(10))
    
    st.write("### KPIs Chave")
    st.json(kpis_chave)