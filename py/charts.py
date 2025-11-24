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

def create_evolucao_temporal_chart(df_temporal: pd.DataFrame) -> go.Figure:
    if df_temporal.empty:
        # Retorna gráfico vazio
        fig = go.Figure()
        fig.add_annotation(
            text="Nenhum dado disponível para o período selecionado",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="gray")
        )
        return fig
    
    fig = go.Figure()
    
    # Cores para as lojas (cicla automaticamente)
    cores = ['#47C7DA', '#F63366', '#FFA500', '#9B59B6', '#2ECC71', '#E74C3C']
    
    lojas = df_temporal['Nome_Loja'].unique()
    
    # === ADICIONA LINHAS DE TOTAL DE PRODUTOS (Eixo Esquerdo) ===
    for i, loja in enumerate(lojas):
        df_loja = df_temporal[df_temporal['Nome_Loja'] == loja].sort_values('Periodo_Str')
        
        fig.add_trace(go.Scatter(
            x=df_loja['Periodo_Str'],
            y=df_loja['Total_Produtos'],
            name=f'{loja} - Produtos',
            mode='lines+markers',
            line=dict(color=cores[i % len(cores)], width=2),
            marker=dict(size=8),
            yaxis='y1',
            hovertemplate='<b>%{fullData.name}</b><br>Período: %{x}<br>Produtos: %{y:,.0f}<extra></extra>'
        ))
    
    # === ADICIONA LINHAS DE FATURAMENTO (Eixo Direito) ===
    for i, loja in enumerate(lojas):
        df_loja = df_temporal[df_temporal['Nome_Loja'] == loja].sort_values('Periodo_Str')
        
        fig.add_trace(go.Scatter(
            x=df_loja['Periodo_Str'],
            y=df_loja['Venda_RS'],
            name=f'{loja} - Faturamento',
            mode='lines+markers',
            line=dict(color=cores[i % len(cores)], width=2, dash='dash'),
            marker=dict(size=8, symbol='square'),
            yaxis='y2',
            hovertemplate='<b>%{fullData.name}</b><br>Período: %{x}<br>Faturamento: R$ %{y:,.2f}<extra></extra>'
        ))
    
    # === LAYOUT COM EIXOS DUPLOS ===
    fig.update_layout(
        title='📈 Evolução Temporal: Produtos e Faturamento por Loja',
        xaxis=dict(
            title='Período',
            tickangle=-45
        ),
        yaxis=dict(
            title='Total de Produtos',
            side='left',
            showgrid=True,
            gridcolor='rgba(200, 200, 200, 0.2)'
        ),
        yaxis2=dict(
            title='Faturamento (R$)',
            overlaying='y',
            side='right',
            showgrid=False
        ),
        hovermode='x unified',
        legend=dict(
            orientation='v',
            yanchor='top',
            y=1,
            xanchor='left',
            x=1.15
        ),
        height=500,
        template='plotly_white'
    )
    return fig