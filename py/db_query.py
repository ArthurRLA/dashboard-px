from typing import List
from datetime import date


class SalesQueries:
    @staticmethod
    def get_sales_data() -> str:
        return """
        SELECT 
          s.id,
          s.document_number as n_doc,
          s.reference_date as mes,
          s.quantity as quantidade,
          s.function as funcao,
          
          c.id as loja_id,
          c.fantasy_name as nome_loja,
          c.cnpj,
          
          c.group_id,
          g.name as grupo,
          
          c.flag_id,
          f.name as marca,
          
          c.industry_id,
          i.name as segmento,
          
          e.id as employee_id,
          e.name as vendedor,
          e.cpf,
          
          p.id as product_id,
          p.product_code as produto,
          p.product_name as descricao,
          
          COALESCE(tp.price, 0) as valor_unidade,
          s.quantity * COALESCE(tp.price, 0) as valor_total,
          
          CASE 
            WHEN tp.price IS NULL THEN 'SEM_PRECO'
            ELSE 'OK'
          END as status_preco
          
        FROM sale s
        INNER JOIN customer c ON s.customer_id = c.id
        INNER JOIN employee e ON s.employee_id = e.id
        INNER JOIN product p ON s.product_id = p.id
        
        LEFT JOIN groups g ON c.group_id = g.id
        LEFT JOIN flag f ON c.flag_id = f.id
        LEFT JOIN industry i ON c.industry_id = i.id
        
        LEFT JOIN table_price tp ON p.id = tp.product_id AND c.id = tp.customer_id
        
        INNER JOIN employee_function ef ON e.id = ef.employee_id
        INNER JOIN function fn ON ef.function_id = fn.id AND fn.name = 'Consultor Técnico'
        
        WHERE s.reference_date BETWEEN %(data_inicio)s AND %(data_fim)s
          AND c.id = ANY(%(lojas_ids)s)
          AND c.active = true
          AND e.active = true
        
        ORDER BY s.reference_date DESC
        """


class MetadataQueries:
    @staticmethod
    def get_grupos() -> str:
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
        return """
        SELECT 
          MIN(reference_date) as data_inicio,
          MAX(reference_date) as data_fim
        FROM sale
        """


class IncentiveQueries:
    
    @staticmethod
    def get_incentives_by_employee() -> str:
        return """
        SELECT 
            e.id as employee_id,
            i.cpf,
            e.name as vendedor,
            
            COALESCE(
                STRING_AGG(DISTINCT fn.name, ' / ' ORDER BY fn.name),
                'Não informado'
            ) as funcao,
            
            c.fantasy_name as loja,
            g.name as grupo,
            
            COUNT(i.id) as total_incentivos,
            COALESCE(SUM(i.incentive_value), 0) as valor_total_incentivos,
            COALESCE(AVG(i.incentive_value), 0) as valor_medio_incentivo
            
        FROM incentive i
        INNER JOIN employee e ON i.employee_id = e.id
        INNER JOIN customer c ON i.customer_id = c.id
        LEFT JOIN groups g ON c.group_id = g.id
        
        LEFT JOIN employee_function ef ON e.id = ef.employee_id
        LEFT JOIN function fn ON ef.function_id = fn.id
        
        WHERE c.id = ANY(%(lojas_ids)s)
          AND e.active = true
          AND c.active = true
          AND TO_CHAR(i.reference_date, 'YYYY-MM') = ANY(%(meses)s)
        
        GROUP BY e.id, i.cpf, e.name, c.fantasy_name, g.name
        ORDER BY valor_total_incentivos DESC
        """
    
    @staticmethod
    def get_incentives_by_month_employee() -> str:
        return """
        SELECT 
            e.id as employee_id,
            e.name as vendedor,
            i.cpf,
            
            TO_CHAR(i.reference_date, 'YYYY-MM') as mes,
            TO_CHAR(i.reference_date, 'Mon/YY') as mes_display,
            
            COUNT(i.id) as quantidade_mes,
            COALESCE(SUM(i.incentive_value), 0) as valor_mes
            
        FROM incentive i
        INNER JOIN employee e ON i.employee_id = e.id
        INNER JOIN customer c ON i.customer_id = c.id
        
        WHERE c.id = ANY(%(lojas_ids)s)
          AND e.active = true
          AND c.active = true
          AND TO_CHAR(i.reference_date, 'YYYY-MM') = ANY(%(meses)s)
        
        GROUP BY e.id, e.name, i.cpf, mes, mes_display
        ORDER BY e.name, mes 
        """
    
    @staticmethod
    def get_available_months() -> str:
        return """
        SELECT DISTINCT
            TO_CHAR(reference_date, 'YYYY-MM') as mes,
            TO_CHAR(reference_date, 'Mon/YYYY') as mes_display,
            COUNT(*) as total_incentivos
        FROM incentive
        WHERE reference_date IS NOT NULL
        GROUP BY mes, mes_display
        ORDER BY mes DESC
        """
    
    @staticmethod
    def get_incentives_details() -> str:
        return """
        SELECT 
            i.id,
            i.cpf,
            i.incentive_value as valor,
            i.reference_date as data_referencia,
            i.sale_document_number as numero_documento,
            i.state,
            
            e.id as employee_id,
            e.name as vendedor,
            
            c.id as customer_id,
            c.fantasy_name as loja,
            
            g.name as grupo,
            
            COALESCE(
                STRING_AGG(DISTINCT fn.name, ' / ' ORDER BY fn.name),
                'Não informado'
            ) as funcao,
            
            TO_CHAR(i.reference_date, 'YYYY-MM') as mes,
            TO_CHAR(i.reference_date, 'Mon/YY') as mes_display
            
        FROM incentive i
        INNER JOIN employee e ON i.employee_id = e.id
        INNER JOIN customer c ON i.customer_id = c.id
        LEFT JOIN groups g ON c.group_id = g.id
        LEFT JOIN employee_function ef ON e.id = ef.employee_id
        LEFT JOIN function fn ON ef.function_id = fn.id
        
        WHERE c.id = ANY(%(lojas_ids)s)
          AND e.active = true
          AND c.active = true
          AND TO_CHAR(i.reference_date, 'YYYY-MM') = ANY(%(meses)s)
        
        GROUP BY i.id, i.cpf, i.incentive_value, i.reference_date,
                 i.sale_document_number, i.state,
                 e.id, e.name, c.id, c.fantasy_name, g.name
        
        ORDER BY i.reference_date DESC, e.name
        """