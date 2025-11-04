import streamlit as st
import pandas as pd
from pathlib import Path
import locale
import sys

# Adicionar raiz do projeto ao path para imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils import selecionar_arquivo_excel, obter_ano_atual, carregar_dados_do_mongodb, MESES, adicionar_interface_edicao, criar_dialog_edicao, exportar_para_pdf, criar_dialog_cadastro_aluno

locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')

st.set_page_config(page_title='Pilates', layout='wide')
pasta_atual = Path(__file__).parent.parent / 'pilates'

# Seleção de mês e ano
ano = obter_ano_atual()
mes_nome = st.sidebar.selectbox(
    'Selecione o mês de referência',
    options=list(MESES.keys()),
    index=0
)
mes_abrev = MESES[mes_nome]

# Carregar dados do MongoDB
tabela_pilates = carregar_dados_do_mongodb('pilates', mes_abrev, mes_nome, ano)

if tabela_pilates is None or tabela_pilates.empty:
    st.warning("Nenhum dado encontrado no banco de dados para este período.")
    st.info("💡 Use a página 'Importar Arquivos' para importar dados.")
    st.stop()

# Filtro por Professor
if 'Professor' in tabela_pilates.columns:
    # Obter lista de professores únicos (incluindo NaN como "Sem Professor")
    professores_disponiveis = tabela_pilates['Professor'].dropna().unique().tolist()
    professores_disponiveis.sort()
    
    # Adicionar opção "Todos" e "Sem Professor"
    opcoes_professor = ['Todos'] + professores_disponiveis
    if tabela_pilates['Professor'].isna().any():
        opcoes_professor.append('Sem Professor')
    
    professor_selecionado = st.sidebar.selectbox(
        'Filtrar por Professor',
        options=opcoes_professor,
        index=0
    )
    
    # Aplicar filtro
    if professor_selecionado == 'Todos':
        tabela_pilates_filtrada = tabela_pilates.copy()
    elif professor_selecionado == 'Sem Professor':
        tabela_pilates_filtrada = tabela_pilates[tabela_pilates['Professor'].isna()].copy()
    else:
        tabela_pilates_filtrada = tabela_pilates[tabela_pilates['Professor'] == professor_selecionado].copy()
    
    tabela_pilates = tabela_pilates_filtrada
    
    if tabela_pilates.empty:
        st.warning(f"Nenhum dado encontrado para o professor '{professor_selecionado}'.")
        st.stop()
else:
    professor_selecionado = None

def calcular_valor_mensal(plano, valor):
    if "15 MESES" in plano:
        return valor / 15
    elif "ANUAL" in plano or "12 MESES" in plano:
        return valor / 12
    elif "SEMESTRAL" in plano:
        return valor / 6
    elif "TRIMESTRAL" in plano:
        return valor / 3
    else:
        return valor 

def processar_valores_pilates(tabela):
    """Processa os valores e adiciona colunas calculadas"""
    # Calcular valor mensal baseado no tipo de plano
    tabela.loc[:,"VALOR_MENSAL"] = tabela.apply(lambda row: calcular_valor_mensal(row["Contratos"], row["Valor"]), axis=1)    
    # Calcular 50% do VALOR_MENSAL (metade do valor mensal)
    tabela.loc[:,"50%"] = tabela["VALOR_MENSAL"] / 2
    
    # Salvar uma cópia antes da formatação para session_state
    tabela_state = tabela.copy()
    st.session_state["pilates"] = tabela_state
    
    return tabela

def formatar_valores_para_exibicao_pilates(tabela):
    """Formata os valores para exibição e adiciona linha de total"""
    # Calcular total antes da formatação
    total_50_percent = tabela["50%"].sum()
    
    # Formatar valores numéricos
    tabela_formatada = tabela.copy()
    tabela_formatada.loc[:,"Valor"] = tabela_formatada["Valor"].apply(lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    tabela_formatada.loc[:,"VALOR_MENSAL"] = tabela_formatada["VALOR_MENSAL"].apply(lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    tabela_formatada.loc[:,"50%"] = tabela_formatada["50%"].apply(lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    
    # Criar uma nova linha para o total
    linha_total = pd.DataFrame({
        'nome_completo': [''],
        'Contratos': [''],
        'Valor': [''],
        'Início': [''],
        'Vencimento': [''],
        'VALOR_MENSAL': [''],
        '50%': [f"{total_50_percent:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")],
        'Professor': ['']
    }, index=['Total a Pagar'])
    
    # Concatenar com a tabela formatada
    tabela_com_total = pd.concat([tabela_formatada, linha_total])
    
    return tabela_com_total

def formatar_valor_para_csv(valor):
    """Formata valor para CSV com vírgula como separador decimal"""
    if isinstance(valor, str):
        return valor
    return f"{valor:.2f}".replace(".", ",")

def exportar_tabela_pilates(mes_abrev, ano, professor_selecionado=None):
    """Exporta a tabela para PDF com resumo e tabela detalhada"""
    tabela_original = st.session_state.get("pilates", tabela_pilates)
    
    # Se há filtro por professor, usar a tabela filtrada
    if professor_selecionado and professor_selecionado != 'Todos':
        if professor_selecionado == 'Sem Professor':
            tabela_filtrada = tabela_original[tabela_original["Professor"].isna()].copy()
            nome_professor_export = "Sem Professor"
        else:
            tabela_filtrada = tabela_original[tabela_original["Professor"] == professor_selecionado].copy()
            nome_professor_export = professor_selecionado
    else:
        tabela_filtrada = tabela_original.copy()
        nome_professor_export = "Todos"
    
    # Calcular totais
    total_50_percent = tabela_filtrada['50%'].sum() if '50%' in tabela_filtrada.columns else 0
    num_registros = len(tabela_filtrada)
    
    # Preparar tabela para PDF (nome, início, vencimento e 50%)
    colunas_para_pdf = ['nome_completo', 'Início', 'Vencimento', '50%']
    tabela_para_pdf = tabela_filtrada[[col for col in colunas_para_pdf if col in tabela_filtrada.columns]].copy()
    
    # Criar nome do arquivo base
    if professor_selecionado and professor_selecionado != 'Todos':
        # Normalizar nome do professor para nome de arquivo
        nome_arquivo_prof = nome_professor_export.lower().replace(" ", "_").replace("ã", "a").replace("õ", "o")
        nome_arquivo_base = f'pilates_{nome_arquivo_prof}_{mes_abrev}_{ano}'
    else:
        nome_arquivo_base = f'pilates_{mes_abrev}_{ano}'
    
    # Exportar PDF
    caminho_pdf = exportar_para_pdf(
        total_50_percent=total_50_percent,
        num_registros=num_registros,
        nome_professor=nome_professor_export,
        mes_abrev=mes_abrev,
        ano=ano,
        pasta_destino=pasta_atual,
        nome_arquivo_base=nome_arquivo_base,
        tabela_dados=tabela_para_pdf
    )
    
    if caminho_pdf:
        st.success(f"PDF exportado com sucesso! ({nome_arquivo_base}.pdf)")
    else:
        st.error("Erro ao exportar PDF. Verifique se a biblioteca reportlab está instalada.")

if tabela_pilates is not None and not tabela_pilates.empty:
    # Processar dados
    tabela_pilates = processar_valores_pilates(tabela_pilates)
    
    ano = obter_ano_atual()
    
    # Sidebar com ações
    st.sidebar.header("Ações")
    
    with st.sidebar.container():
        if st.button('➕ Novo Aluno', use_container_width=True):
            st.session_state['dialog_cadastro_aberto'] = True
            st.rerun()

        if st.button('📥 Exportar PDF', use_container_width=True):
            exportar_tabela_pilates(mes_abrev, ano, professor_selecionado)

    # Abrir dialog de cadastro se necessário
    if st.session_state.get('dialog_cadastro_aberto', False):
        criar_dialog_cadastro_aluno('pilates', mes_abrev, ano, tem_professor=True)
        
        # Verificar se foi cadastrado e recarregar
        if st.session_state.get('aluno_cadastrado', False):
            st.session_state['aluno_cadastrado'] = False
            st.session_state['dialog_cadastro_aberto'] = False
            st.rerun()
    
    # Mostrar informação do filtro se aplicado
    if professor_selecionado and professor_selecionado != 'Todos':
        st.info(f"📋 Exibindo dados do professor: **{professor_selecionado}**")
    
    # Adicionar interface de edição
    tabela_pilates = adicionar_interface_edicao(tabela_pilates, 'pilates', mes_abrev, mes_nome, ano, 'Pilates')

