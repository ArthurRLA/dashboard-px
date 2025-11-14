import streamlit as st
import pandas as pd
import os
import io
import re
# CORREÇÃO: Importa Optional para anotações de tipo
from typing import Optional 
# Importa a função de processamento de metadados
from kpi_processor import identify_dynamic_metadata 

def load_shop_config():
    """
    Carrega o mapeamento das lojas hierárquico (Região -> Loja -> Caminho).
    ATENÇÃO: Ajuste o BASE_DIR para o caminho correto dos seus arquivos CSV.
    """
    # Define o diretório base para os CSVs
    BASE_DIR = '/home/arthur/projetos/database_px/dashboard-px/csv' 

    # Estrutura Hierárquica: Região -> Loja -> Caminho
    return {
        "SP1": {
            "BMW FODA .VRUM VRUM": os.path.join(BASE_DIR, '/home/arthur/projetos/database_px/dashboard-px/csv/exemplo.csv'),
            #"LOJA B - CENTRO": os.path.join(BASE_DIR, 'loja_b_sp1.csv'), 
        },
        "SP2": {
            #"LOJA C - MATRIZ": os.path.join(BASE_DIR, 'matriz_dados.csv'),
            #"LOJA D - GUARULHOS": os.path.join(BASE_DIR, 'loja_d_sp2.csv'),
        },
        "PE": {
            #"LOJA E - RECIFE": os.path.join(BASE_DIR, 'loja_e_pe.csv'),
        }
    }

# CORRIGIDO: Substituído "or None" por Optional[pd.DataFrame]
def read_and_clean_csv(file_path: str) -> Optional[pd.DataFrame]: 
    """Lê o arquivo CSV, detecta o separador, trata o decimal (vírgula) e limpa."""
    
    if not os.path.exists(file_path):
        return None 
    
    try:
        # Lógica de leitura e limpeza MANTIDA INTACTA
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

# CORRIGIDO: Substituído "or None" por Optional[pd.DataFrame]
def load_and_combine_data(loja_paths: list, loja_names: list) -> Optional[pd.DataFrame]:
    """Lê múltiplos arquivos, adiciona a coluna 'Nome_Loja' e concatena."""
    all_dfs = []
    
    for path, name in zip(loja_paths, loja_names):
        df = read_and_clean_csv(path) 
        if df is not None:
            df['Nome_Loja'] = name 
            all_dfs.append(df)

    if not all_dfs:
        return None

    df_master = pd.concat(all_dfs, ignore_index=True)
    return df_master

@st.cache_data
def load_data(loja_paths: list, loja_names: list):
    """Orquestra o carregamento, combinação, cache e processamento inicial."""
    
    df_master = load_and_combine_data(loja_paths, loja_names)
    
    if df_master is None:
        return pd.DataFrame(), pd.DataFrame(), [], {} 
        
    # Usa a função do kpi_processor para extrair metadados do DF MESTRE
    consultores_da_regiao, dynamic_kpi_map = identify_dynamic_metadata(df_master.columns)

    # Separação dos DataFrames agregados e de produtos
    df_totais = df_master[df_master['Tipo_de_Registro'] == 'Total'].set_index('Codigo')
    df_produtos = df_master[df_master['Tipo_de_Registro'] == 'Produto']
    
    return df_totais, df_produtos, consultores_da_regiao, dynamic_kpi_map