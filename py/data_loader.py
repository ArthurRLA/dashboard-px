import streamlit as st
import pandas as pd
import numpy as np
from typing import Tuple, List, Optional
from datetime import date

from db_connector import db
from db_query import SalesQueries, MetadataQueries
from data_transformer import DataTransformer, GroupHierarchyBuilder, safe_int

from db_query import IncentiveQueries


def abreviar_nome(nome: str) -> str:
    if not nome or not isinstance(nome, str):
        return nome
    
    PARTICULAS = {'de', 'do', 'da', 'dos', 'das'}
    partes = nome.strip().split()
    
    if len(partes) <= 2:
        return ' '.join(partes)
    
    if partes[1].lower() in PARTICULAS:
        return ' '.join(partes[:3])
    
    return ' '.join(partes[:2])


@st.cache_data(ttl=300)
def load_shop_config_from_db(user_id: Optional[int] = None) -> dict:
    """
    Carrega grupos e lojas do banco.

    Args:
        user_id: Se informado (ROLE_USER), filtra apenas clientes vinculados
                 a esse usuário. Se None (ROLE_ADMIN), retorna todos.
    """
    try:
        query_grupos = MetadataQueries.get_grupos()
        df_grupos = db.execute_query(query_grupos, {"user_id": user_id})

        query_lojas = MetadataQueries.get_all_lojas()
        df_lojas = db.execute_query(query_lojas, {"user_id": user_id})

        shop_config = GroupHierarchyBuilder.build_shop_config(df_grupos, df_lojas)

        if st.secrets.get('settings', {}).get('debug_mode', False):
            st.sidebar.info(
                f"{len(shop_config)} grupos | "
                f"{sum(len(lojas) for lojas in shop_config.values())} lojas"
            )

        return shop_config

    except Exception as e:
        st.error(f"Erro ao carregar configuração de lojas: {e}")
        return {}


def load_sales_from_db(
    lojas_ids: List[int],
    data_inicio: date,
    data_fim: date
) -> pd.DataFrame:
    if not lojas_ids:
        st.warning("Nenhuma loja selecionada")
        return pd.DataFrame()

    try:
        query = SalesQueries.get_sales_data()

        df_raw = db.execute_query(query, {
            'lojas_ids': lojas_ids,
            'data_inicio': data_inicio,
            'data_fim': data_fim
        })

        if df_raw.empty:
            return pd.DataFrame()

        df_normalized = DataTransformer.normalize_sales_data(df_raw)

        validation = DataTransformer.validate_data_quality(df_normalized)

        if st.secrets.get('settings', {}).get('debug_mode', False):
            DataTransformer.show_validation_warnings(validation)

        return df_normalized

    except Exception as e:
        st.error(f"Erro ao carregar dados de vendas: {e}")

        if st.secrets.get('settings', {}).get('debug_mode', False):
            import traceback
            st.code(traceback.format_exc())

        return pd.DataFrame()


def calcular_metricas_vendedor(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=[
            'Consultor', 'Total_Produtos', 'Venda_RS',
            'Total_OS', 'Ticket_Medio'
        ])

    metricas = df.groupby('Vendedor').agg({
        'Quantidade': 'sum',
        'Valor_Total': 'sum',
        'N_Doc': 'nunique',
    }).reset_index()

    metricas.columns = ['Vendedor', 'Total_Produtos', 'Venda_RS', 'Total_OS']

    metricas['Ticket_Medio'] = metricas['Venda_RS'] / metricas['Total_Produtos']

    metricas['Ticket_Medio'] = metricas['Ticket_Medio'].replace(
        [float('inf'), float('-inf')], 0
    ).fillna(0)

    metricas.rename(columns={'Vendedor': 'Consultor'}, inplace=True)

    metricas['Consultor'] = metricas['Consultor'].apply(abreviar_nome)

    return metricas


def calcular_metricas_produto(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=[
            'Produto', 'Descricao', 'Quantidade_Total',
            'Valor_Total', 'Penetracao_Produto'
        ])

    total_geral = df['Quantidade'].sum()

    produtos = df.groupby(['Produto', 'Descricao']).agg({
        'Quantidade': 'sum',
        'Valor_Total': 'sum',
    }).reset_index()

    produtos.columns = ['Produto', 'Descricao', 'Quantidade_Total', 'Valor_Total']

    if total_geral > 0:
        produtos['Penetracao_Produto'] = (
            produtos['Quantidade_Total'] / total_geral * 100
        )
    else:
        produtos['Penetracao_Produto'] = 0

    return produtos


def calcular_metricas_temporais(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=[
            'Periodo', 'Nome_Loja', 'Total_Produtos', 'Venda_RS', 'Periodo_Str'
        ])

    metricas = df.groupby(['Periodo', 'Nome_Loja']).agg({
        'Quantidade': 'sum',
        'Valor_Total': 'sum',
    }).reset_index()

    metricas.columns = ['Periodo', 'Nome_Loja', 'Total_Produtos', 'Venda_RS']

    metricas['Periodo_Str'] = metricas['Periodo'].astype(str)

    return metricas


@st.cache_data(ttl=300)
def load_data(
    lojas_configs: tuple,
    data_inicio: date,
    data_fim: date
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, List[str]]:
    lojas_ids = [safe_int(loja['id']) for loja in lojas_configs]

    df_master = load_sales_from_db(lojas_ids, data_inicio, data_fim)

    if df_master.empty:
        return (
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            []
        )

    df_metricas_vendedor  = calcular_metricas_vendedor(df_master)
    df_metricas_produto   = calcular_metricas_produto(df_master)
    df_metricas_temporais = calcular_metricas_temporais(df_master)

    lista_consultores = sorted(df_metricas_vendedor['Consultor'].unique().tolist())

    if st.secrets.get('settings', {}).get('debug_mode', False):
        with st.expander("Debug: Dados Carregados", expanded=False):
            st.write(f"**Total de transações:** {len(df_master):,}")
            st.write(f"**Lojas:** {df_master['Nome_Loja'].unique().tolist()}")
            st.write(f"**Vendedores:** {len(lista_consultores)}")
            st.write(f"**Período:** {data_inicio} até {data_fim}")
            st.dataframe(df_master.head(10))

    return (
        df_metricas_vendedor,
        df_metricas_produto,
        df_metricas_temporais,
        lista_consultores
    )

@st.cache_data(ttl=300)
def get_date_range_from_db() -> Tuple[date, date]:
    try:
        query = MetadataQueries.get_date_range()
        df = db.execute_query(query)

        if df.empty:
            from datetime import datetime, timedelta
            data_fim = datetime.now().date()
            data_inicio = data_fim - timedelta(days=90)
            return (data_inicio, data_fim)

        return (df['data_inicio'].iloc[0], df['data_fim'].iloc[0])

    except Exception as e:
        st.error(f"Erro ao buscar período de dados: {e}")
        from datetime import datetime, timedelta
        data_fim = datetime.now().date()
        data_inicio = data_fim - timedelta(days=90)
        return (data_inicio, data_fim)


@st.cache_data(ttl=300)
def get_available_months_incentives() -> List[dict]:
    try:
        query = IncentiveQueries.get_available_months()
        df = db.execute_query(query)

        if df.empty:
            return []

        meses_list = df.to_dict('records')
        return meses_list

    except Exception as e:
        st.error(f"Erro ao buscar meses disponíveis: {e}")
        return []


@st.cache_data(ttl=300)
def load_incentives_by_employee(
    lojas_ids: List[int],
    meses: List[str]
) -> pd.DataFrame:
    if not lojas_ids or not meses:
        return pd.DataFrame()

    try:
        query = IncentiveQueries.get_incentives_by_employee()

        df = db.execute_query(query, {
            'lojas_ids': lojas_ids,
            'meses': meses
        })

        if df.empty:
            return pd.DataFrame()

        numeric_cols = ['total_incentivos', 'valor_total_incentivos', 'valor_medio_incentivo']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        if 'vendedor' in df.columns:
            df['vendedor'] = df['vendedor'].apply(abreviar_nome)

        return df

    except Exception as e:
        st.error(f"Erro ao carregar incentivos por vendedor: {e}")

        if st.secrets.get('settings', {}).get('debug_mode', False):
            import traceback
            st.code(traceback.format_exc())

        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_incentives_by_month_employee(
    lojas_ids: List[int],
    meses: List[str]
) -> pd.DataFrame:
    if not lojas_ids or not meses:
        return pd.DataFrame()

    try:
        query = IncentiveQueries.get_incentives_by_month_employee()

        df = db.execute_query(query, {
            'lojas_ids': lojas_ids,
            'meses': meses
        })

        if df.empty:
            return pd.DataFrame()

        numeric_cols = ['quantidade_mes', 'valor_mes']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        if 'vendedor' in df.columns:
            df['vendedor'] = df['vendedor'].apply(abreviar_nome)

        return df

    except Exception as e:
        st.error(f"Erro ao carregar incentivos: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_incentives_details(
    lojas_ids: List[int],
    meses: List[str]
) -> pd.DataFrame:
    if not lojas_ids or not meses:
        return pd.DataFrame()

    try:
        query = IncentiveQueries.get_incentives_details()

        df = db.execute_query(query, {
            'lojas_ids': lojas_ids,
            'meses': meses
        })

        if df.empty:
            return pd.DataFrame()

        if 'data_referencia' in df.columns:
            df['data_referencia'] = pd.to_datetime(df['data_referencia'])

        if 'valor' in df.columns:
            df['valor'] = pd.to_numeric(df['valor'], errors='coerce').fillna(0)

        return df

    except Exception as e:
        st.error(f"Erro ao carregar detalhes de incentivos: {e}")
        return pd.DataFrame()


def create_monthly_pivot_table(df_monthly: pd.DataFrame) -> pd.DataFrame:
    if df_monthly.empty:
        return pd.DataFrame()

    pivot = df_monthly.pivot_table(
        index='vendedor',
        columns='mes_display',
        values='valor_mes',
        aggfunc='sum',
        fill_value=0
    )

    mes_order = df_monthly[['mes_display', 'mes']].drop_duplicates()
    mes_order = mes_order.sort_values('mes')

    colunas_ordenadas = [col for col in mes_order['mes_display'].tolist() if col in pivot.columns]
    pivot = pivot[colunas_ordenadas]

    pivot['Total'] = pivot.sum(axis=1)
    pivot = pivot.sort_values('Total', ascending=False)
    pivot = pivot.reset_index()

    return pivot


def calculate_incentive_summary_metrics(df_employee: pd.DataFrame) -> dict:
    metrics = {
        'valor_total': 0,
        'total_vendedores': 0,
        'valor_medio': 0,
        'vendedor_destaque': None,
        'maior_valor': 0
    }

    if df_employee.empty:
        return metrics

    metrics['valor_total']      = df_employee['valor_total_incentivos'].sum()
    metrics['total_vendedores'] = len(df_employee)
    metrics['valor_medio']      = df_employee['valor_total_incentivos'].mean()

    idx_max = df_employee['valor_total_incentivos'].idxmax()
    if pd.notna(idx_max):
        metrics['vendedor_destaque'] = df_employee.loc[idx_max, 'vendedor']
        metrics['maior_valor']       = df_employee.loc[idx_max, 'valor_total_incentivos']

    for key in metrics:
        if isinstance(metrics[key], float) and (pd.isna(metrics[key]) or metrics[key] == float('inf')):
            metrics[key] = 0

    return metrics