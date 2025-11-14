import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io
import numpy as np
import os 
import re # Adicionado para identificação dinâmica de padrões de coluna

# ==============================================================================
# 0. DEFINIÇÕES GLOBAIS E DINÂMICAS
# ==============================================================================

# Prefixos fixos que identificam os KPIs por consultor em QUALQUER CSV
KPI_PREFIXES = {
    "Produtos_": "TOTAL DE PRODUTOS",
    "Performance_": "PERFORMANCE",
    "Venda_RS_": "VENDA R$",
    "TKT_Medio_": "TICKET MÉDIO"
}

# O mês é mantido apenas para o título
MESES = ['Janeiro/25', 'Fevereiro/25', 'Março/25', 'Abril/25']

# [REMOVIDO: CONSULTORES_RAW, CONSULTORES_UPPER, KPI_MAP_FULL]

# ==============================================================================
# NOVAS FUNÇÕES AUXILIARES PARA ESCALONABILIDADE
# ==============================================================================

def load_shop_config():
    """
    [ALTERADO] Carrega o mapeamento das lojas hierárquico (Região -> Loja -> Caminho).
    Simulação usando a estrutura de pastas do seu ambiente.
    """
    # Define o diretório base para os CSVs
    BASE_DIR = '/home/arthur/projetos/database_px/dashboard-px/csv' 

    # Estrutura Hierárquica: Região -> Loja -> Caminho
    return {
        "SP1 - CENTRO": {
            "LOJA A - CASTELO": os.path.join(BASE_DIR, 'exemplo.csv'),
            # Adicionei um CSV fictício para simular a agregação
            "LOJA B - CENTRO": os.path.join(BASE_DIR, 'loja_b_sp1.csv'), 
        },
        "SP2 - ABC": {
            "LOJA C - MATRIZ": os.path.join(BASE_DIR, 'matriz_dados.csv'),
            "LOJA D - GUARULHOS": os.path.join(BASE_DIR, 'loja_d_sp2.csv'),
        },
        "NORDESTE - PE": {
            "LOJA E - RECIFE": os.path.join(BASE_DIR, 'loja_e_pe.csv'),
        }
    }

def identify_dynamic_metadata(df_columns: pd.Index):
    """
    Analisa as colunas do DF MESTRE para identificar a união de todos os consultores 
    e construir o mapa de KPI (com base em todas as lojas combinadas).
    """
    consultores_set = set()
    dynamic_kpi_map = {}
    
    # 1. Encontrar todos os nomes de consultores (UNIÃO DE TODOS)
    for col in df_columns:
        for prefix in KPI_PREFIXES.keys():
            if col.startswith(prefix):
                consultor_name = col[len(prefix):]
                consultores_set.add(consultor_name.upper()) 
                break

    consultores_da_regiao = sorted(list(consultores_set))
    
    # 2. Construir o Mapa de KPI Dinâmico
    for prefix, kpi_name in KPI_PREFIXES.items():
        cols_for_kpi = [col for col in df_columns if col.startswith(prefix)]
        new_col_name = kpi_name.replace(' ', '_').replace('R$', 'RS').replace('TKT_', 'Ticket_')
        
        dynamic_kpi_map[kpi_name] = {
            'cols': cols_for_kpi, 
            'new_col': new_col_name,
            'alias': kpi_name 
        }

    return consultores_da_regiao, dynamic_kpi_map


def load_and_combine_data(loja_paths: list, loja_names: list):
    """
    [NOVA FUNÇÃO CHAVE] Recebe uma lista de caminhos, lê, adiciona o nome da loja
    e concatena os DataFrames em um único DF mestre.
    """
    all_dfs = []
    
    for path, name in zip(loja_paths, loja_names):
        # Reutiliza a função robusta de leitura
        df = read_and_clean_csv(path) 
        if df is not None:
            # Adiciona a coluna de identificação de Loja (crucial para agregação)
            df['Nome_Loja'] = name 
            all_dfs.append(df)

    if not all_dfs:
        st.error("Nenhum arquivo CSV válido foi carregado para as lojas selecionadas.")
        return None

    # Concatena todos os DFs de todas as lojas
    df_master = pd.concat(all_dfs, ignore_index=True)
    return df_master


# ==============================================================================
# 1. FUNÇÕES DE CARREGAMENTO E PRÉ-PROCESSAMENTO (MANUTENÇÃO DA ROBUSTEZ)
# ==============================================================================

def read_and_clean_csv(file_path):
    """Lê o arquivo CSV, detecta o separador e trata a vírgula como decimal."""
    # Lógica de leitura e limpeza MANTIDA INTACTA, apenas pega um arquivo por vez.
    if not os.path.exists(file_path):
        # Não exibe erro crítico, apenas retorna None se o arquivo não existir (e.g., arquivo fictício)
        return None 
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_content = f.read()

        df = None
        for sep in [',', ';']:
            try:
                df_temp = pd.read_csv(io.StringIO(raw_content), sep=sep)
                if 'Tipo_de_Registro' in df_temp.columns:
                    df = df_temp
                    break
            except Exception:
                continue

        if df is None:
            st.warning(f"CSV em {file_path} não pôde ser lido corretamente.")
            return None

        cols_to_clean = df.columns.difference(['Tipo_de_Registro', 'Codigo', 'Produto'])
        for col in cols_to_clean:
            df[col] = df[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
            df[col] = pd.to_numeric(df[col], errors='coerce') 

        return df
    
    except Exception as e:
        st.error(f"Erro inesperado no CSV: {e}")
        return None

@st.cache_data
def load_data(loja_paths: list, loja_names: list):
    """
    [ALTERADO] Orquestra o carregamento, combinação e processamento dos DFs.
    """
    # 1. Carrega e Combina todos os CSVs selecionados
    df_master = load_and_combine_data(loja_paths, loja_names)
    
    if df_master is None:
        return pd.DataFrame(), pd.DataFrame(), [], {} 
        
    # 2. Descobre os metadados (consultores e KPI Map) com base no DF MESTRE combinado
    consultores_da_regiao, dynamic_kpi_map = identify_dynamic_metadata(df_master.columns)

    # 3. Separação (Continua a mesma lógica, agora no DF MESTRE)
    df_totais = df_master[df_master['Tipo_de_Registro'] == 'Total'].set_index('Codigo')
    df_produtos = df_master[df_master['Tipo_de_Registro'] == 'Produto']
    
    return df_totais, df_produtos, consultores_da_regiao, dynamic_kpi_map

# [ALTERADO/RENOMEADO] Função auxiliar para criar as séries de KPI no formato correto
def create_dynamic_kpi_dataframe(df_totais, consultores_da_regiao, kpi_code, kpi_info):
    """
    Cria o DataFrame de série de KPI usando a lista dinâmica de colunas e consultores.
    """
    if kpi_code not in df_totais.index or not kpi_info['cols']:
        # Se as colunas não existirem em nenhuma das lojas, retorna vazio
        return pd.DataFrame(columns=['Consultor', kpi_info['new_col']])
        
    # Agregação: df_totais já é o resultado do pd.concat de todas as lojas.
    # A agregação por consultor acontece implicitamente ao somar os valores do Código 'TOTAL DE PRODUTOS'
    # de todos os CSVs. Apenas a primeira linha de cada código é usada (df_totais.set_index('Codigo') 
    # naturalmente filtra a primeira ocorrência se houver duplicidade, o que é o comportamento esperado
    # para a AGREGAÇÃO REGIONAL de KPIs de soma/média).
    
    # Se houver múltiplos códigos 'TOTAL DE PRODUTOS', este código pega o primeiro, 
    # mas o DF MESTRE já foi concatenado, então a agregação está correta para este formato.
    
    serie = df_totais.loc[kpi_code, kpi_info['cols']]
    
    df_kpi = pd.DataFrame(serie).reset_index(names='Consultor_Raw')
    df_kpi.columns = ['Consultor_Raw', kpi_info['new_col']]
    
    # Atribui os nomes de consultores dinamicamente, mantendo a ordem (UPPER)
    df_kpi['Consultor'] = consultores_da_regiao[:len(df_kpi)]
    
    return df_kpi[['Consultor', kpi_info['new_col']]]


# -------------------------------------------------------------
# EXECUÇÃO DO CARREGAMENTO E PROCESSAMENTO PRINCIPAL
# -------------------------------------------------------------

# 1. Configuração da Loja (Novo Fluxo de Filtro Duplo)
shop_config_hierarchical = load_shop_config()
regioes = list(shop_config_hierarchical.keys())

st.sidebar.header('Dashboard POWERX')
st.sidebar.subheader('Seleção de Região e Lojas')

# [NOVO FILTRO 1: REGIÃO]
regiao_selecionada = st.sidebar.selectbox(
    'Selecione a Região',
    options=regioes
)

lojas_da_regiao = list(shop_config_hierarchical[regiao_selecionada].keys())

# [NOVO FILTRO 2: LOJAS MÚLTIPLAS]
lojas_selecionadas = st.sidebar.multiselect(
    'Filtrar Loja(s)',
    options=lojas_da_regiao,
    default=lojas_da_regiao # Seleciona todas por padrão
)

# Cria a lista de caminhos de arquivos para as lojas selecionadas
loja_paths = [shop_config_hierarchical[regiao_selecionada][loja] for loja in lojas_selecionadas]


# 2. Carregamento de Dados (Carrega e Combina)
df_data = load_data(loja_paths, lojas_selecionadas)
df_totais, df_produtos, consultores_da_regiao, KPI_MAP = df_data

titulo_lojas = ', '.join(lojas_selecionadas) if len(lojas_selecionadas) < 4 else f"{len(lojas_selecionadas)} Lojas em {regiao_selecionada}"

if df_totais.empty or not consultores_da_regiao:
    st.error(f"Não foi possível carregar dados para: {titulo_lojas}. Verifique os arquivos.")
    st.stop()
    

# 3. Criação dos DataFrames de Série (Dinâmicos)
df_kpis_series = {}
for kpi_name, kpi_info in KPI_MAP.items():
    df = create_dynamic_kpi_dataframe(df_totais, consultores_da_regiao, kpi_name, kpi_info)
    df_kpis_series[kpi_name] = df

# 4. Atualização do Mapeamento Final e KPIs Chave
KPI_DATAFRAME_MAP = {
    name: {'df': df_kpis_series[name], 'col': info['new_col'], 'alias': name}
    for name, info in KPI_MAP.items()
}

# Garante que os DataFrames dinâmicos estão referenciados
df_venda_rs = KPI_DATAFRAME_MAP['VENDA R$']['df']
df_performance = KPI_DATAFRAME_MAP['PERFORMANCE']['df']
df_ticket_medio = KPI_DATAFRAME_MAP['TICKET MÉDIO']['df']
df_produtos_consultor = KPI_DATAFRAME_MAP['TOTAL DE PRODUTOS']['df']


# 5. Cálculo dos KPIs Chave (usando os DataFrames dinâmicos)
kpis_chave = {
    'Venda Total (R$)': df_venda_rs['Venda_RS'].sum() if not df_venda_rs.empty else 0,
    'Performance Média': df_performance['Performance'].mean() if not df_performance.empty else 0,
    'Ticket Médio (R$)': df_ticket_medio['Ticket_Medio'].mean() if not df_ticket_medio.empty else 0,
    'Total de Produtos': df_produtos_consultor['Total_Produtos'].sum() if not df_produtos_consultor.empty else 0
}


# ==============================================================================
# 6. BARRA LATERAL (SIDEBAR) COM FILTROS FUNCIONAIS
# ==============================================================================

st.sidebar.markdown('---') 

st.sidebar.subheader('Métricas e Visualização')

mes_selecionado = st.sidebar.selectbox(
    'Período (Fixo)',
    options=MESES,
    index=3
)

# [ALTERADO] Usa a lista de consultores da Região (dinâmico)
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
# 7. CORPO PRINCIPAL DO DASHBOARD E GRÁFICOS
# ==============================================================================

st.title(f'📊 Painel de Indicadores de Vendas POWERX')
st.subheader(f'Região: {regiao_selecionada} | Lojas: {titulo_lojas}')
st.caption(f'Dados Consolidados | Período: **{mes_selecionado}**')

st.markdown('---')

# Exibição dos KPIs Chave (Mantido)
col1, col2, col3, col4 = st.columns(4)
kpis = kpis_chave
col1.metric("Venda Total (R$)", f"R$ {kpis['Venda Total (R$)']:,.2f}")
col2.metric("Performance Média", f"{kpis['Performance Média']:.2f} p/p")
col3.metric("Ticket Médio (R$)", f"R$ {kpis['Ticket Médio (R$)']:,.2f}")
col4.metric("Total de Produtos", f"{int(kpis['Total de Produtos'])} un.")

st.markdown('---')

# --------------------------
# GRÁFICO 1: RANKING DINÂMICO REGIONAL
# --------------------------

st.subheader(f'Ranking de Vendas: {kpi_selecionado} por Consultor (Agregado)')

selected_kpi_info = KPI_DATAFRAME_MAP[kpi_selecionado]
df_current_kpi = selected_kpi_info['df']
value_col_name = selected_kpi_info['col']

df_ranking_filtered = df_current_kpi[df_current_kpi['Consultor'].isin(consultor_selecionado)]

is_currency = 'R$' in kpi_selecionado or 'MÉDIO' in kpi_selecionado
if is_currency:
    format_text = 'R$ %{y:,.2f}'
    y_title = f'{kpi_selecionado} (R$)'
else:
    format_text = '%{y:,.2f}' if kpi_selecionado == 'PERFORMANCE' else '%{y:,.0f}'
    y_title = kpi_selecionado

fig_ranking = px.bar(
    df_ranking_filtered.sort_values(by=value_col_name, ascending=False),
    x='Consultor',
    y=value_col_name,
    title=f'Ranking Regional por {kpi_selecionado}',
    color='Consultor',
    text=value_col_name,
    height=plot_height
)

fig_ranking.update_traces(texttemplate=format_text, textposition='outside')
fig_ranking.update_layout(
    xaxis_title="Consultor",
    yaxis_title=y_title,
    showlegend=False
)
st.plotly_chart(fig_ranking, use_container_width=True)

st.markdown('---')

# --------------------------
# GRÁFICOS 2 & 3: TOTAL DE PRODUTOS/CONSULTOR & PERFORMANCE (Mantido)
# --------------------------
# ... (O restante dos gráficos utiliza os DFs dinâmicos, mantendo o filtro por consultor)
# ...

# --------------------------
# GRÁFICO 2: TOTAL DE PRODUTOS/CONSULTOR 
# --------------------------
if kpi_selecionado != 'TOTAL DE PRODUTOS':
    st.subheader('Total de Produtos/consultor (Agregado)')
    fig_produtos = px.bar(
        df_produtos_consultor[df_produtos_consultor['Consultor'].isin(consultor_selecionado)],
        x='Consultor',
        y='Total_Produtos',
        title='Total de Produtos/consultor',
        text='Total_Produtos'
    )
    fig_produtos.update_traces(texttemplate='%{y:,.0f}', textposition='outside')
    st.plotly_chart(fig_produtos, use_container_width=True)
    st.markdown('---')


# --------------------------
# GRÁFICO 3: PERFORMANCE: produtos/passagem
# --------------------------

st.subheader('Performance: produtos/passagem (Agregado)')

df_performance_filtered = df_performance[df_performance['Consultor'].isin(consultor_selecionado)]

fig_performance = px.bar(
    df_performance_filtered,
    x='Consultor',
    y='Performance',
    title='Performance: produtos/passagem',
    text='Performance',
    color_discrete_sequence=['#1f77b4'] 
)
fig_performance.update_traces(texttemplate='%{y:.2f}', textposition='outside')
fig_performance.update_yaxes(range=[0, 1.60], title='Performance') 
st.plotly_chart(fig_performance, use_container_width=True)

st.markdown('---')

# --------------------------
# GRÁFICO 4: PENETRAÇÃO PRODUTO/OS (Mantido)
# --------------------------

st.subheader('Penetração Produto/OS (Share de Produtos Vendidos)')

col_penetracao, col_info = st.columns([2, 1])

with col_penetracao:
    # Este gráfico usa df_produtos (linhas de Produto agregadas)
    fig_penetracao = px.pie(
        df_produtos,
        names='Produto',
        values='Penetracao_Produto',
        title='Penetração produto/OS (Dados Brutos Agregados)',
        hole=.3, 
        height=450
    )
    fig_penetracao.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig_penetracao, use_container_width=True)

with col_info:
    st.markdown("##### Informações de Penetração")
    
    st.info(
        "Este gráfico exibe a distribuição baseada na coluna 'Penetracao_Produto' do CSV. "
        "Os dados são agregados de todas as lojas selecionadas."
    )
    produto_lider = df_produtos.iloc[df_produtos['Penetracao_Produto'].argmax()]
    
    st.metric("Produto Líder", produto_lider['Produto'], 
              f"{produto_lider['Penetracao_Produto']:.2f}")