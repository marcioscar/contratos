import streamlit as st
import pandas as pd
from pathlib import Path
import sys

# Adicionar raiz do projeto ao path para imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils import selecionar_arquivo_excel, obter_ano_atual, carregar_dados_do_mongodb, MESES, adicionar_interface_edicao, exportar_para_pdf, criar_dialog_cadastro_aluno

st.set_page_config(page_title='Prime', layout='wide')
pasta_atual = Path(__file__).parent.parent / 'prime'

# Seleção de mês e ano
ano = obter_ano_atual()
mes_nome = st.sidebar.selectbox(
    'Selecione o mês de referência',
    options=list(MESES.keys()),
    index=0
)
mes_abrev = MESES[mes_nome]

# Carregar dados do MongoDB
tabela_prime = carregar_dados_do_mongodb('prime', mes_abrev, mes_nome, ano)

if tabela_prime is None or tabela_prime.empty:
    st.warning("Nenhum dado encontrado no banco de dados para este período.")
    st.info("💡 Use a página 'Importar Arquivos' para importar dados.")
    st.stop()

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

def processar_valores_prime(tabela):
    """Processa os valores e adiciona colunas calculadas"""
    # Calcular valor mensal baseado no tipo de plano
    tabela.loc[:,"VALOR_MENSAL"] = tabela.apply(lambda row: calcular_valor_mensal(row["Contratos"], row["Valor"]), axis=1)    
    # Calcular 50% do VALOR_MENSAL (metade do valor mensal)
    tabela.loc[:,"50%"] = tabela["VALOR_MENSAL"] / 2
    
    # Salvar uma cópia antes da formatação para session_state
    tabela_state = tabela.copy()
    st.session_state["prime"] = tabela_state
    
    return tabela

def formatar_valores_para_exibicao_prime(tabela):
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
        '50%': [f"{total_50_percent:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")]
    }, index=['Total a Pagar'])
    
    # Concatenar com a tabela formatada
    tabela_com_total = pd.concat([tabela_formatada, linha_total])
    
    return tabela_com_total

def formatar_valor_para_csv(valor):
    """Formata valor para CSV com vírgula como separador decimal"""
    if isinstance(valor, str):
        return valor
    return f"{valor:.2f}".replace(".", ",")

def exportar_tabela_prime(mes_abrev, ano):
    """Exporta a tabela para PDF"""
    tabela_original = st.session_state.get("prime", tabela_prime)
    
    # Calcular totais
    total_50_percent = tabela_original['50%'].sum() if '50%' in tabela_original.columns else 0
    num_registros = len(tabela_original)
    
    # Preparar tabela para PDF (nome, início, vencimento e 50%)
    colunas_para_pdf = ['nome_completo', 'Início', 'Vencimento', '50%']
    tabela_para_pdf = tabela_original[[col for col in colunas_para_pdf if col in tabela_original.columns]].copy()
    
    nome_arquivo_base = f'prime_{mes_abrev}_{ano}'
    
    # Exportar PDF
    caminho_pdf = exportar_para_pdf(
        total_50_percent=total_50_percent,
        num_registros=num_registros,
        nome_professor=None,  # Prime não tem professor
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

if tabela_prime is not None:
    # Processar dados
    tabela_prime = processar_valores_prime(tabela_prime)
    
    ano = obter_ano_atual()
    
    # Sidebar com ações
    st.sidebar.header("Ações")
    with st.sidebar.container():
        if st.button('➕ Novo Aluno', use_container_width=True):
            st.session_state['dialog_cadastro_aberto'] = True
            st.rerun()

        if st.button('📥 Exportar PDF', use_container_width=True):
            exportar_tabela_prime(mes_abrev, ano)

    # Abrir dialog de cadastro se necessário
    if st.session_state.get('dialog_cadastro_aberto', False):
        criar_dialog_cadastro_aluno('prime', mes_abrev, ano, tem_professor=False)
        
        # Verificar se foi cadastrado e recarregar
        if st.session_state.get('aluno_cadastrado', False):
            st.session_state['aluno_cadastrado'] = False
            st.session_state['dialog_cadastro_aberto'] = False
            st.rerun()
    
    # Adicionar interface de edição
    tabela_prime = adicionar_interface_edicao(tabela_prime, 'prime', mes_abrev, mes_nome, ano, 'Prime')
    
    st.divider()
    
    # Exibir tabela formatada completa
    tabela_final = formatar_valores_para_exibicao_prime(tabela_prime)
    st.subheader("Tabela Completa")
    st.dataframe(tabela_final, height=600, use_container_width=True)