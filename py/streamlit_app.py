import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from config_loader import config

from db_connector import db
from data_loader import (
    load_shop_config_from_db,
    load_data,
    get_date_range_from_db
)

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
    create_penetracao_chart,
    create_evolucao_temporal_chart
)

settings = config.get_settings()
ui_config = settings.get('ui', {})

st.set_page_config(
    page_title=ui_config.get('titulo', 'Dashboard PowerX'),
    page_icon=ui_config.get('icone_pagina', '📊'),
    layout=ui_config.get('layout', 'wide')
)

if not db.test_connection():
    st.error("Não foi possível conectar ao PostgreSQL")
    st.info(
        "**Verifique:**\n"
        "- Credenciais em `.streamlit/secrets.toml`\n"
        "- PostgreSQL está rodando\n"
        "- Firewall permite conexão\n"
        "- IP/Porta corretos"
    )
    st.stop()


st.sidebar.header('Dashboard POWERX')
st.sidebar.subheader('Seleção de Grupo e Lojas')

shop_config = load_shop_config_from_db()

if not shop_config:
    st.error("Não foi possível carregar lojas do banco de dados")
    st.stop()

grupos = list(shop_config.keys())

if not grupos:
    st.error("Nenhum grupo encontrado com vendas")
    st.stop()

grupo_selecionado = st.sidebar.selectbox(
    'Selecione o Grupo',
    options=grupos,
    index=0
)

lojas_do_grupo = list(shop_config[grupo_selecionado].keys())

lojas_selecionadas = st.sidebar.multiselect(
    'Filtrar Loja(s)',
    options=lojas_do_grupo,
    default=lojas_do_grupo
)

lojas_configs = [
    {
        'id': shop_config[grupo_selecionado][loja]['id'],
        'nome': loja,
        'cnpj': shop_config[grupo_selecionado][loja].get('cnpj', '')
    }
    for loja in lojas_selecionadas
]


st.sidebar.markdown('---')
st.sidebar.subheader('Período de Análise')

data_min, data_max = get_date_range_from_db()

hoje = datetime.now().date()
primeiro_dia_mes_atual = hoje.replace(day=1)
ultimo_dia_mes_anterior = primeiro_dia_mes_atual - timedelta(days=1)
primeiro_dia_mes_anterior = ultimo_dia_mes_anterior.replace(day=1)
data_fim_default = min(ultimo_dia_mes_anterior, data_max)
data_inicio_default = max(primeiro_dia_mes_anterior, data_min)

col1, col2 = st.sidebar.columns(2)

with col1:
    data_inicio = st.date_input(
        "De",
        value=data_inicio_default,
        min_value=data_min,
        max_value=data_max,
        help="Data inicial do período"
    )

with col2:
    data_fim = st.date_input(
        "Até",
        value=data_fim_default,
        min_value=data_min,
        max_value=data_max,
        help="Data final do período"
    )


if data_inicio > data_fim:
    st.sidebar.error("Data inicial deve ser anterior à data final")
    st.stop()


if not lojas_configs:
    st.warning("Selecione pelo menos uma loja para visualizar os dados")
    st.stop()

df_metricas_vendedor, df_metricas_produto, df_metricas_temporais, lista_consultores = load_data(
    lojas_configs,
    data_inicio,
    data_fim
)

titulo_lojas = ', '.join(lojas_selecionadas) if len(lojas_selecionadas) < 4 else f"{len(lojas_selecionadas)} Lojas"

if df_metricas_vendedor.empty:
    st.warning(
        f"**Sem dados** para **{titulo_lojas}** no período "
        f"**{data_inicio.strftime('%d/%m/%Y')}** até **{data_fim.strftime('%d/%m/%Y')}**"
    )
    st.info("Procure uma nova data ou nova loja ou sei lá")
    st.stop()

KPI_DATAFRAME_MAP = create_kpi_dataframe_map(df_metricas_vendedor)

df_venda_rs = KPI_DATAFRAME_MAP['TOTAL VENDA RS']['df']
df_performance = KPI_DATAFRAME_MAP['PERFORMANCE']['df']
df_ticket_medio = KPI_DATAFRAME_MAP['TKT MÉDIO SELL OUT']['df']
df_produtos_consultor = KPI_DATAFRAME_MAP['TOTAL DE PRODUTOS']['df']

kpis_chave = calculate_kpis_chave(df_metricas_vendedor)


st.sidebar.markdown('---')
st.sidebar.subheader('Métricas e Visualização')

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
    index=1
)

plot_height = st.sidebar.slider(
    'Ajustar Altura dos Gráficos',
    250, 500, 350
)


st.title(f'📊 Painel de Indicadores de Vendas POWERX')
st.subheader(f'Grupo: {grupo_selecionado} | Lojas: {titulo_lojas}')
st.caption(
    f'Período: {data_inicio.strftime("%d/%m/%Y")} até {data_fim.strftime("%d/%m/%Y")} '
    f'({(data_fim - data_inicio).days + 1} dias)'
)

st.markdown('---')

col1, col2, col3, col4 = st.columns(4)

venda_total = kpis_chave.get('Venda Total (R$)', 0)
performance_media = kpis_chave.get('Performance Média', 0)
ticket_medio = kpis_chave.get('Ticket Médio (R$)', 0)
total_produtos = kpis_chave.get('Total de Produtos', 0)

def format_brl(valor):
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

col1.metric("Venda Total (R$)", format_brl(venda_total))
col2.metric("Performance Média", f"{performance_media:.2f} p/p")
col3.metric("Ticket Médio (R$)", format_brl(ticket_medio))
col4.metric("Total de Produtos", f"{int(total_produtos):,} un.")

st.markdown('---')

st.subheader(f'Ranking de Vendas: {kpi_selecionado} por Consultor')

selected_kpi_info = KPI_DATAFRAME_MAP[kpi_selecionado]
df_current_kpi = selected_kpi_info['df']
value_col_name = selected_kpi_info['col']

df_ranking_filtered = df_current_kpi[df_current_kpi['Consultor'].isin(consultor_selecionado)]

if not df_ranking_filtered.empty:
    fig_ranking = create_ranking_chart(
        df_ranking_filtered,
        kpi_selecionado,
        value_col_name,
        plot_height
    )
    st.plotly_chart(fig_ranking, use_container_width=True)
else:
    st.info("Nenhum dado disponível para os filtros selecionados")

st.markdown('---')


if kpi_selecionado != 'TOTAL DE PRODUTOS':
    st.subheader('Total de Produtos/Consultor')
    
    df_produtos_filtered = df_produtos_consultor[
        df_produtos_consultor['Consultor'].isin(consultor_selecionado)
    ]
    
    if not df_produtos_filtered.empty:
        fig_produtos = create_produtos_chart(df_produtos_filtered, consultor_selecionado)
        st.plotly_chart(fig_produtos, use_container_width=True)
    else:
        st.info("Sem dados de produtos para os consultores selecionados")
    
    st.markdown('---')


st.subheader('Performance: Produtos/Passagem')

df_performance_filtered = df_performance[
    df_performance['Consultor'].isin(consultor_selecionado)
]

if not df_performance_filtered.empty:
    fig_performance = create_performance_chart(df_performance_filtered, consultor_selecionado)
    st.plotly_chart(fig_performance, use_container_width=True)
else:
    st.info("Sem dados de performance para os consultores selecionados")

st.markdown('---')


st.subheader('Penetração Produto/OS (Share de Produtos Vendidos)')

col_penetracao, col_info = st.columns([2, 1])

with col_penetracao:
    if not df_metricas_produto.empty:
        df_produtos_chart = df_metricas_produto[['Descricao', 'Penetracao_Produto']].copy()
        
        fig_penetracao = create_penetracao_chart(df_produtos_chart)
        st.plotly_chart(fig_penetracao, use_container_width=True)
    else:
        st.info("Sem dados de produtos para o período selecionado")

with col_info:
    st.markdown("##### Informações de Penetração")
    
    st.info(
        "Este gráfico exibe a distribuição de produtos vendidos. "
        "Os dados são agregados de todas as lojas selecionadas."
    )
    
    if not df_metricas_produto.empty:
        produto_lider = df_metricas_produto.loc[
            df_metricas_produto['Penetracao_Produto'].idxmax()
        ]
        st.metric(
            "Produto Líder",
            produto_lider['Descricao'],
            f"{produto_lider['Penetracao_Produto']:.2f}%"
        )


st.markdown('---')
st.subheader('Evolução Temporal por Loja')

if not df_metricas_temporais.empty:
    fig_evolucao = create_evolucao_temporal_chart(df_metricas_temporais)
    st.plotly_chart(fig_evolucao, use_container_width=True)
    
    col_info1, col_info2 = st.columns(2)
    
    with col_info1:
        st.info(
            "**Linhas Sólidas**: Total de Produtos (eixo esquerdo)\n\n"
            "**Linhas Tracejadas**: Faturamento em R$ (eixo direito)"
        )
    
    with col_info2:
        loja_top = df_metricas_temporais.groupby('Nome_Loja')['Venda_RS'].sum().idxmax()
        faturamento_top = df_metricas_temporais.groupby('Nome_Loja')['Venda_RS'].sum().max()
        
        st.metric(
            "Loja Destaque (Faturamento)",
            loja_top,
            format_brl(faturamento_top)
        )
else:
    st.info("Sem dados temporais para o período selecionado")

st.markdown('---')

if st.secrets.get('settings', {}).get('debug_mode', False):
    with st.expander("🔍 Debug: Métricas Detalhadas", expanded=False):
        st.write("### Métricas por Vendedor")
        st.dataframe(df_metricas_vendedor)
        
        st.write("### Top 10 Produtos")
        st.dataframe(df_metricas_produto.head(10))
        
        st.write("### KPIs Chave")
        st.json(kpis_chave)
        
        st.write("### Configuração de Lojas Carregadas")
        st.json(lojas_configs)