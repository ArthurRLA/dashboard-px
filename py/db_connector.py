import streamlit as st
import psycopg2
from psycopg2 import pool
import pandas as pd
from contextlib import contextmanager
from typing import Optional, Dict, Any


class DatabaseConnector:
    _instance = None
    _connection_pool = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._init_pool()
    
    def _init_pool(self):
        try:
            db_config = st.secrets.get('database', {})
            
            if not db_config:
                raise ValueError(
                    "Configuração de banco não encontrada em secrets.toml. "
                    "Adicione seção [database] com host, port, database, user, password."
                )
            
            min_conn = db_config.get('connection_pool_min', 2)
            max_conn = db_config.get('connection_pool_max', 10)
            
            self._connection_pool = psycopg2.pool.SimpleConnectionPool(
                minconn=min_conn,
                maxconn=max_conn,
                host=db_config['host'],
                port=db_config.get('port', 5432),
                database=db_config['database'],
                user=db_config['user'],
                password=db_config['password'],
                connect_timeout=db_config.get('connect_timeout', 10),
                sslmode=db_config.get('sslmode', 'prefer')
            )
            
            if st.secrets.get('settings', {}).get('debug_mode', False):
                st.sidebar.success(f"✅ Pool PostgreSQL criado ({min_conn}-{max_conn} conexões)")
                
        except KeyError as e:
            error_msg = f"Configuração faltando em secrets.toml: {e}"
            st.error(f"{error_msg}")
            raise ValueError(error_msg)
            
        except psycopg2.OperationalError as e:
            error_msg = f"Erro ao conectar PostgreSQL: {e}"
            st.error(f"{error_msg}")
            st.info(
                "💡 Verifique:\n"
                "- IP/Porta corretos\n"
                "- PostgreSQL está rodando\n"
                "- Firewall permite conexão\n"
                "- Credenciais corretas"
            )
            raise
    
    @contextmanager
    def get_connection(self):
        conn = None
        try:
            conn = self._connection_pool.getconn()
            yield conn
        finally:
            if conn:
                self._connection_pool.putconn(conn)
    
    def execute_query(
        self, 
        query: str, 
        params: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """
        Executa query SQL e retorna DataFrame.
        
        Args:
            query: SQL query com placeholders %(param)s
            params: Dicionário de parâmetros
        
        Returns:
            DataFrame com resultados
        
        Exemplo:
            df = db.execute_query(
                "SELECT * FROM sale WHERE customer_id = %(id)s",
                {'id': 1}
            )
        """
        try:
            with self.get_connection() as conn:
                df = pd.read_sql_query(query, conn, params=params)
            return df
            
        except psycopg2.Error as e:
            st.error(f"❌ Erro ao executar query: {e}")
            
            if st.secrets.get('settings', {}).get('debug_mode', False):
                st.code(f"Query: {query}\nParams: {params}")
            
            raise
        
        except Exception as e:
            st.error(f"Erro inesperado: {type(e).__name__}: {e}")
            raise
    
    def test_connection(self) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                cursor.close()
                return result[0] == 1
                
        except Exception as e:
            st.error(f"Falha no teste de conexão: {e}")
            return False
    
    def close(self):
        if self._connection_pool:
            self._connection_pool.closeall()
            if st.secrets.get('settings', {}).get('debug_mode', False):
                st.info("🔒 Pool de conexões fechado")


db = DatabaseConnector()