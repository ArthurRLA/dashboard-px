"""
Data Loader - PostgreSQL Version
Carrega dados do banco PostgreSQL e calcula métricas.
"""

import streamlit as st
import pandas as pd
import numpy as np
from typing import Tuple, List
from datetime import date

from db_connector import db
from db_query import SalesQueries, MetadataQueries
from data_transformer import DataTransformer, GroupHierarchyBuilder, safe_int


@st.cache_data(ttl=300)
def load_shop_config_from_db() -> dict:
    """
    Returns:
        Dicionário no formato:
        {
            'Beni Car': {
                'Beni Car - Castelo': {'id': 1, 'cnpj': '...'},
                'Beni Car - São José': {'id': 7, 'cnpj': '...'}
            },
            'Jorlan': { ... }
        }
    """
    try:
        query_grupos = MetadataQueries.get_grupos()
        df_grupos = db.execute_query(query_grupos)
        
        query_lojas = MetadataQueries.get_all_lojas()
        df_lojas = db.execute_query(query_lojas)
        
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
    """
    Args:
        lojas_ids: Lista de IDs das lojas (customer.id)
        data_inicio: Data inicial do período
        data_fim: Data final do período
    
    Returns:
        DataFrame normalizado com dados de vendas
    """
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
    """
    Returns:
        DataFrame com:
        - Consultor (ou Vendedor)
        - Total_Produtos
        - Venda_RS
        - Total_OS
        - Ticket_Medio
        - Performance
    """
    if df.empty:
        return pd.DataFrame(columns=[
            'Consultor', 'Total_Produtos', 'Venda_RS',
            'Total_OS', 'Ticket_Medio', 'Performance'
        ])
    
    metricas = df.groupby('Vendedor').agg({
        'Quantidade': 'sum',
        'Valor_Total': 'sum',
        'N_Doc': 'nunique',
    }).reset_index()
    
    metricas.columns = ['Vendedor', 'Total_Produtos', 'Venda_RS', 'Total_OS']
    
    metricas['Ticket_Medio'] = metricas['Venda_RS'] / metricas['Total_OS']
    metricas['Performance'] = metricas['Total_Produtos'] / metricas['Total_OS']
    
    metricas['Ticket_Medio'] = metricas['Ticket_Medio'].replace(
        [float('inf'), float('-inf')], 0
    ).fillna(0)
    metricas['Performance'] = metricas['Performance'].replace(
        [float('inf'), float('-inf')], 0
    ).fillna(0)
    
    metricas.rename(columns={'Vendedor': 'Consultor'}, inplace=True)
    
    return metricas


def calcular_metricas_produto(df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns:
        DataFrame com:
        - Produto (código)
        - Descricao
        - Quantidade_Total
        - Valor_Total
        - Penetracao_Produto (%)
    """
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
    """
    Returns:
        DataFrame com:
        - Periodo
        - Nome_Loja
        - Total_Produtos
        - Venda_RS
        - Periodo_Str (para gráficos)
    """
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
    lojas_configs: list,
    data_inicio: date,
    data_fim: date
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, List[str]]:
    """
    Args:
        lojas_configs: Lista de dicts com {'id': int, 'nome': str, ...}
        data_inicio: Data inicial do período
        data_fim: Data final do período
    
    Returns:
        Tupla com:
        - df_metricas_vendedor: Métricas por vendedor
        - df_metricas_produto: Métricas por produto
        - df_metricas_temporais: Evolução temporal
        - lista_consultores: Lista de vendedores únicos
    """
    lojas_ids = [safe_int(loja['id']) for loja in lojas_configs]

    df_master = load_sales_from_db(lojas_ids, data_inicio, data_fim)
    
    if df_master.empty:
        return (
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            []
        )
    
    df_metricas_vendedor = calcular_metricas_vendedor(df_master)
    df_metricas_produto = calcular_metricas_produto(df_master)
    df_metricas_temporais = calcular_metricas_temporais(df_master)
    
    lista_consultores = sorted(df_master['Vendedor'].unique().tolist())
    
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
    """
    Returns:
        Tupla (data_inicio, data_fim)
    """
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