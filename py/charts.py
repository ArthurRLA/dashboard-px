import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def create_ranking_chart(df_ranking_filtered: pd.DataFrame, kpi_selecionado: str, value_col_name: str, plot_height: int) -> go.Figure:
    """Cria o gráfico de barras de ranking dinâmico."""
    
    is_currency = 'R$' in kpi_selecionado or 'MÉDIO' in kpi_selecionado
    if is_currency:
        format_text = 'R$ %{y:,.2f}'
        y_title = f'{kpi_selecionado} (R$)'
    else:
        format_text = '%{y:,.2f}' if kpi_selecionado == 'PERFORMANCE' else '%{y:,.0f}'
        y_title = kpi_selecionado

    fig_ranking = px.bar(
        df_ranking_filtered.sort_values(by=value_col_name, ascending=False),
        x='Consultor',
        y=value_col_name,
        title=f'Ranking Regional por {kpi_selecionado}',
        color='Consultor',
        text=value_col_name,
        height=plot_height
    )

    fig_ranking.update_traces(texttemplate=format_text, textposition='outside')
    fig_ranking.update_layout(
        xaxis_title="Consultor",
        yaxis_title=y_title,
        showlegend=False
    )
    return fig_ranking

def create_produtos_chart(df_produtos_consultor: pd.DataFrame, consultor_selecionado: list) -> go.Figure:
    """Cria o gráfico de barras de Total de Produtos/consultor."""
    fig_produtos = px.bar(
        df_produtos_consultor[df_produtos_consultor['Consultor'].isin(consultor_selecionado)],
        x='Consultor',
        y='Total_Produtos',
        title='Total de Produtos/consultor',
        text='Total_Produtos'
    )
    fig_produtos.update_traces(texttemplate='%{y:,.0f}', textposition='outside')
    return fig_produtos

def create_performance_chart(df_performance: pd.DataFrame, consultor_selecionado: list) -> go.Figure:
    """Cria o gráfico de barras de Performance (produtos/passagem)."""
    df_performance_filtered = df_performance[df_performance['Consultor'].isin(consultor_selecionado)]

    fig_performance = px.bar(
        df_performance_filtered,
        x='Consultor',
        y='Performance',
        title='Performance: produtos/passagem',
        text='Performance',
        color_discrete_sequence=['#1f77b4'] 
    )
    fig_performance.update_traces(texttemplate='%{y:.2f}', textposition='outside')
    fig_performance.update_yaxes(range=[0, 1.60], title='Performance') 
    return fig_performance

def create_penetracao_chart(df_produtos: pd.DataFrame) -> go.Figure:
    # Detecta qual coluna usar
    if 'Descricao' in df_produtos.columns:
        col_produto = 'Descricao'
    elif 'Produto' in df_produtos.columns:
        col_produto = 'Produto'
    
    fig_penetracao = px.pie(
        df_produtos,
        names=col_produto,  # ✅ Usa a coluna detectada
        values='Penetracao_Produto',
        title='Penetração produto/OS',
        hole=.3,
        height=450
    )
    fig_penetracao.update_traces(textposition='inside', textinfo='percent+label')
    return fig_penetracao