import os
import yaml
import streamlit as st
from pathlib import Path
from typing import Dict, Any, Optional

class ConfigLoader:
    """Singleton para gerenciar configurações da aplicação"""
    
    _instance = None
    _config_cache = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._project_root = self._find_project_root()
    
    def _find_project_root(self) -> Path:
        """
        Encontra a raiz do projeto (onde está .streamlit/)
        """
        current = Path(__file__).resolve().parent
        
        # Sobe até encontrar .streamlit/ ou atingir raiz do sistema
        while current != current.parent:
            if (current / '.streamlit').exists():
                return current
            current = current.parent
        
        # Fallback: usa diretório atual
        return Path.cwd()
    
    def get_data_dir(self) -> Path:
        """
        Retorna o diretório de dados (com prioridade para secrets)
        
        Priority:
        1. st.secrets['paths']['data_dir']
        2. Variável de ambiente DATA_DIR
        3. ./data/vendas (relativo à raiz do projeto)
        """
        
        # 1. Tenta carregar de secrets
        if hasattr(st, 'secrets') and 'paths' in st.secrets:
            data_dir_str = st.secrets['paths'].get('data_dir')
            if data_dir_str:
                path = Path(data_dir_str)
                # Se for relativo, resolve a partir da raiz do projeto
                if not path.is_absolute():
                    path = self._project_root / path
                return path.resolve()
        
        # 2. Tenta variável de ambiente
        env_data_dir = os.getenv('DATA_DIR')
        if env_data_dir:
            path = Path(env_data_dir)
            if not path.is_absolute():
                path = self._project_root / path
            return path.resolve()
        
        # 3. Fallback: diretório padrão
        return (self._project_root / 'data' / 'vendas').resolve()
    
    def load_yaml(self, yaml_path: str) -> Dict[str, Any]:
        """
        Carrega arquivo YAML (com cache)
        
        Args:
            yaml_path: Caminho relativo a partir de config/ ou caminho absoluto
        """
        
        # Normaliza path
        if not Path(yaml_path).is_absolute():
            full_path = self._project_root / 'config' / yaml_path
        else:
            full_path = Path(yaml_path)
        
        # Cache
        cache_key = str(full_path)
        if cache_key in self._config_cache:
            return self._config_cache[cache_key]
        
        # Carrega
        if not full_path.exists():
            st.error(f"Arquivo de configuração não encontrado: {full_path}")
            return {}
        
        with open(full_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        self._config_cache[cache_key] = config
        return config
    
    def get_lojas_config(self) -> Dict[str, Any]:
        """Carrega configuração de lojas"""
        return self.load_yaml('lojas.yaml')
    
    def get_settings(self) -> Dict[str, Any]:
        """Carrega settings gerais"""
        return self.load_yaml('settings.yaml')
    
    def get_secret(self, key: str, default: Any = None) -> Any:
        """
        Busca valor em secrets com fallback
        
        Args:
            key: Chave no formato 'section.key' (ex: 'paths.data_dir')
            default: Valor padrão se não encontrado
        """
        if not hasattr(st, 'secrets'):
            return default
        
        keys = key.split('.')
        value = st.secrets
        
        for k in keys:
            if k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def is_debug_mode(self) -> bool:
        """Verifica se está em modo debug"""
        return self.get_secret('settings.debug_mode', False)
    
    def get_cache_ttl(self) -> int:
        """Retorna TTL do cache em segundos"""
        # Priority: secrets > settings.yaml > padrão
        ttl_secret = self.get_secret('settings.cache_ttl')
        if ttl_secret:
            return int(ttl_secret)
        
        settings = self.get_settings()
        return settings.get('cache', {}).get('ttl_segundos', 300)


# Instância global
config = ConfigLoader()