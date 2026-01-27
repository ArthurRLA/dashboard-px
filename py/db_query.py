from typing import List
from datetime import date


class SalesQueries:
    """Queries relacionadas a vendas."""
    
    @staticmethod
    def get_sales_data() -> str:
        """
        Query principal para buscar dados de vendas.
        
        Parâmetros esperados:
            - lojas_ids: List[int]
            - data_inicio: date
            - data_fim: date
        
        Returns:
            Query SQL com placeholders
        """
        
        return """
        SELECT 
          -- Identificação
          s.id,
          s.document_number as n_doc,
          s.reference_date as mes,
          s.quantity as quantidade,
          s.function as funcao,
          
          -- Loja
          c.id as loja_id,
          c.fantasy_name as nome_loja,
          c.cnpj,
          
          -- Hierarquia DINÂMICA
          c.group_id,
          g.name as grupo,
          
          c.flag_id,
          f.name as marca,
          
          c.industry_id,
          i.name as segmento,
          
          -- Vendedor
          e.id as employee_id,
          e.name as vendedor,
          e.cpf,
          
          -- Produto
          p.id as product_id,
          p.product_code as produto,
          p.product_name as descricao,
          
          -- Valores via table_price
          COALESCE(tp.price, 0) as valor_unidade,
          s.quantity * COALESCE(tp.price, 0) as valor_total,
          
          -- Flag de validação
          CASE 
            WHEN tp.price IS NULL THEN 'SEM_PRECO'
            ELSE 'OK'
          END as status_preco
          
        FROM sale s
        INNER JOIN customer c ON s.customer_id = c.id
        INNER JOIN employee e ON s.employee_id = e.id
        INNER JOIN product p ON s.product_id = p.id
        
        -- Hierarquia DINÂMICA
        LEFT JOIN groups g ON c.group_id = g.id
        LEFT JOIN flag f ON c.flag_id = f.id
        LEFT JOIN industry i ON c.industry_id = i.id
        
        -- Preços
        LEFT JOIN table_price tp ON p.id = tp.product_id AND c.id = tp.customer_id
        
        WHERE s.reference_date BETWEEN %(data_inicio)s AND %(data_fim)s
          AND c.id = ANY(%(lojas_ids)s)
          AND c.active = true
          AND e.active = true
        
        ORDER BY s.reference_date DESC
        """


class MetadataQueries:
    """Queries para metadados (grupos, lojas, etc)."""
    
    @staticmethod
    def get_grupos() -> str:
        """
        Lista todos os grupos com vendas.
        
        Returns:
            Query SQL que retorna:
            - id: ID do grupo
            - nome: Nome do grupo
            - total_lojas: Quantidade de lojas
            - total_vendas: Quantidade de vendas
        """
        
        return """
        SELECT 
          g.id,
          g.name as nome,
          COUNT(DISTINCT c.id) as total_lojas,
          COUNT(s.id) as total_vendas
        FROM groups g
        INNER JOIN customer c ON c.group_id = g.id
        LEFT JOIN sale s ON s.customer_id = c.id
        WHERE c.active = true
        GROUP BY g.id, g.name
        HAVING COUNT(s.id) > 0
        ORDER BY g.name
        """
    
    @staticmethod
    def get_lojas_by_grupo() -> str:
        """
        Lista lojas de um grupo específico.
        
        Parâmetros esperados:
            - grupo_id: int
        
        Returns:
            Query SQL que retorna:
            - id: ID da loja (customer)
            - nome: Nome da loja (fantasy_name)
            - cnpj: CNPJ
            - total_vendas: Quantidade de vendas
        """
        
        return """
        SELECT 
          c.id,
          c.fantasy_name as nome,
          c.cnpj,
          COUNT(s.id) as total_vendas
        FROM customer c
        LEFT JOIN sale s ON s.customer_id = c.id
        WHERE c.group_id = %(grupo_id)s
          AND c.active = true
        GROUP BY c.id, c.fantasy_name, c.cnpj
        ORDER BY c.fantasy_name
        """
    
    @staticmethod
    def get_all_lojas() -> str:
        """
        Lista todas as lojas ativas com suas hierarquias.
        
        Returns:
            Query SQL que retorna:
            - id: ID da loja
            - nome: Nome da loja
            - cnpj: CNPJ
            - grupo_id: ID do grupo
            - grupo: Nome do grupo
            - total_vendas: Quantidade de vendas
        """
        
        return """
        SELECT 
          c.id,
          c.fantasy_name as nome,
          c.cnpj,
          c.group_id as grupo_id,
          g.name as grupo,
          COUNT(s.id) as total_vendas
        FROM customer c
        LEFT JOIN groups g ON c.group_id = g.id
        LEFT JOIN sale s ON s.customer_id = c.id
        WHERE c.active = true
        GROUP BY c.id, c.fantasy_name, c.cnpj, c.group_id, g.name
        HAVING COUNT(s.id) > 0
        ORDER BY g.name, c.fantasy_name
        """
    
    @staticmethod
    def get_date_range() -> str:
        """
        Retorna o período disponível de dados (min e max).
        
        Returns:
            Query SQL que retorna:
            - data_inicio: Data mínima
            - data_fim: Data máxima
        """
        
        return """
        SELECT 
          MIN(reference_date) as data_inicio,
          MAX(reference_date) as data_fim
        FROM sale
        """