import pandas as pd

# Prefixos fixos que identificam os KPIs por consultor em QUALQUER CSV
KPI_PREFIXES = {
    "Produtos_": "TOTAL DE PRODUTOS",
    "Performance_": "PERFORMANCE",
    "Venda_RS_": "VENDA R$",
    "TKT_Medio_": "TICKET MÉDIO"
}

def identify_dynamic_metadata(df_columns: pd.Index):
    """
    Analisa as colunas do DF MESTRE (combinado) para identificar a união de todos 
    os consultores e construir o mapa de KPI dinâmico.
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
        # Cria um nome de coluna limpo para o DataFrame de série
        new_col_name = kpi_name.replace(' ', '_').replace('R$', 'RS').replace('TKT_', 'Ticket_')
        
        dynamic_kpi_map[kpi_name] = {
            'cols': cols_for_kpi, 
            'new_col': new_col_name,
            'alias': kpi_name 
        }

    return consultores_da_regiao, dynamic_kpi_map

def create_dynamic_kpi_dataframe(df_totais: pd.DataFrame, consultores_da_regiao: list, kpi_code: str, kpi_info: dict) -> pd.DataFrame:
    """
    Cria o DataFrame de série de KPI (consultor, valor) para Plotly.
    """
    if kpi_code not in df_totais.index or not kpi_info['cols']:
        return pd.DataFrame(columns=['Consultor', kpi_info['new_col']])
        
    # Agrega os dados da linha 'Total' de todas as lojas para a coluna específica
    serie = df_totais.loc[kpi_code, kpi_info['cols']]
    
    df_kpi = pd.DataFrame(serie).reset_index(names='Consultor_Raw')
    df_kpi.columns = ['Consultor_Raw', kpi_info['new_col']]
    
    # Mapeia os nomes limpos de consultores
    df_kpi['Consultor'] = consultores_da_regiao[:len(df_kpi)]
    
    return df_kpi[['Consultor', kpi_info['new_col']]]

def calculate_kpis_chave(df_venda_rs: pd.DataFrame, df_performance: pd.DataFrame, df_ticket_medio: pd.DataFrame, df_produtos_consultor: pd.DataFrame) -> dict:
    """Calcula e retorna as métricas principais do topo do dashboard."""
    kpis_chave = {
        'Venda Total (R$)': df_venda_rs['Venda_RS'].sum() if not df_venda_rs.empty else 0,
        'Performance Média': df_performance['Performance'].mean() if not df_performance.empty else 0,
        'Ticket Médio (R$)': df_ticket_medio['Ticket_Medio'].mean() if not df_ticket_medio.empty else 0,
        'Total de Produtos': df_produtos_consultor['Total_Produtos'].sum() if not df_produtos_consultor.empty else 0
    }
    return kpis_chave