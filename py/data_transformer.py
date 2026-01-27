import pandas as pd
import numpy as np
import streamlit as st
from typing import Dict, Any


def safe_int(value: Any) -> int:
    """
    Args:
        value: Valor a converter (pode ser numpy.int64, int, float, etc)
    
    Returns:
        int Python nativo
    """
    if pd.isna(value):
        return 0
    if isinstance(value, (np.integer, np.int64)):
        return int(value)
    return int(value)


def safe_float(value: Any) -> float:
    """
    Args:
        value: Valor a converter
    
    Returns:
        float Python nativo
    """
    if pd.isna(value):
        return 0.0
    if isinstance(value, (np.floating, np.float64)):
        return float(value)
    return float(value)


class DataTransformer:
    """Normaliza dados do PostgreSQL para formato compatível com o dashboard."""
    
    COLUMN_MAP = {
        'n_doc': 'N_Doc',
        'mes': 'Mes',
        'quantidade': 'Quantidade',
        'funcao': 'Funcao',
        'loja_id': 'Loja_ID',
        'nome_loja': 'Nome_Loja',
        'cnpj': 'CNPJ',
        'group_id': 'Grupo_ID',
        'grupo': 'Grupo',
        'flag_id': 'Marca_ID',
        'marca': 'Marca',
        'industry_id': 'Segmento_ID',
        'segmento': 'Segmento',
        'employee_id': 'Employee_ID',
        'vendedor': 'Vendedor',
        'cpf': 'CPF',
        'product_id': 'Product_ID',
        'produto': 'Produto',
        'descricao': 'Descricao',
        'valor_unidade': 'Valor_Unidade',
        'valor_total': 'Valor_Total',
        'status_preco': 'Status_Preco'
    }
    
    @staticmethod
    def normalize_sales_data(df_raw: pd.DataFrame) -> pd.DataFrame:
        """
        Args:
            df_raw: DataFrame bruto do banco
        
        Returns:
            DataFrame normalizado com colunas no formato esperado
        """
        if df_raw.empty:
            return pd.DataFrame()
        
        df = df_raw.copy()
        df = df.rename(columns=DataTransformer.COLUMN_MAP)
        
        if 'Mes' in df.columns:
            df['Mes'] = pd.to_datetime(df['Mes'])
            df['Data'] = df['Mes']
            df['Periodo'] = df['Mes'].dt.to_period('M')
            df['Periodo_Display'] = df['Mes'].dt.strftime('%b/%y')
        
        numeric_cols = ['Quantidade', 'Valor_Unidade', 'Valor_Total']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        required_cols = ['Vendedor', 'Produto']
        for col in required_cols:
            if col in df.columns:
                df = df.dropna(subset=[col])
        
        return df
    
    @staticmethod
    def validate_data_quality(df: pd.DataFrame) -> Dict[str, int]:
        """
        Args:
            df: DataFrame normalizado
        
        Returns:
            Dicionário com estatísticas de validação:
            - total_registros: Total de linhas
            - produtos_sem_preco: Quantidade sem preço
            - valores_zerados: Quantidade com valor_total = 0
            - quantidades_invalidas: Quantidade <= 0
            - registros_invalidos: Total de problemas
        """
        if df.empty:
            return {
                'total_registros': 0,
                'produtos_sem_preco': 0,
                'valores_zerados': 0,
                'quantidades_invalidas': 0,
                'registros_invalidos': 0
            }
        
        validations = {
            'total_registros': len(df),
            'produtos_sem_preco': 0,
            'valores_zerados': 0,
            'quantidades_invalidas': 0,
            'registros_invalidos': 0
        }
        
        if 'Status_Preco' in df.columns:
            validations['produtos_sem_preco'] = (df['Status_Preco'] == 'SEM_PRECO').sum()
        
        if 'Valor_Total' in df.columns:
            validations['valores_zerados'] = (df['Valor_Total'] == 0).sum()
        
        if 'Quantidade' in df.columns:
            validations['quantidades_invalidas'] = (df['Quantidade'] <= 0).sum()
        
        validations['registros_invalidos'] = max(
            validations['produtos_sem_preco'],
            validations['valores_zerados'],
            validations['quantidades_invalidas']
        )
        
        return validations
    
    @staticmethod
    def show_validation_warnings(validation: Dict[str, int]):
        """
        Args:
            validation: Dicionário retornado por validate_data_quality()
        """
        total = validation['total_registros']
        
        if total == 0:
            return
        
        sem_preco = validation['produtos_sem_preco']
        if sem_preco > 0:
            pct = (sem_preco / total * 100)
            if pct > 50:
                st.error(
                    f"**{sem_preco:,} produtos sem preço** ({pct:.1f}% dos registros). "
                    f"Valores estarão zerados. Verifique cadastro em `table_price`."
                )
            elif pct > 20:
                st.warning(
                    f"**{sem_preco:,} produtos sem preço** ({pct:.1f}% dos registros). "
                    f"Alguns valores podem estar zerados."
                )
            else:
                st.info(
                    f"{sem_preco:,} produtos sem preço ({pct:.1f}%). "
                    f"Impacto mínimo nos resultados."
                )
        
        qtd_invalida = validation['quantidades_invalidas']
        if qtd_invalida > 0:
            st.warning(
                f"**{qtd_invalida:,} registros** com quantidade inválida (≤ 0). "
                f"Estes registros foram removidos."
            )
        
        if sem_preco == 0 and qtd_invalida == 0:
            st.success(f"{total:,} registros carregados sem problemas!")


class GroupHierarchyBuilder:
    @staticmethod
    def build_shop_config(df_grupos: pd.DataFrame, df_lojas: pd.DataFrame) -> dict:
        """
        Args:
            df_grupos: DataFrame com grupos (id, nome, total_lojas, total_vendas)
            df_lojas: DataFrame com lojas (id, nome, cnpj, grupo_id, grupo, total_vendas)
        
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
        shop_config = {}
        
        for _, grupo in df_grupos.iterrows():
            grupo_nome = grupo['nome']
            grupo_id = int(grupo['id'])  
            
            lojas_do_grupo = df_lojas[df_lojas['grupo_id'] == grupo_id]
            
            shop_config[grupo_nome] = {}
            
            for _, loja in lojas_do_grupo.iterrows():
                loja_nome = loja['nome']
                shop_config[grupo_nome][loja_nome] = {
                    'id': safe_int(loja['id']),  
                    'cnpj': str(loja['cnpj']),
                    'total_vendas': safe_int(loja.get('total_vendas', 0))
                }
        
        return shop_config