import pandas as pd
from typing import Dict, List

# ==============================================================================
# 1. MAPEAMENTO DE KPIs (Atualizado)
# ==============================================================================

KPI_NAMES = {
    'TOTAL_PRODUTOS': 'TOTAL DE PRODUTOS',
    'VENDA_RS': 'TOTAL VENDA RS',
    'TICKET_MEDIO': 'TKT MÉDIO SELL OUT',
    'PERFORMANCE': 'PERFORMANCE',
}

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
    if df_metricas.empty:
        col_name = COLUMN_NAME_MAP.get(kpi_name, 'Valor')
        return pd.DataFrame(columns=['Consultor', col_name])
    
    col_name = COLUMN_NAME_MAP.get(kpi_name)
    
    if col_name not in df_metricas.columns:
        return pd.DataFrame(columns=['Consultor', col_name])
    
    df_kpi = df_metricas[['Consultor', col_name]].copy()
    
    return df_kpi


def create_all_kpi_dataframes(df_metricas_vendedor: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    kpi_dataframes = {}
    
    for kpi_key, kpi_name in KPI_NAMES.items():
        df_kpi = create_kpi_dataframe(df_metricas_vendedor, kpi_name)
        kpi_dataframes[kpi_name] = df_kpi
    
    return kpi_dataframes


# ==============================================================================
# 3. MAPEAMENTO COMPLETO DE KPIs (Para Compatibilidade)
# ==============================================================================

def create_kpi_dataframe_map(df_metricas_vendedor: pd.DataFrame) -> Dict[str, Dict]:
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
    
    for key in kpis_chave:
        if pd.isna(kpis_chave[key]) or kpis_chave[key] == float('inf'):
            kpis_chave[key] = 0
    
    return kpis_chave


# ==============================================================================
# 5. EXTRAÇÃO DE CONSULTORES (Substitui identify_dynamic_metadata)
# ==============================================================================

def get_consultores_list(df_metricas_vendedor: pd.DataFrame) -> List[str]:
    if df_metricas_vendedor.empty:
        return []
    
    return sorted(df_metricas_vendedor['Consultor'].unique().tolist())


# ==============================================================================
# 6. FUNÇÃO AUXILIAR: FILTRAR MÉTRICAS POR CONSULTOR
# ==============================================================================

def filter_metricas_por_consultor(df_metricas: pd.DataFrame, consultores_selecionados: List[str]) -> pd.DataFrame:
    if not consultores_selecionados or df_metricas.empty:
        return df_metricas
    
    return df_metricas[df_metricas['Consultor'].isin(consultores_selecionados)]


# ==============================================================================
# 7. VALIDAÇÃO DE DADOS
# ==============================================================================

def validar_metricas(df_metricas_vendedor: pd.DataFrame) -> Dict[str, bool]:
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
    df_totais_sim = {}
    for kpi_name, col_name in COLUMN_NAME_MAP.items():
        if col_name in df_metricas_vendedor.columns:
            df_totais_sim[kpi_name] = df_metricas_vendedor.set_index('Consultor')[col_name]
    
    df_produtos_sim = pd.DataFrame()
    
    consultores = get_consultores_list(df_metricas_vendedor)
    
    kpi_map = create_kpi_dataframe_map(df_metricas_vendedor)
    
    return df_totais_sim, df_produtos_sim, consultores, kpi_map


# SELL IN
def calculate_sell_in_by_consultor(df_metricas_vendedor: pd.DataFrame) -> pd.DataFrame:
    if df_metricas_vendedor.empty:
        return pd.DataFrame(columns=['Consultor', 'Total_Produtos', 'Sell_In_Percentual'])
    
    total_geral = df_metricas_vendedor['Total_Produtos'].sum()
    df_sell_in = df_metricas_vendedor[['Consultor', 'Total_Produtos']].copy()
    
    if total_geral > 0:
        df_sell_in['Sell_In_Percentual'] = (
            df_sell_in['Total_Produtos'] / total_geral * 100
        )
    else:
        df_sell_in['Sell_In_Percentual'] = 0
    
    df_sell_in = df_sell_in.sort_values('Sell_In_Percentual', ascending=False)
    return df_sell_in