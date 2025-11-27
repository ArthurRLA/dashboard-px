"""
Novo Data Loader - Leitura de Arquivos XLSX
Substitui a lógica baseada em CSV por processamento de dados transacionais.
"""

import streamlit as st
import pandas as pd
import os
from typing import Optional, Tuple, List
from pathlib import Path
from config_loader import config

# ==============================================================================
# 1. CONFIGURAÇÃO DE LOJAS (Hierárquica)
# ==============================================================================

def load_shop_config():
   
    # Carrega YAML
    lojas_yaml = config.get_lojas_config()
    
    if not lojas_yaml or 'regioes' not in lojas_yaml:
        st.error("Erro ao carregar configuração de lojas (config/lojas.yaml)")
        return {}
    
    # Obtém diretório de dados
    data_dir = config.get_data_dir()
    
    # Transforma YAML em estrutura esperada pelo código
    shop_config = {}
    
    for regiao_code, regiao_data in lojas_yaml['regioes'].items():
        shop_config[regiao_code] = {}

        lojas = regiao_data.get('lojas') or []  # ← FIX

        for loja in lojas:
            if not loja.get('ativa', True):
                continue
            
            nome_loja = loja['nome']
            shop_config[regiao_code][nome_loja] = {
                'path': str(data_dir / loja['arquivo']),
                'filter': loja.get('filtro_cliente', loja['nome_completo']),
                'sheet_name': loja.get('sheet', 'Sheet0'),
                'nome_completo': loja.get('nome_completo', nome_loja)
            }
    
    if config.is_debug_mode():
        st.sidebar.info(f"📁 Diretório de dados: {data_dir}")
        st.sidebar.info(f"🏪 {sum(len(lojas) for lojas in shop_config.values())} lojas carregadas")
    
    return shop_config


# ==============================================================================
# 2. LEITURA E LIMPEZA DO XLSX
# ==============================================================================

def read_and_clean_xlsx(file_path: str, loja_filter: str = None, sheet_name: str = 'Sheet0') -> Optional[pd.DataFrame]:
    
    # Carrega settings
    settings = config.get_settings()
    validacoes = settings.get('validacoes', {})
    formatos = settings.get('formatos', {})
    
    if not os.path.exists(file_path):
        st.warning(f"Arquivo não encontrado: {file_path}")
        return None
    
    try:
        # Lê o arquivo XLSX
        df = pd.read_excel(
            file_path,
            sheet_name=sheet_name,
            engine='openpyxl'
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
        df.columns = df.columns.str.strip()
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
            
            if config.is_debug_mode():
                st.info(f"📊 Filtrado {len(df)} de {original_len} transações para {loja_filter}")
        
        # Limpeza e conversão de dados numéricos
        numeric_cols = ['Quantidade', 'Valor_Total', 'Valor_Unidade']
        
        for col in numeric_cols:
            if col in df.columns:
                # Remove pontos (milhares) e troca vírgula por ponto (decimal)
                df[col] = df[col].astype(str).str.replace('.', '', regex=False)
                df[col] = df[col].str.replace(',', '.', regex=False)
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Remove linhas inválidas
        df = df.dropna(subset=['Vendedor', 'Produto'])
        
        # Valida cálculo (usa tolerância do settings)
        tolerancia = validacoes.get('tolerancia_valor_total', 0.10)
        
        if 'Valor_Unidade' in df.columns:
            df['Valor_Calculado'] = df['Valor_Unidade'] * df['Quantidade']
            df['Diferenca'] = abs(df['Valor_Total'] - df['Valor_Calculado'])
            
            erros = df[df['Diferenca'] > tolerancia]
            if len(erros) > 0:
                st.warning(f"⚠️ {len(erros)} linhas com inconsistência de valores (tolerância: R$ {tolerancia})")
        
        # Extrai período (usa formato do settings)
        if 'Mes' in df.columns:
            formato_data = formatos.get('data_entrada', '%Y/%m/%d')
            df = parse_periodos(df, formato_data)
        
        # Adiciona coluna de identificação da loja
        if loja_filter:
            df['Nome_Loja'] = loja_filter
        
        return df
    
    except Exception as e:
        st.error(f"❌ Erro ao ler arquivo XLSX: {e}")
        if config.is_debug_mode():
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
# 5. FUNÇÕES DE FILTRO TEMPORAL
# ==============================================================================
def parse_periodos(df: pd.DataFrame, formato: str = '%Y/%m/%d') -> pd.DataFrame:
    """
    Parse da coluna Mes para datetime e extração de período.
    
    Args:
        df: DataFrame com coluna 'Mes'
        formato: Formato da data (ex: '%Y/%m/%d')
    
    Returns:
        DataFrame com colunas adicionais: Data, Periodo, Periodo_Display
    """
    settings = config.get_settings()
    formato_display = settings.get('formatos', {}).get('data_exibicao', '%b/%y')
    
    # Converte para datetime
    df['Data'] = pd.to_datetime(df['Mes'], format=formato, errors='coerce')
    
    # Cria coluna de período
    df['Periodo'] = df['Data'].dt.to_period('M')
    
    # Formato para exibição
    df['Periodo_Display'] = df['Data'].dt.strftime(formato_display)
    
    return df


def extrair_periodos_disponiveis(df: pd.DataFrame) -> tuple:
    """
    Extrai lista ordenada de períodos únicos presentes nos dados.
    
    Returns:
        Tuple: (lista_de_periods, lista_de_labels)
    """
    if df.empty or 'Periodo' not in df.columns:
        return [], []
    
    # Remove NaN e pega únicos
    periodos_unicos = df['Periodo'].dropna().unique()
    
    # Ordena
    periodos_sorted = sorted(periodos_unicos)
    
    # Cria labels de exibição com tratamento de erro
    labels = []
    for p in periodos_sorted:
        try:
            # Tenta formatar como Period
            labels.append(p.strftime('%b/%y'))
        except AttributeError:
            # Fallback: converte para string diretamente
            labels.append(str(p))
    
    return periodos_sorted, labels

def calcular_metricas_temporais(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula métricas agregadas por período e loja.
    
    Returns:
        DataFrame com:
        - Periodo
        - Nome_Loja
        - Total_Produtos
        - Venda_RS
    """
    if df.empty:
        return pd.DataFrame(columns=['Periodo', 'Nome_Loja', 'Total_Produtos', 'Venda_RS'])
    
    # Agregação por período e loja
    metricas = df.groupby(['Periodo', 'Nome_Loja']).agg({
        'Quantidade': 'sum',
        'Valor_Total': 'sum',
    }).reset_index()
    
    metricas.columns = ['Periodo', 'Nome_Loja', 'Total_Produtos', 'Venda_RS']
    
    # Converte Periodo para string (necessário para Plotly)
    metricas['Periodo_Str'] = metricas['Periodo'].astype(str)
    
    return metricas


# ==============================================================================
# 5. FUNÇÃO PRINCIPAL (Cached)
# ==============================================================================

@st.cache_data
# Remove decorador fixo e adiciona dinâmico
def load_data(loja_configs: list, periodos_selecionados: list = None) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, List[str]]:
    # 1. Carrega e combina dados
    df_master = load_and_combine_data(loja_configs)
    
    if df_master is None or df_master.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), []
    
    # 2. Filtra por períodos se especificado
    if periodos_selecionados:
        df_master = df_master[df_master['Periodo'].isin(periodos_selecionados)]
    
    # 3. Calcula métricas agregadas
    df_metricas_vendedor = calcular_metricas_vendedor(df_master)
    df_metricas_produto = calcular_metricas_produto(df_master)
    df_metricas_temporais = calcular_metricas_temporais(df_master)
    
    # 4. Extrai lista de consultores
    lista_consultores = sorted(df_master['Vendedor'].unique().tolist())
    
    # Debug info
    if config.is_debug_mode():
        with st.expander("🔍 Debug: Dados Carregados", expanded=False):
            st.write(f"**Total de transações:** {len(df_master)}")
            st.write(f"**Lojas:** {df_master['Nome_Loja'].unique().tolist()}")
            st.write(f"**Vendedores:** {lista_consultores}")
            st.write(f"**Períodos:** {df_master['Periodo_Display'].unique().tolist()}")
            st.dataframe(df_master.head(10))
    
    return df_metricas_vendedor, df_metricas_produto, df_metricas_temporais, lista_consultores

# Aplica cache com TTL dinâmico
load_data = st.cache_data(ttl=config.get_cache_ttl())(load_data)