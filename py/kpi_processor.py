import pandas as pd
from typing import Dict, List

KPI_NAMES = {
    'TOTAL_PRODUTOS': 'TOTAL DE PRODUTOS',
    'VENDA_RS': 'SELL IN',
    'TICKET_MEDIO': 'TKT MÉDIO SELL OUT',
}

COLUMN_NAME_MAP = {
    'TOTAL DE PRODUTOS': 'Total_Produtos',
    'SELL IN': 'Venda_RS',
    'TKT MÉDIO SELL OUT': 'Ticket_Medio',
}



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


def calculate_kpis_chave(df_metricas_vendedor: pd.DataFrame) -> dict:
    if df_metricas_vendedor.empty:
        return {
            'Sell In Total (R$)': 0,
            'Ticket Médio (R$)': 0,
            'Total de Produtos': 0
        }

    sell_in_total = df_metricas_vendedor['Venda_RS'].sum()
    total_produtos = df_metricas_vendedor['Total_Produtos'].sum()

    ticket_medio = sell_in_total / total_produtos if total_produtos > 0 else 0

    kpis_chave = {
        'Sell In Total (R$)': sell_in_total,
        'Ticket Médio (R$)': ticket_medio,
        'Total de Produtos': total_produtos
    }
    
    for key in kpis_chave:
        val = kpis_chave[key]
        if isinstance(val, float) and (pd.isna(val) or val == float('inf')):
            kpis_chave[key] = 0
    
    return kpis_chave


def get_consultores_list(df_metricas_vendedor: pd.DataFrame) -> List[str]:
    if df_metricas_vendedor.empty:
        return []
    
    return sorted(df_metricas_vendedor['Consultor'].unique().tolist())

def filter_metricas_por_consultor(df_metricas: pd.DataFrame, consultores_selecionados: List[str]) -> pd.DataFrame:
    if not consultores_selecionados or df_metricas.empty:
        return df_metricas
    
    return df_metricas[df_metricas['Consultor'].isin(consultores_selecionados)]


def validar_metricas(df_metricas_vendedor: pd.DataFrame) -> Dict[str, bool]:
    validacoes = {
        'tem_dados': not df_metricas_vendedor.empty,
        'venda_positiva': False,
        'ticket_valido': False,
        'produtos_positivos': False
    }
    
    if validacoes['tem_dados']:
        validacoes['venda_positiva'] = (df_metricas_vendedor['Venda_RS'] > 0).any()
        validacoes['ticket_valido'] = (df_metricas_vendedor['Ticket_Medio'] >= 0).all()
        validacoes['produtos_positivos'] = (df_metricas_vendedor['Total_Produtos'] > 0).any()
    
    return validacoes


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