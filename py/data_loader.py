"""
Novo Data Loader - Leitura de Arquivos XLSX
Substitui a lógica baseada em CSV por processamento de dados transacionais.
"""

import streamlit as st
import pandas as pd
import os
from typing import Optional, Tuple, List
from pathlib import Path

# ==============================================================================
# 1. CONFIGURAÇÃO DE LOJAS (Hierárquica)
# ==============================================================================

def load_shop_config():
    BASE_DIR = '/home/arthur/projetos/database_px/dashboard-px/xlsx'
    
    # ✅ Um arquivo por loja (confirma que cada loja terá seu próprio XLSX)
    return {
        "SP1": {
            "McLarty Maia": {
                'path': os.path.join(BASE_DIR, 'relatorio-vendas.xlsx'),  # ✅ Nome confirmado
                'filter': 'McLarty Maia - Mini Pinheiros',  # ✅ Texto exato da coluna Cliente
                'sheet_name': 'Sheet0'  # ✅ Nome da sheet
            },
            "Jeep Pacaembu": {
                'path': os.path.join(BASE_DIR, 'relatorio-vendas.xlsx'),
                'filter': 'McLarty Maia - Jeep Pacaembu',  # Ajuste conforme o texto real
                'sheet_name': 'Sheet0'
            },
        },
        "SP2": {
            "Mercedes Pacaembu": {
                'path': os.path.join(BASE_DIR, 'relatorio-vendas.xlsx'),
                'filter': 'McLarty Maia - Mercedes Pacaembu',  # Ajuste conforme o texto real
                'sheet_name': 'Sheet0'
            },
        },
        "PE": {
            # Adicione lojas da região PE aqui quando disponível
        }
    }


# ==============================================================================
# 2. LEITURA E LIMPEZA DO XLSX
# ==============================================================================

def read_and_clean_xlsx(file_path: str, loja_filter: str = None, sheet_name: str = 'Sheet0') -> Optional[pd.DataFrame]:
    """
    Lê arquivo XLSX e retorna DataFrame limpo com transações.
    
    Args:
        file_path: Caminho do arquivo .xlsx
        loja_filter: Nome da loja para filtrar na coluna 'Cliente'
        sheet_name: Nome da sheet (padrão: 'Sheet0')
    
    Returns:
        DataFrame com colunas padronizadas ou None se erro
    """
    
    if not os.path.exists(file_path):
        st.warning(f"⚠️ Arquivo não encontrado: {file_path}")
        return None
    
    try:
        # Lê o arquivo XLSX
        df = pd.read_excel(
            file_path,
            sheet_name=sheet_name,
            engine='openpyxl'  # Requer: pip install openpyxl
        )

        expected_columns = {
            'Mês': 'Mes',
            'N° Doc': 'N_Doc',
            'Cliente': 'Cliente',
            'CNPJ': 'CNPJ',
            'Vendedor': 'Vendedor',
            'CPF': 'CPF',
            'Produto': 'Produto',
            'Valor_Unidade': 'Valor_Unidade',
            'Descrição': 'Descricao',
            'Quantidade': 'Quantidade',
            'Função': 'Funcao',
            'Valor_Total': 'Valor_Total',
        }
        
        # Renomeia colunas (case-insensitive)
        df.columns = df.columns.str.strip()  # Remove espaços
        df.rename(columns=expected_columns, inplace=True)
        
        # Verifica colunas essenciais
        required_cols = ['Vendedor', 'Produto', 'Quantidade', 'Valor_Total']
        missing = [col for col in required_cols if col not in df.columns]
        
        if missing:
            st.error(f"❌ Colunas obrigatórias faltando: {missing}")
            st.write("Colunas encontradas:", list(df.columns))
            return None
        
        # Filtra por loja (se especificado)
        if loja_filter and 'Cliente' in df.columns:
            original_len = len(df)
            df = df[df['Cliente'].str.contains(loja_filter, case=False, na=False)]
            
            if len(df) == 0:
                st.warning(f"⚠️ Nenhuma transação encontrada para loja: {loja_filter}")
                return None
            
            st.info(f"📊 Filtrado {len(df)} de {original_len} transações para {loja_filter}")
        
        # Limpeza e conversão de dados numéricos
        numeric_cols = ['Quantidade', 'Valor_Total', 'Valor_Unidade']
        
        for col in numeric_cols:
            if col in df.columns:
                # Remove pontos (milhares) e troca vírgula por ponto (decimal)
                df[col] = df[col].astype(str).str.replace('.', '', regex=False)
                df[col] = df[col].str.replace(',', '.', regex=False)
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Remove linhas inválidas (sem vendedor ou produto)
        df = df.dropna(subset=['Vendedor', 'Produto'])
        
        # Valida cálculo: Valor_Total deve ser ≈ Valor_Unidade × Quantidade
        if 'Valor_Unidade' in df.columns:
            df['Valor_Calculado'] = df['Valor_Unidade'] * df['Quantidade']
            df['Diferenca'] = abs(df['Valor_Total'] - df['Valor_Calculado'])
            
            erros = df[df['Diferenca'] > 0.10]  # Tolerância de 10 centavos
            if len(erros) > 0:
                st.warning(f"⚠️ {len(erros)} linhas com inconsistência de valores")
        
        # Extrai mês/período se disponível
        if 'Mes' in df.columns:
            df['Periodo'] = pd.to_datetime(df['Mes'], errors='coerce').dt.to_period('M')
        
        # Adiciona coluna de identificação da loja
        if loja_filter:
            df['Nome_Loja'] = loja_filter
        
        return df
    
    except Exception as e:
        st.error(f"❌ Erro ao ler arquivo XLSX: {e}")
        import traceback
        st.code(traceback.format_exc())
        return None


# ==============================================================================
# 3. AGREGAÇÃO DE MÉTRICAS
# ==============================================================================

def calcular_metricas_vendedor(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula todas as métricas agregadas por vendedor.
    Equivalente às antigas linhas "Total" do CSV.
    
    Returns:
        DataFrame com:
        - Vendedor (ou Consultor)
        - Total_Produtos
        - Venda_RS
        - Total_OS
        - Ticket_Medio
        - Performance
    """
    
    if df.empty:
        return pd.DataFrame(columns=['Consultor', 'Total_Produtos', 'Venda_RS', 
                                      'Total_OS', 'Ticket_Medio', 'Performance'])
    
    # Agregação por vendedor
    metricas = df.groupby('Vendedor').agg({
        'Quantidade': 'sum',           # Total de produtos vendidos
        'Valor_Total': 'sum',          # Venda total em R$
        'N_Doc': 'nunique',            # Total de OS únicas (documentos)
    }).reset_index()
    
    metricas.columns = ['Vendedor', 'Total_Produtos', 'Venda_RS', 'Total_OS']
    
    # Calcula métricas derivadas
    metricas['Ticket_Medio'] = metricas['Venda_RS'] / metricas['Total_OS']
    metricas['Performance'] = metricas['Total_Produtos'] / metricas['Total_OS']
    
    # Trata divisão por zero
    metricas['Ticket_Medio'] = metricas['Ticket_Medio'].replace([float('inf'), float('-inf')], 0).fillna(0)
    metricas['Performance'] = metricas['Performance'].replace([float('inf'), float('-inf')], 0).fillna(0)
    
    # Padroniza nome da coluna para 'Consultor' (compatibilidade)
    metricas.rename(columns={'Vendedor': 'Consultor'}, inplace=True)
    
    return metricas


def calcular_metricas_produto(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula métricas agregadas por produto.
    Equivalente às antigas linhas tipo "Produto" do CSV.
    
    Returns:
        DataFrame com:
        - Produto (código)
        - Descricao
        - Quantidade_Total
        - Valor_Total
        - Penetracao_Produto (%)
    """
    
    if df.empty:
        return pd.DataFrame(columns=['Produto', 'Descricao', 'Quantidade_Total', 
                                      'Valor_Total', 'Penetracao_Produto'])
    
    # Agregação por produto
    total_geral = df['Quantidade'].sum()
    
    produtos = df.groupby(['Produto', 'Descricao']).agg({
        'Quantidade': 'sum',
        'Valor_Total': 'sum',
    }).reset_index()
    
    produtos.columns = ['Produto', 'Descricao', 'Quantidade_Total', 'Valor_Total']
    
    # Calcula penetração
    if total_geral > 0:
        produtos['Penetracao_Produto'] = (produtos['Quantidade_Total'] / total_geral * 100)
    else:
        produtos['Penetracao_Produto'] = 0
    
    return produtos


# ==============================================================================
# 4. COMBINAÇÃO DE MÚLTIPLAS LOJAS
# ==============================================================================

def load_and_combine_data(loja_configs: list) -> Optional[pd.DataFrame]:
    """
    Lê múltiplos arquivos XLSX e combina em um DataFrame mestre.
    
    Args:
        loja_configs: Lista de dicts com 'path', 'filter', 'name'
    
    Returns:
        DataFrame combinado ou None
    """
    all_dfs = []
    
    for config in loja_configs:
        df = read_and_clean_xlsx(
            file_path=config['path'],
            loja_filter=config.get('filter'),
            sheet_name=config.get('sheet_name', 'Sheet0')
        )
        
        if df is not None:
            # Adiciona nome da loja se não existir
            if 'Nome_Loja' not in df.columns:
                df['Nome_Loja'] = config.get('name', config.get('filter', 'Desconhecido'))
            
            all_dfs.append(df)
    
    if not all_dfs:
        st.error("❌ Nenhum arquivo XLSX válido foi carregado.")
        return None
    
    # Concatena todos os DataFrames
    df_master = pd.concat(all_dfs, ignore_index=True)
    
    return df_master


# ==============================================================================
# 5. FUNÇÃO PRINCIPAL (Cached)
# ==============================================================================

@st.cache_data
def load_data(loja_configs: list) -> Tuple[pd.DataFrame, pd.DataFrame, List[str]]:
    """
    Função principal de carregamento e processamento.
    
    Args:
        loja_configs: Lista de configurações de lojas
    
    Returns:
        Tuple com:
        - df_metricas_vendedor: Métricas agregadas por vendedor
        - df_metricas_produto: Métricas agregadas por produto
        - lista_consultores: Lista de vendedores únicos
    """
    
    # 1. Carrega e combina dados
    df_master = load_and_combine_data(loja_configs)
    
    if df_master is None or df_master.empty:
        return pd.DataFrame(), pd.DataFrame(), []
    
    # 2. Calcula métricas agregadas
    df_metricas_vendedor = calcular_metricas_vendedor(df_master)
    df_metricas_produto = calcular_metricas_produto(df_master)
    
    # 3. Extrai lista de consultores (vendedores únicos)
    lista_consultores = sorted(df_master['Vendedor'].unique().tolist())
    
    # Debug info (opcional)
    with st.expander("🔍 Debug: Dados Carregados", expanded=False):
        st.write(f"**Total de transações:** {len(df_master)}")
        st.write(f"**Lojas:** {df_master['Nome_Loja'].unique().tolist()}")
        st.write(f"**Vendedores:** {lista_consultores}")
        st.write(f"**Período:** {df_master.get('Periodo', 'N/A').unique()}")
        st.dataframe(df_master.head(10))
    
    return df_metricas_vendedor, df_metricas_produto, lista_consultores