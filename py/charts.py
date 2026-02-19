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

def create_incentive_pie_chart(df_employee: pd.DataFrame) -> go.Figure:
    if df_employee.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Nenhum dado disponível",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="gray")
        )
        return fig
    
    df_top = df_employee.nlargest(10, 'valor_total_incentivos')
    
    fig = px.pie(
        df_top,
        names='vendedor',
        values='valor_total_incentivos',
        title='Distribuição de Incentivos por Vendedor (Top 10)',
        hole=0.3,
        height=450
    )
    
    fig.update_traces(
        textposition='inside',
        textinfo='percent+label',
        hovertemplate='<b>%{label}</b><br>Valor: R$ %{value:,.2f}<br>Percentual: %{percent}<extra></extra>'
    )
    
    return fig


def create_incentive_bar_chart(df_employee: pd.DataFrame, top_n: int = 15, plot_height: int = 500) -> go.Figure:
    if df_employee.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Nenhum dado disponível",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="gray")
        )
        return fig
    
    df_top = df_employee.nlargest(top_n, 'valor_total_incentivos')
    
    fig = px.bar(
        df_top,
        x='vendedor',
        y='valor_total_incentivos',
        title=f'Top {top_n} Vendedores - Incentivos Recebidos',
        color='funcao',
        text='valor_total_incentivos',
        height=plot_height
    )
    
    fig.update_traces(
        texttemplate='R$ %{y:,.2f}',
        textposition='outside'
    )
    
    fig.update_layout(
        xaxis_title="Vendedor",
        yaxis_title="Valor Total (R$)",
        xaxis_tickangle=-45,
        showlegend=True
    )
    
    return fig


def create_monthly_comparison_bar_chart(df_monthly: pd.DataFrame) -> go.Figure:
    if df_monthly.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Nenhum dado disponível",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="gray")
        )
        return fig
    
    top_vendedores = (
        df_monthly.groupby('vendedor')['valor_mes']
        .sum()
        .nlargest(10)
        .index.tolist()
    )
    
    df_filtered = df_monthly[df_monthly['vendedor'].isin(top_vendedores)]
    
    fig = px.bar(
        df_filtered,
        x='mes_display',
        y='valor_mes',
        color='vendedor',
        title='Evolução Mensal de Incentivos (Top 10 Vendedores)',
        barmode='group',
        height=500
    )
    
    fig.update_layout(
        xaxis_title="Período",
        yaxis_title="Valor (R$)",
        xaxis_tickangle=-45,
        legend_title="Vendedor",
        hovermode='x unified'
    )
    
    fig.update_traces(
        hovertemplate='<b>%{fullData.name}</b><br>Valor: R$ %{y:,.2f}<extra></extra>'
    )
    
    return fig


def create_monthly_stores_comparison_chart(df_monthly: pd.DataFrame, df_employee: pd.DataFrame) -> go.Figure:
    if df_monthly.empty or df_employee.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Nenhum dado disponível",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="gray")
        )
        return fig
    
    df_with_loja = df_monthly.merge(
        df_employee[['vendedor', 'loja']],
        on='vendedor',
        how='left'
    )
    
    df_lojas_mes = df_with_loja.groupby(['loja', 'mes_display', 'mes']).agg({
        'valor_mes': 'sum',
        'quantidade_mes': 'sum'
    }).reset_index()
    
    df_lojas_mes = df_lojas_mes.sort_values('mes')
    
    fig = px.bar(
        df_lojas_mes,
        x='mes_display',
        y='valor_mes',
        color='loja',
        title='Comparação de Incentivos por Loja - Evolução Mensal',
        barmode='group',
        height=500,
        text='valor_mes'
    )
    
    fig.update_traces(
        texttemplate='R$ %{text:,.0f}',
        textposition='outside',
        hovertemplate='<b>%{fullData.name}</b><br>Período: %{x}<br>Valor: R$ %{y:,.2f}<extra></extra>'
    )
    
    fig.update_layout(
        xaxis_title="Período",
        yaxis_title="Valor Total de Incentivos (R$)",
        xaxis_tickangle=-45,
        legend_title="Loja",
        hovermode='x unified',
        showlegend=True
    )
    
    return fig


def format_incentive_monthly_table(df_pivot: pd.DataFrame) -> pd.DataFrame:
    if df_pivot.empty:
        return pd.DataFrame()
    
    df_display = df_pivot.copy()
    
    for col in df_display.columns:
        if col != 'vendedor' and col != 'Vendedor':
            df_display[col] = df_display[col].apply(
                lambda x: f"R$ {x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.') if pd.notna(x) else "R$ 0,00"
            )
    
    return df_display


def create_sell_in_chart(df_sell_in: pd.DataFrame, consultor_selecionado: list, plot_height: int = 400) -> go.Figure:
    if df_sell_in.empty:
        fig = go.Figure()
        fig.add_annotation(text="Nenhum dado disponível",)
        return fig
    
    df_filtered = df_sell_in[df_sell_in['Consultor'].isin(consultor_selecionado)]
    
    if df_filtered.empty:
        fig = go.Figure()
        fig.add_annotation(text="Nenhum consultor selecionado",)
        return fig
    
    fig = px.bar(
        df_filtered,
        x='Consultor',
        y='Sell_In_Percentual',
        title='Sell In por Consultor',
        text='Sell_In_Percentual',
        color='Sell_In_Percentual',
        color_continuous_scale='Blues',
        height=plot_height
    )
    
    fig.update_traces(texttemplate='%{y:.1f}%', textposition='outside')
    fig.update_layout(xaxis_title="Consultor", yaxis_title="Sell In (%)",)
    fig.update_coloraxes(showscale=False)
    
    return fig