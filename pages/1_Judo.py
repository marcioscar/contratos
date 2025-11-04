import streamlit as st
import pandas as pd
from pathlib import Path
import locale
import sys

# Adicionar raiz do projeto ao path para imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils import selecionar_arquivo_excel, obter_ano_atual, carregar_dados_do_mongodb, MESES, criar_dialog_edicao, exportar_para_pdf, criar_dialog_cadastro_aluno

locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')

st.set_page_config(page_title='Judo', layout='wide')
pasta_atual = Path(__file__).parent.parent / 'judo'

# Seleção de mês e ano
ano = obter_ano_atual()
mes_nome = st.sidebar.selectbox(
    'Selecione o mês de referência',
    options=list(MESES.keys()),
    index=0
)
mes_abrev = MESES[mes_nome]

# Carregar dados do MongoDB
tabela_judo = carregar_dados_do_mongodb('judo', mes_abrev, mes_nome, ano)

if tabela_judo is None or tabela_judo.empty:
    st.warning("Nenhum dado encontrado no banco de dados para este período.")
    st.info("💡 Use a página 'Importar Arquivos' para importar dados.")
    st.stop()

def calcular_valor_mensal(plano, valor):
    """Calcula o valor mensal baseado no tipo de plano"""
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

def processar_valores(tabela):
    """Processa os valores e adiciona colunas calculadas"""
    # Calcular valor mensal baseado no tipo de plano
    tabela.loc[:,"VALOR_MENSAL"] = tabela.apply(lambda row: calcular_valor_mensal(row["Contratos"], row["Valor"]), axis=1)    
    # Calcular 50% do VALOR_MENSAL (metade do valor mensal)
    tabela.loc[:,"50%"] = tabela["VALOR_MENSAL"] / 2
    
    # Salvar uma cópia antes da formatação para session_state
    tabela_state = tabela.copy()
    st.session_state["judo"] = tabela_state
    
    return tabela

def formatar_valores_para_exibicao(tabela):
    """Formata os valores para exibição e adiciona linha de total"""
    # Calcular total antes da formatação
    total_50_percent = tabela["50%"].sum()
    
    # Formatar valores numéricos
    tabela_formatada = tabela.copy()
    tabela_formatada.loc[:,"Valor"] = tabela_formatada["Valor"].apply(lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    tabela_formatada.loc[:,"VALOR_MENSAL"] = tabela_formatada["VALOR_MENSAL"].apply(lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    tabela_formatada.loc[:,"50%"] = tabela_formatada["50%"].apply(lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    
    # Criar uma nova linha para o total sem afetar o índice original
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
    return f"{valor:.2f}".replace(".", ",")

def exportar_tabela(mes_abrev, ano):
    """Exporta a tabela para PDF"""
    tabela_original = st.session_state.get("judo", tabela_judo)
    
    # Calcular totais
    total_50_percent = tabela_original['50%'].sum() if '50%' in tabela_original.columns else 0
    num_registros = len(tabela_original)
    
    # Preparar tabela para PDF (nome, início, vencimento e 50%)
    colunas_para_pdf = ['nome_completo', 'Início', 'Vencimento', '50%']
    tabela_para_pdf = tabela_original[[col for col in colunas_para_pdf if col in tabela_original.columns]].copy()
    
    nome_arquivo_base = f'judo_{mes_abrev}_{ano}'
    
    # Exportar PDF
    caminho_pdf = exportar_para_pdf(
        total_50_percent=total_50_percent,
        num_registros=num_registros,
        nome_professor=None,  # Judo não tem professor
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


if tabela_judo is not None:
    # Processar dados
    tabela_judo = processar_valores(tabela_judo)
    
    ano = obter_ano_atual()
    
    # Sidebar com ações
    st.sidebar.header("Ações")
    with st.sidebar.container():
        if st.button('➕ Novo Aluno', use_container_width=True):
            st.session_state['dialog_cadastro_aberto'] = True
            st.rerun()
        if st.button('📥 Exportar PDF', use_container_width=True):
                exportar_tabela(mes_abrev, ano)
        
    # Abrir dialog de cadastro se necessário
    if st.session_state.get('dialog_cadastro_aberto', False):
        criar_dialog_cadastro_aluno('judo', mes_abrev, ano, tem_professor=False)
        
        # Verificar se foi cadastrado e recarregar
        if st.session_state.get('aluno_cadastrado', False):
            st.session_state['aluno_cadastrado'] = False
            st.session_state['dialog_cadastro_aberto'] = False
            st.rerun()
    
    # Criar cópia para exibição (sem formatação ainda)
    tabela_para_exibicao = tabela_judo.copy()
    
    # Remover linha "Total a Pagar" temporariamente para criar checkboxes
    tabela_sem_total = tabela_para_exibicao[tabela_para_exibicao.index != 'Total a Pagar'].copy()
    
    # Inicializar estado de seleção
    if 'selecionado' not in st.session_state:
        st.session_state['selecionado'] = {idx: False for idx in tabela_sem_total.index}
    
    # Adicionar coluna de seleção com checkboxes
    tabela_com_selecao = tabela_sem_total.copy()
    tabela_com_selecao['Selecionar'] = [st.session_state['selecionado'].get(idx, False) for idx in tabela_com_selecao.index]
    
    # Resetar checkboxes se necessário
    if 'reset_checkboxes' in st.session_state and st.session_state['reset_checkboxes']:
        st.session_state['selecionado'] = {idx: False for idx in tabela_sem_total.index}
        st.session_state['reset_checkboxes'] = False
    
    st.header(f'Judo - {mes_nome}/{ano}')
    
    # Criar interface com checkboxes
    ids_para_editar = []
    
    # Criar tabela com coluna de checkbox usando st.data_editor
    tabela_editavel = tabela_com_selecao[['Selecionar', 'nome_completo', 'Contratos', 'Valor', 'Início', 'Vencimento', 'VALOR_MENSAL', '50%']].copy()
    
    # Converter para formato editável (reset_index preserva o nome do índice)
    tabela_editavel = tabela_editavel.reset_index()
    
    # Garantir que o nome da coluna do índice seja 'ID do cliente'
    if tabela_editavel.index.name == 'ID do cliente' or 'ID do cliente' not in tabela_editavel.columns:
        # Se o índice já tem o nome correto, o reset_index cria a coluna com esse nome
        pass
    
    # Usar st.data_editor para permitir edição de checkboxes
    edited_df = st.data_editor(
        tabela_editavel,
        column_config={
            "Selecionar": st.column_config.CheckboxColumn("Selecionar", help="Marque para editar esta linha"),
            "ID do cliente": st.column_config.TextColumn("ID", disabled=True) if "ID do cliente" in tabela_editavel.columns else None,
            "nome_completo": st.column_config.TextColumn("Nome Completo", disabled=True),
            "Contratos": st.column_config.TextColumn("Contratos", disabled=True),
            "Valor": st.column_config.NumberColumn("Valor", format="%.2f", disabled=True),
            "Início": st.column_config.TextColumn("Início", disabled=True),
            "Vencimento": st.column_config.TextColumn("Vencimento", disabled=True),
            "VALOR_MENSAL": st.column_config.NumberColumn("Valor Mensal", format="%.2f", disabled=True),
            "50%": st.column_config.NumberColumn("50%", format="%.2f", disabled=True),
        },
        hide_index=True,
        use_container_width=True,
        height=400
    )
    
    # Atualizar estado de seleção e verificar se alguma linha foi marcada
    nome_coluna_id = "ID do cliente" if "ID do cliente" in edited_df.columns else edited_df.columns[0]
    linha_marcada_agora = None
    
    for _, row in edited_df.iterrows():
        idx = row[nome_coluna_id]
        estava_selecionado = st.session_state['selecionado'].get(idx, False)
        esta_selecionado = row['Selecionar']
        
        st.session_state['selecionado'][idx] = esta_selecionado
        
        # Se acabou de marcar (não estava selecionado antes, mas está agora)
        if esta_selecionado and not estava_selecionado:
            linha_marcada_agora = idx
            ids_para_editar.append(idx)
        elif esta_selecionado:
            ids_para_editar.append(idx)
    
    # Chave específica para dialog de edição do judo
    key_dialog_aberto = 'dialog_aberto_judo'
    
    # Se marcou uma linha agora e não há dialog aberto, abrir automaticamente
    if linha_marcada_agora and not st.session_state.get(key_dialog_aberto, False) and not st.session_state.get('dialog_cadastro_aberto', False):
        # Desmarcar outras linhas
        for idx in st.session_state['selecionado']:
            if idx != linha_marcada_agora:
                st.session_state['selecionado'][idx] = False
        
        st.session_state[key_dialog_aberto] = True
        st.session_state['id_para_editar_judo'] = linha_marcada_agora
        st.rerun()
    
    # Se marcou mais de uma linha, mostrar aviso
    if len(ids_para_editar) > 1:
        st.warning(f"⚠️ Você selecionou {len(ids_para_editar)} linhas. Selecione apenas uma para editar.")
    
    # Abrir dialog de edição se necessário
    if st.session_state.get(key_dialog_aberto, False) and 'id_para_editar_judo' in st.session_state and not st.session_state.get('dialog_cadastro_aberto', False):
        id_para_editar = st.session_state['id_para_editar_judo']
        linha_original = tabela_judo.loc[id_para_editar].to_dict()
        criar_dialog_edicao(id_para_editar, linha_original, 'judo', mes_abrev, ano)
        
        # Verificar se foi salvo e recarregar
        if st.session_state.get('contrato_editado_judo', False):
            st.session_state['contrato_editado_judo'] = False
            st.session_state[key_dialog_aberto] = False
            st.session_state['selecionado'][id_para_editar] = False
            st.session_state['reset_checkboxes'] = True
            st.rerun()
    
    
    

