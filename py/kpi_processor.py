"""
Novo KPI Processor - Adaptado para Dados Transacionais XLSX
Remove dependência de estrutura CSV e usa agregações.
"""

import pandas as pd
from typing import Dict, List

# ==============================================================================
# 1. MAPEAMENTO DE KPIs (Atualizado)
# ==============================================================================

# Nomes padronizados para os KPIs (mantém compatibilidade com código existente)
KPI_NAMES = {
    'TOTAL_PRODUTOS': 'TOTAL DE PRODUTOS',
    'VENDA_RS': 'TOTAL VENDA RS',
    'TICKET_MEDIO': 'TKT MÉDIO SELL OUT',
    'PERFORMANCE': 'PERFORMANCE',
}

# Mapeamento de colunas no DataFrame de métricas
COLUMN_NAME_MAP = {
    'TOTAL DE PRODUTOS': 'Total_Produtos',
    'TOTAL VENDA RS': 'Venda_RS',
    'TKT MÉDIO SELL OUT': 'Ticket_Medio',
    'PERFORMANCE': 'Performance',
}


# ==============================================================================
# 2. CRIAÇÃO DE DATAFRAMES DE KPI (Formato Compatível)
# ==============================================================================

def create_kpi_dataframe(df_metricas: pd.DataFrame, kpi_name: str) -> pd.DataFrame:
    """
    Cria DataFrame de KPI no formato esperado pelo código de visualização.
    
    Args:
        df_metricas: DataFrame com métricas por vendedor/consultor
        kpi_name: Nome do KPI (ex: 'TOTAL DE PRODUTOS')
    
    Returns:
        DataFrame com formato: Consultor | {Valor_KPI}
    """
    
    if df_metricas.empty:
        col_name = COLUMN_NAME_MAP.get(kpi_name, 'Valor')
        return pd.DataFrame(columns=['Consultor', col_name])
    
    # Pega o nome da coluna correspondente ao KPI
    col_name = COLUMN_NAME_MAP.get(kpi_name)
    
    if col_name not in df_metricas.columns:
        return pd.DataFrame(columns=['Consultor', col_name])
    
    # Cria DataFrame no formato esperado
    df_kpi = df_metricas[['Consultor', col_name]].copy()
    
    return df_kpi


def create_all_kpi_dataframes(df_metricas_vendedor: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """
    Cria todos os DataFrames de KPI de uma vez.
    
    Args:
        df_metricas_vendedor: DataFrame com todas as métricas agregadas
    
    Returns:
        Dicionário com formato: {KPI_NAME: DataFrame}
    """
    
    kpi_dataframes = {}
    
    for kpi_key, kpi_name in KPI_NAMES.items():
        df_kpi = create_kpi_dataframe(df_metricas_vendedor, kpi_name)
        kpi_dataframes[kpi_name] = df_kpi
    
    return kpi_dataframes


# ==============================================================================
# 3. MAPEAMENTO COMPLETO DE KPIs (Para Compatibilidade)
# ==============================================================================

def create_kpi_dataframe_map(df_metricas_vendedor: pd.DataFrame) -> Dict[str, Dict]:
    """
    Cria estrutura completa de KPIs no formato esperado pelo streamlit_app.py.
    
    Returns:
        Dicionário com formato:
        {
            'TOTAL DE PRODUTOS': {
                'df': DataFrame(Consultor, Total_Produtos),
                'col': 'Total_Produtos',
                'alias': 'TOTAL DE PRODUTOS'
            },
            ...
        }
    """
    
    kpi_dataframes = create_all_kpi_dataframes(df_metricas_vendedor)
    
    kpi_map = {}
    
    for kpi_name, df_kpi in kpi_dataframes.items():
        col_name = COLUMN_NAME_MAP.get(kpi_name, 'Valor')
        
        kpi_map[kpi_name] = {
            'df': df_kpi,
            'col': col_name,
            'alias': kpi_name
        }
    
    return kpi_map


# ==============================================================================
# 4. CÁLCULO DOS KPIs PRINCIPAIS (Compatível com Código Existente)
# ==============================================================================

def calculate_kpis_chave(df_metricas_vendedor: pd.DataFrame) -> dict:
    """
    Calcula as métricas principais do topo do dashboard.
    
    Args:
        df_metricas_vendedor: DataFrame com métricas por consultor
    
    Returns:
        Dicionário com:
        - 'Venda Total (R$)'
        - 'Performance Média'
        - 'Ticket Médio (R$)'
        - 'Total de Produtos'
    """
    
    if df_metricas_vendedor.empty:
        return {
            'Venda Total (R$)': 0,
            'Performance Média': 0,
            'Ticket Médio (R$)': 0,
            'Total de Produtos': 0
        }
    
    kpis_chave = {
        'Venda Total (R$)': df_metricas_vendedor['Venda_RS'].sum(),
        'Performance Média': df_metricas_vendedor['Performance'].mean(),
        'Ticket Médio (R$)': df_metricas_vendedor['Ticket_Medio'].mean(),
        'Total de Produtos': df_metricas_vendedor['Total_Produtos'].sum()
    }
    
    # Trata NaN/Inf
    for key in kpis_chave:
        if pd.isna(kpis_chave[key]) or kpis_chave[key] == float('inf'):
            kpis_chave[key] = 0
    
    return kpis_chave


# ==============================================================================
# 5. EXTRAÇÃO DE CONSULTORES (Substitui identify_dynamic_metadata)
# ==============================================================================

def get_consultores_list(df_metricas_vendedor: pd.DataFrame) -> List[str]:
    """
    Extrai lista de consultores do DataFrame de métricas.
    
    Returns:
        Lista ordenada de nomes de consultores
    """
    
    if df_metricas_vendedor.empty:
        return []
    
    return sorted(df_metricas_vendedor['Consultor'].unique().tolist())


# ==============================================================================
# 6. FUNÇÃO AUXILIAR: FILTRAR MÉTRICAS POR CONSULTOR
# ==============================================================================

def filter_metricas_por_consultor(df_metricas: pd.DataFrame, consultores_selecionados: List[str]) -> pd.DataFrame:
    """
    Filtra o DataFrame de métricas para incluir apenas consultores selecionados.
    
    Args:
        df_metricas: DataFrame com métricas agregadas
        consultores_selecionados: Lista de nomes de consultores
    
    Returns:
        DataFrame filtrado
    """
    
    if not consultores_selecionados or df_metricas.empty:
        return df_metricas
    
    return df_metricas[df_metricas['Consultor'].isin(consultores_selecionados)]


# ==============================================================================
# 7. VALIDAÇÃO DE DADOS
# ==============================================================================

def validar_metricas(df_metricas_vendedor: pd.DataFrame) -> Dict[str, bool]:
    """
    Valida se as métricas calculadas fazem sentido.
    
    Returns:
        Dicionário com resultados de validação
    """
    
    validacoes = {
        'tem_dados': not df_metricas_vendedor.empty,
        'venda_positiva': False,
        'performance_valida': False,
        'ticket_valido': False,
        'produtos_positivos': False
    }
    
    if validacoes['tem_dados']:
        validacoes['venda_positiva'] = (df_metricas_vendedor['Venda_RS'] > 0).any()
        validacoes['performance_valida'] = (
            (df_metricas_vendedor['Performance'] >= 0) & 
            (df_metricas_vendedor['Performance'] <= 100)
        ).all()
        validacoes['ticket_valido'] = (df_metricas_vendedor['Ticket_Medio'] >= 0).all()
        validacoes['produtos_positivos'] = (df_metricas_vendedor['Total_Produtos'] > 0).any()
    
    return validacoes


# ==============================================================================
# 8. FUNÇÃO DE MIGRAÇÃO (Para Testes)
# ==============================================================================

def simular_estrutura_antiga(df_metricas_vendedor: pd.DataFrame) -> tuple:
    """
    Simula a estrutura antiga de retorno para facilitar migração gradual.
    Útil para testes de compatibilidade.
    
    Returns:
        Tuple com:
        - df_totais (simulado como dict de Series)
        - df_produtos (vazio, será calculado separadamente)
        - consultores_da_regiao (lista)
        - dynamic_kpi_map (dict)
    """
    
    # Simula df_totais como dict de Series (formato antigo)
    df_totais_sim = {}
    for kpi_name, col_name in COLUMN_NAME_MAP.items():
        if col_name in df_metricas_vendedor.columns:
            df_totais_sim[kpi_name] = df_metricas_vendedor.set_index('Consultor')[col_name]
    
    # df_produtos será calculado separadamente em load_data
    df_produtos_sim = pd.DataFrame()
    
    # Lista de consultores
    consultores = get_consultores_list(df_metricas_vendedor)
    
    # KPI Map
    kpi_map = create_kpi_dataframe_map(df_metricas_vendedor)
    
    return df_totais_sim, df_produtos_sim, consultores, kpi_map