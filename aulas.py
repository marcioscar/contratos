import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys
from datetime import datetime

# Adicionar raiz do projeto ao path para imports
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from db import buscar_dados_dashboard, conexao
from utils import MESES, obter_ano_atual

st.set_page_config(page_title='Dashboard de Aulas', layout='wide', page_icon='📊')

# Mapeamento de meses abreviados para nomes completos (para ordenação)
ORDEM_MESES = {
    'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4, 'mai': 5, 'jun': 6,
    'jul': 7, 'ago': 8, 'set': 9, 'out': 10, 'nov': 11, 'dez': 12
}

NOMES_MESES = {
    'jan': 'Janeiro', 'fev': 'Fevereiro', 'mar': 'Março', 'abr': 'Abril',
    'mai': 'Maio', 'jun': 'Junho', 'jul': 'Julho', 'ago': 'Agosto',
    'set': 'Setembro', 'out': 'Outubro', 'nov': 'Novembro', 'dez': 'Dezembro'
}

MODALIDADES = {
    'judo': 'Judo',
    'pilates': 'Pilates',
    'prime': 'Prime',
    'muay': 'Muay',
    'krav': 'Kravmaga',
    'kravmaga': 'Kravmaga'  # Fallback caso exista no BD
}

def processar_dados_dashboard(df):
    """Processa os dados do dashboard para facilitar visualização"""
    if df.empty:
        return df
    
    # Adicionar coluna com ordem do mês
    df['ordem_mes'] = df['mes'].map(ORDEM_MESES)
    
    # Adicionar nome completo do mês
    df['mes_nome'] = df['mes'].map(NOMES_MESES)
    
    # Adicionar nome completo da modalidade
    df['modalidade_nome'] = df['modalidade'].map(MODALIDADES)
    
    # Ordenar por ano, mês e modalidade
    df = df.sort_values(['ano', 'ordem_mes', 'modalidade'])
    
    return df

st.title('📊 Dashboard de Aulas')
st.markdown('---')

# Sidebar com filtros
st.sidebar.header('Filtros')

# Filtro por ano
ano_atual = obter_ano_atual()
anos_disponiveis = list(range(2020, ano_atual + 2))  # Inclui ano atual e próximo
ano_selecionado = st.sidebar.selectbox(
    'Selecione o Ano',
    options=anos_disponiveis,
    index=anos_disponiveis.index(ano_atual) if ano_atual in anos_disponiveis else len(anos_disponiveis) - 1
)

# Buscar dados
with st.spinner('Carregando dados...'):
    df_dashboard = buscar_dados_dashboard(ano=ano_selecionado)
    
    if df_dashboard.empty:
        st.warning(f'⚠️ Nenhum dado encontrado para o ano {ano_selecionado}.')
        st.stop()
    
    df_dashboard = processar_dados_dashboard(df_dashboard)

# Métricas principais
st.subheader('📈 Resumo Geral')

total_valor_mensal = df_dashboard['total_valor_mensal'].sum()
total_50_percent = df_dashboard['total_50_percent'].sum()
total_registros = df_dashboard['num_registros'].sum()
num_modalidades = df_dashboard['modalidade'].nunique()
num_meses = df_dashboard['mes'].nunique()

# Primeira linha: Valores monetários (3 colunas para dar mais espaço)
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        'Total Valor Mensal',
        f'R$ {total_valor_mensal:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    )

with col2:
    st.metric(
        'Total 50%',
        f'R$ {total_50_percent:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    )

with col3:
    st.metric('Total de Registros', f'{total_registros:,}'.replace(',', '.'))

# Segunda linha: Outras métricas (3 colunas)
col4, col5, col6 = st.columns(3)

with col4:
    st.metric('Modalidades Ativas', num_modalidades)

with col5:
    st.metric('Meses com Dados', num_meses)

with col6:
    # Calcular média mensal se houver meses
    if num_meses > 0:
        media_mensal = total_50_percent / num_meses
        st.metric(
            'Média Mensal 50%',
            f'R$ {media_mensal:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
        )
    else:
        st.metric('Média Mensal 50%', 'R$ 0,00')

st.markdown('---')

# Gráficos
tab1, tab2, tab3, tab4 = st.tabs(['📊 Comparação por Mês', '📈 Evolução Temporal', '💰 Valores por Modalidade', '📋 Tabela Detalhada'])

with tab1:
    st.subheader('Comparação de Valores 50% por Modalidade e Mês')
    
    # Preparar dados para gráfico de barras agrupadas
    df_pivot = df_dashboard.pivot_table(
        index='mes_nome',
        columns='modalidade_nome',
        values='total_50_percent',
        aggfunc='sum',
        fill_value=0
    )
    
    # Reordenar colunas pela ordem dos meses
    ordem_meses_nomes = [NOMES_MESES[m] for m in ORDEM_MESES.keys() if NOMES_MESES[m] in df_pivot.index]
    df_pivot = df_pivot.reindex([m for m in ordem_meses_nomes if m in df_pivot.index])
    
    # Criar gráfico de barras
    fig_barras = go.Figure()
    
    cores = {
        'Judo': '#1f77b4',
        'Pilates': '#ff7f0e',
        'Prime': '#2ca02c',
        'Muay': '#d62728',
        'Kravmaga': '#9467bd'
    }
    
    for modalidade in df_pivot.columns:
        fig_barras.add_trace(go.Bar(
            name=modalidade,
            x=df_pivot.index,
            y=df_pivot[modalidade],
            marker_color=cores.get(modalidade, '#888888')
        ))
    
    fig_barras.update_layout(
        title='Valores 50% por Modalidade e Mês',
        xaxis_title='Mês',
        yaxis_title='Valor 50% (R$)',
        barmode='group',
        height=500,
        xaxis={'categoryorder': 'array', 'categoryarray': ordem_meses_nomes}
    )
    
    st.plotly_chart(fig_barras, use_container_width=True)

with tab2:
    st.subheader('Evolução Temporal dos Valores 50%')
    
    # Criar gráfico de linha
    fig_linha = px.line(
        df_dashboard,
        x='mes_nome',
        y='total_50_percent',
        color='modalidade_nome',
        markers=True,
        labels={
            'mes_nome': 'Mês',
            'total_50_percent': 'Valor 50% (R$)',
            'modalidade_nome': 'Modalidade'
        },
        title='Evolução dos Valores 50% ao Longo dos Meses'
    )
    
    # Ordenar meses no eixo X
    fig_linha.update_xaxes(
        categoryorder='array',
        categoryarray=[NOMES_MESES[m] for m in ORDEM_MESES.keys()]
    )
    
    fig_linha.update_layout(height=500)
    st.plotly_chart(fig_linha, use_container_width=True)
    
    # Gráfico de área empilhada
    st.subheader('Comparação Acumulada (Área Empilhada)')
    
    fig_area = px.area(
        df_dashboard,
        x='mes_nome',
        y='total_50_percent',
        color='modalidade_nome',
        labels={
            'mes_nome': 'Mês',
            'total_50_percent': 'Valor 50% (R$)',
            'modalidade_nome': 'Modalidade'
        },
        title='Distribuição Acumulada dos Valores 50%'
    )
    
    fig_area.update_xaxes(
        categoryorder='array',
        categoryarray=[NOMES_MESES[m] for m in ORDEM_MESES.keys()]
    )
    
    fig_area.update_layout(height=500)
    st.plotly_chart(fig_area, use_container_width=True)

with tab3:
    st.subheader('Total de Valores por Modalidade')
    
    # Agrupar por modalidade
    df_modalidade = df_dashboard.groupby('modalidade_nome').agg({
        'total_valor_mensal': 'sum',
        'total_50_percent': 'sum',
        'num_registros': 'sum'
    }).reset_index()
    
    df_modalidade = df_modalidade.sort_values('total_50_percent', ascending=False)
    
    # Gráfico de pizza para distribuição percentual
    col1, col2 = st.columns(2)
    
    with col1:
        fig_pizza = px.pie(
            df_modalidade,
            values='total_50_percent',
            names='modalidade_nome',
            title='Distribuição Percentual dos Valores 50%',
            color_discrete_map=cores
        )
        fig_pizza.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pizza, use_container_width=True)
    
    with col2:
        # Gráfico de barras horizontais
        fig_barras_h = px.bar(
            df_modalidade,
            x='total_50_percent',
            y='modalidade_nome',
            orientation='h',
            labels={
                'total_50_percent': 'Valor 50% (R$)',
                'modalidade_nome': 'Modalidade'
            },
            title='Total de Valores 50% por Modalidade',
            color='modalidade_nome',
            color_discrete_map=cores
        )
        fig_barras_h.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig_barras_h, use_container_width=True)
    
    # Métricas por modalidade
    st.subheader('Métricas Detalhadas por Modalidade')
    
    for _, row in df_modalidade.iterrows():
        with st.expander(f"📌 {row['modalidade_nome']}"):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(
                    'Total Valor Mensal',
                    f"R$ {row['total_valor_mensal']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                )
            with col2:
                st.metric(
                    'Total 50%',
                    f"R$ {row['total_50_percent']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                )
            with col3:
                st.metric('Registros', f"{row['num_registros']:,}".replace(',', '.'))

with tab4:
    st.subheader('Tabela Detalhada de Dados')
    
    # Preparar tabela para exibição
    df_tabela = df_dashboard.copy()
    df_tabela['total_valor_mensal'] = df_tabela['total_valor_mensal'].apply(
        lambda x: f"R$ {x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    )
    df_tabela['total_50_percent'] = df_tabela['total_50_percent'].apply(
        lambda x: f"R$ {x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    )
    
    # Selecionar colunas para exibição
    df_exibicao = df_tabela[['ano', 'mes_nome', 'modalidade_nome', 'total_valor_mensal', 'total_50_percent', 'num_registros']].copy()
    df_exibicao.columns = ['Ano', 'Mês', 'Modalidade', 'Total Valor Mensal', 'Total 50%', 'Nº Registros']
    
    st.dataframe(
        df_exibicao,
        use_container_width=True,
        hide_index=True
    )
    
    # Botão para download
    csv = df_dashboard.to_csv(index=False, sep=';', decimal=',')
    st.download_button(
        label='📥 Download CSV',
        data=csv,
        file_name=f'dashboard_aulas_{ano_selecionado}.csv',
        mime='text/csv'
    )

st.markdown('---')
st.caption(f'Última atualização: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}')

