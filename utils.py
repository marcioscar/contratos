import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime

MESES = {
    'Janeiro': 'jan',
    'Fevereiro': 'fev',
    'Março': 'mar',
    'Abril': 'abr',
    'Maio': 'mai',
    'Junho': 'jun',
    'Julho': 'jul',
    'Agosto': 'ago',
    'Setembro': 'set',
    'Outubro': 'out',
    'Novembro': 'nov',
    'Dezembro': 'dez'
}

def obter_ano_atual():
    """Retorna o ano atual"""
    return datetime.now().year

def listar_arquivos_excel_disponiveis(pasta_atual, modalidade, mes_abrev, ano):
    """Lista arquivos Excel disponíveis na pasta da modalidade"""
    if not pasta_atual.exists():
        return []
    
    padrao = f"{modalidade}_{mes_abrev}_{ano}.xlsx"
    arquivos = list(pasta_atual.glob(f"{modalidade}_{mes_abrev}_{ano}.xlsx"))
    
    # Também buscar variações do nome
    arquivos.extend(pasta_atual.glob(f"{modalidade}_{mes_abrev}*.xlsx"))
    
    return sorted(arquivos, reverse=True)

def selecionar_arquivo_excel(modalidade, pasta_atual):
    """Interface para selecionar arquivo Excel existente (apenas leitura)"""
    ano = obter_ano_atual()
    
    # Seletor de mês
    mes_nome = st.sidebar.selectbox(
        'Selecione o mês de referência',
        options=list(MESES.keys()),
        index=8 if 'set' in str(pasta_atual).lower() else 0  # Setembro como padrão se detectado
    )
    mes_abrev = MESES[mes_nome]
    
    # Buscar arquivos existentes
    arquivos_disponiveis = listar_arquivos_excel_disponiveis(pasta_atual, modalidade, mes_abrev, ano)
    
    arquivo_selecionado = None
    
    if arquivos_disponiveis:
        arquivo_nome = st.sidebar.selectbox(
            'Selecione o arquivo',
            options=[arq.name for arq in arquivos_disponiveis],
            index=0
        )
        arquivo_selecionado = pasta_atual / arquivo_nome
    else:
        st.sidebar.warning(f'Nenhum arquivo encontrado para {modalidade} - {mes_nome}/{ano}')
        st.sidebar.info('💡 Use a página "Importar Arquivos" para fazer upload de novos arquivos')
        return None, mes_abrev, mes_nome
    
    return arquivo_selecionado, mes_abrev, mes_nome

def carregar_dados_do_mongodb(modalidade, mes_abrev, mes_nome, ano):
    """Carrega dados do MongoDB e retorna DataFrame formatado"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from db import buscar_contratos
    
    # Buscar contratos do MongoDB
    df = buscar_contratos(modalidade, mes_abrev, ano)
    
    if df.empty:
        return None
    
    # Renomear colunas para compatibilidade com código existente
    colunas_renomear = {
        'id_cliente': 'ID do cliente',
        'nome_completo': 'nome_completo',
        'contratos': 'Contratos',
        'valor': 'Valor',
        'inicio': 'Início',
        'vencimento': 'Vencimento',
        'valor_mensal': 'VALOR_MENSAL',
        'professor': 'Professor'
    }
    
    # Renomear apenas as colunas que existem
    for old_name, new_name in colunas_renomear.items():
        if old_name in df.columns:
            df = df.rename(columns={old_name: new_name})
    
    # Garantir que o índice seja ID do cliente se não estiver já definido
    if df.index.name != 'id_cliente' and 'ID do cliente' in df.columns:
        df = df.set_index('ID do cliente')
    elif df.index.name == 'id_cliente':
        # Se o índice já é id_cliente mas queremos renomear para 'ID do cliente'
        df.index.name = 'ID do cliente'
    
    # Converter tipos numéricos se necessário
    if 'Valor' in df.columns:
        df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce').fillna(0)
    if 'VALOR_MENSAL' in df.columns:
        df['VALOR_MENSAL'] = pd.to_numeric(df['VALOR_MENSAL'], errors='coerce').fillna(0)
    
    return df

@st.dialog("Cadastrar Novo Aluno", width="medium")
def dialog_cadastrar_aluno():
    """Dialog para cadastrar um novo aluno"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from db import cadastrar_contrato, calcular_valor_mensal, buscar_professores_unicos, buscar_planos_unicos
    
    # Recuperar dados da session_state
    dados = st.session_state.get('dialog_cadastro_data', {})
    if not dados:
        st.error("Erro: dados do dialog não encontrados")
        return
    
    modalidade = dados['modalidade']
    mes_abrev = dados['mes_abrev']
    ano = dados['ano']
    tem_professor = dados.get('tem_professor', False)
    
    st.write("**Cadastrar Novo Aluno**")
    
    # Campos para cadastro
    id_cliente = st.text_input("ID do Cliente", value="", placeholder="Digite o ID do cliente")
    nome_completo = st.text_input("Nome Completo", value="", placeholder="Digite o nome completo")
    
    # Buscar planos existentes
    planos_existentes = buscar_planos_unicos(modalidade)
    
    # Selectbox para planos com opção de digitar novo
    st.write("**Plano/Contrato**")
    opcao_plano = st.radio(
        "Escolha uma opção:",
        ["Selecionar plano existente", "Digitar novo plano"],
        horizontal=True,
        key="opcao_plano_cadastro"
    )
    
    if opcao_plano == "Selecionar plano existente":
        if planos_existentes:
            plano_selecionado = st.selectbox(
                "Selecione o plano:",
                options=planos_existentes,
                index=0 if planos_existentes else None,
                key="selectbox_plano_cadastro"
            )
            contratos = plano_selecionado if plano_selecionado else ""
        else:
            st.info("Nenhum plano cadastrado ainda. Use a opção 'Digitar novo plano'.")
            contratos = ""
    else:
        contratos = st.text_input("Digite o novo plano:", value="", placeholder="Ex: PILATES STUDIO 2X ANUAL", key="text_plano_cadastro")
    
    valor = st.number_input("Valor", value=0.0, step=0.01, format="%.2f")
    inicio = st.text_input("Início", value="", placeholder="DD/MM/AAAA")
    vencimento = st.text_input("Vencimento", value="", placeholder="DD/MM/AAAA")
    
    # Campo professor se a modalidade tiver
    professor_valor = None
    if tem_professor:
        # Buscar professores existentes
        professores_existentes = buscar_professores_unicos(modalidade)
        
        st.write("**Professor**")
        opcao_professor = st.radio(
            "Escolha uma opção:",
            ["Selecionar professor existente", "Digitar novo professor", "Sem professor"],
            horizontal=False,
            key="opcao_professor_cadastro"
        )
        
        if opcao_professor == "Selecionar professor existente":
            if professores_existentes:
                professor_selecionado = st.selectbox(
                    "Selecione o professor:",
                    options=professores_existentes,
                    index=0 if professores_existentes else None,
                    key="selectbox_professor_cadastro"
                )
                professor_valor = professor_selecionado if professor_selecionado else None
            else:
                st.info("Nenhum professor cadastrado ainda. Use a opção 'Digitar novo professor'.")
                professor_valor = None
        elif opcao_professor == "Digitar novo professor":
            professor_valor = st.text_input("Digite o nome do professor:", value="", placeholder="Nome do professor", key="text_professor_cadastro")
            professor_valor = professor_valor.strip() if professor_valor else None
        else:
            professor_valor = None
    
    # Calcular valor mensal baseado no contrato
    contratos_para_calculo = str(contratos).strip() if contratos else ""
    novo_valor_mensal = calcular_valor_mensal(contratos_para_calculo, valor) if contratos_para_calculo and valor else 0.0
    if contratos_para_calculo and valor:
        st.info(f"Valor Mensal Calculado: R$ {novo_valor_mensal:,.2f}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("💾 Salvar", type="primary", use_container_width=True):
            # Validações
            contratos_str = contratos_para_calculo  # Já foi processado acima
            professor_str = str(professor_valor).strip() if professor_valor else None
            if professor_str == "":
                professor_str = None
                
            if not id_cliente.strip():
                st.error("❌ ID do Cliente é obrigatório")
            elif not nome_completo.strip():
                st.error("❌ Nome Completo é obrigatório")
            elif not contratos_str:
                st.error("❌ Contratos é obrigatório")
            elif valor <= 0:
                st.error("❌ Valor deve ser maior que zero")
            elif not inicio.strip():
                st.error("❌ Data de Início é obrigatória")
            elif not vencimento.strip():
                st.error("❌ Data de Vencimento é obrigatória")
            else:
                try:
                    # Preparar dados para cadastro
                    dados_cadastro = {
                        'id_cliente': id_cliente.strip(),
                        'nome_completo': nome_completo.strip(),
                        'contratos': contratos_str,
                        'valor': valor,
                        'inicio': inicio.strip(),
                        'vencimento': vencimento.strip(),
                        'valor_mensal': novo_valor_mensal,
                        'professor': professor_str,
                        'modalidade': modalidade,
                        'mes_abrev': mes_abrev,
                        'ano': ano
                    }
                    
                    # Cadastrar no banco
                    cadastrar_contrato(**dados_cadastro)
                    
                    st.success("✅ Aluno cadastrado com sucesso!")
                    st.session_state['aluno_cadastrado'] = True
                    st.session_state['dialog_cadastro_aberto'] = False
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro: {str(e)}")
    
    with col2:
        if st.button("❌ Cancelar", use_container_width=True):
            st.session_state['dialog_cadastro_aberto'] = False
            st.rerun()

def criar_dialog_cadastro_aluno(modalidade, mes_abrev, ano, tem_professor=False):
    """Prepara e chama o dialog de cadastro de novo aluno"""
    # Verificar se há dialog de edição aberto
    key_dialog_edicao = f'dialog_aberto_{modalidade}'
    if st.session_state.get(key_dialog_edicao, False):
        st.warning("⚠️ Feche o dialog de edição antes de cadastrar um novo aluno.")
        return
    
    # Salvar dados na session_state para o dialog acessar
    st.session_state['dialog_cadastro_data'] = {
        'modalidade': modalidade,
        'mes_abrev': mes_abrev,
        'ano': ano,
        'tem_professor': tem_professor
    }
    
    # Chamar a função dialog diretamente
    dialog_cadastrar_aluno()

@st.dialog("Editar Contrato", width="medium")
def dialog_editar_contrato():
    """Dialog para editar um contrato"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from db import atualizar_contrato, calcular_valor_mensal
    
    # Recuperar dados da session_state
    dados = st.session_state.get('dialog_data', {})
    if not dados:
        st.error("Erro: dados do dialog não encontrados")
        return
    
    id_cliente = dados['id_cliente']
    linha_original = dados['linha_original']
    modalidade = dados['modalidade']
    mes_abrev = dados['mes_abrev']
    ano = dados['ano']
    
    st.write(f"**Editando contrato ID: {id_cliente}**")
    
    # Campos editáveis
    nome_completo = st.text_input("Nome Completo", value=str(linha_original.get('nome_completo', '')))
    contratos = st.text_input("Contratos", value=str(linha_original.get('Contratos', '')))
    valor = st.number_input("Valor", value=float(linha_original.get('Valor', 0)), step=0.01, format="%.2f")
    inicio = st.text_input("Início", value=str(linha_original.get('Início', '')))
    vencimento = st.text_input("Vencimento", value=str(linha_original.get('Vencimento', '')))
    
    # Campo professor se existir
    professor_valor = None
    if 'Professor' in linha_original:
        professor_valor = st.text_input("Professor", value=str(linha_original.get('Professor', '')) if linha_original.get('Professor') else '')
    
    # Calcular novo valor mensal baseado no contrato
    novo_valor_mensal = calcular_valor_mensal(contratos, valor)
    st.info(f"Valor Mensal Calculado: R$ {novo_valor_mensal:,.2f}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("💾 Salvar", type="primary", use_container_width=True):
            try:
                # Preparar dados para atualização
                dados_atualizacao = {
                    'id_cliente': id_cliente,
                    'modalidade': modalidade,
                    'mes_abrev': mes_abrev,
                    'ano': ano,
                    'nome_completo': nome_completo,
                    'contratos': contratos,
                    'valor': valor,
                    'inicio': inicio,
                    'vencimento': vencimento,
                    'valor_mensal': novo_valor_mensal
                }
                
                # Adicionar professor se o campo existir
                if professor_valor is not None:
                    dados_atualizacao['professor'] = professor_valor if professor_valor.strip() else None
                
                # Atualizar no banco
                sucesso = atualizar_contrato(**dados_atualizacao)
                
                if sucesso:
                    st.success("✅ Contrato atualizado com sucesso!")
                    # Usar a modalidade dos dados para criar a chave correta
                    modalidade = dados.get('modalidade', 'judo')
                    st.session_state[f'contrato_editado_{modalidade}'] = True
                    st.session_state[f'dialog_aberto_{modalidade}'] = False
                    # Limpar dados do dialog
                    if 'dialog_data' in st.session_state:
                        del st.session_state['dialog_data']
                    st.rerun()
                else:
                    st.error("❌ Erro ao atualizar contrato")
            except Exception as e:
                st.error(f"Erro: {str(e)}")
    
    with col2:
        if st.button("❌ Cancelar", use_container_width=True):
            modalidade = dados.get('modalidade', 'judo')
            st.session_state[f'dialog_aberto_{modalidade}'] = False
            # Limpar dados do dialog
            if 'dialog_data' in st.session_state:
                del st.session_state['dialog_data']
            st.rerun()

def criar_dialog_edicao(id_cliente, linha_original, modalidade, mes_abrev, ano):
    """Prepara e chama o dialog de edição"""
    # Verificar se há dialog de cadastro aberto
    if st.session_state.get('dialog_cadastro_aberto', False):
        st.warning("⚠️ Feche o dialog de cadastro antes de editar.")
        return
    
    # Salvar dados na session_state para o dialog acessar
    st.session_state['dialog_data'] = {
        'id_cliente': id_cliente,
        'linha_original': linha_original,
        'modalidade': modalidade,
        'mes_abrev': mes_abrev,
        'ano': ano
    }
    
    # Chamar a função dialog diretamente
    dialog_editar_contrato()

def adicionar_interface_edicao(tabela_original, modalidade, mes_abrev, mes_nome, ano, nome_pagina):
    """Adiciona interface de edição com checkboxes para qualquer página"""
    
    # Criar cópia para exibição (sem formatação ainda)
    tabela_para_exibicao = tabela_original.copy()
    
    # Remover linha "Total a Pagar" temporariamente para criar checkboxes
    tabela_sem_total = tabela_para_exibicao[tabela_para_exibicao.index != 'Total a Pagar'].copy()
    
    # Inicializar estado de seleção (por modalidade)
    key_selecionado = f'selecionado_{modalidade}'
    if key_selecionado not in st.session_state:
        st.session_state[key_selecionado] = {idx: False for idx in tabela_sem_total.index}
    
    # Adicionar coluna de seleção com checkboxes
    tabela_com_selecao = tabela_sem_total.copy()
    tabela_com_selecao['Selecionar'] = [st.session_state[key_selecionado].get(idx, False) for idx in tabela_com_selecao.index]
    
    # Resetar checkboxes se necessário
    key_reset = f'reset_checkboxes_{modalidade}'
    if key_reset in st.session_state and st.session_state[key_reset]:
        st.session_state[key_selecionado] = {idx: False for idx in tabela_sem_total.index}
        st.session_state[key_reset] = False
    
    st.header(f'{nome_pagina} - {mes_nome}/{ano}')
    
    # Criar interface com checkboxes
    ids_para_editar = []
    
    # Criar tabela com coluna de checkbox usando st.data_editor
    colunas_disponiveis = ['Selecionar', 'nome_completo', 'Contratos', 'Valor', 'Início', 'Vencimento', 'VALOR_MENSAL', '50%']
    if 'Professor' in tabela_com_selecao.columns:
        colunas_disponiveis.insert(-1, 'Professor')
    
    tabela_editavel = tabela_com_selecao[[col for col in colunas_disponiveis if col in tabela_com_selecao.columns]].copy()
    
    # Converter para formato editável
    tabela_editavel = tabela_editavel.reset_index()
    
    # Configuração de colunas
    column_config = {
        "Selecionar": st.column_config.CheckboxColumn("Selecionar", help="Marque para editar esta linha"),
        "nome_completo": st.column_config.TextColumn("Nome Completo", disabled=True),
        "Contratos": st.column_config.TextColumn("Contratos", disabled=True),
        "Valor": st.column_config.NumberColumn("Valor", format="%.2f", disabled=True),
        "Início": st.column_config.TextColumn("Início", disabled=True),
        "Vencimento": st.column_config.TextColumn("Vencimento", disabled=True),
        "VALOR_MENSAL": st.column_config.NumberColumn("Valor Mensal", format="%.2f", disabled=True),
        "50%": st.column_config.NumberColumn("50%", format="%.2f", disabled=True),
    }
    
    if "ID do cliente" in tabela_editavel.columns:
        column_config["ID do cliente"] = st.column_config.TextColumn("ID", disabled=True)
    
    if "Professor" in tabela_editavel.columns:
        column_config["Professor"] = st.column_config.TextColumn("Professor", disabled=True)
    
    # Usar st.data_editor para permitir edição de checkboxes
    edited_df = st.data_editor(
        tabela_editavel,
        column_config=column_config,
        hide_index=True,
        use_container_width=True,
        height=400
    )
    
    # Calcular e exibir total geral
    if not tabela_com_selecao.empty and '50%' in tabela_com_selecao.columns:
        total_50_percent = tabela_com_selecao['50%'].sum()
        total_valor_mensal = tabela_com_selecao['VALOR_MENSAL'].sum() if 'VALOR_MENSAL' in tabela_com_selecao.columns else 0
        
        # Criar linha de total formatada
        col1, col2, col3 = st.columns([2, 2, 2])
        with col1:
            st.metric("Total Valor Mensal", f"R$ {total_valor_mensal:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        with col2:
            st.metric("Total 50%", f"R$ {total_50_percent:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        with col3:
            num_registros = len(tabela_com_selecao)
            st.metric("Registros", num_registros)
    
    # Atualizar estado de seleção e verificar se alguma linha foi marcada
    nome_coluna_id = "ID do cliente" if "ID do cliente" in edited_df.columns else edited_df.columns[0]
    linha_marcada_agora = None
    
    for _, row in edited_df.iterrows():
        idx = row[nome_coluna_id]
        estava_selecionado = st.session_state[key_selecionado].get(idx, False)
        esta_selecionado = row['Selecionar']
        
        st.session_state[key_selecionado][idx] = esta_selecionado
        
        # Se acabou de marcar (não estava selecionado antes, mas está agora)
        if esta_selecionado and not estava_selecionado:
            linha_marcada_agora = idx
            ids_para_editar.append(idx)
        elif esta_selecionado:
            ids_para_editar.append(idx)
    
    # Se marcou uma linha agora e não há dialog aberto, abrir automaticamente
    key_dialog_aberto = f'dialog_aberto_{modalidade}'
    key_dialog_cadastro = 'dialog_cadastro_aberto'
    
    if linha_marcada_agora and not st.session_state.get(key_dialog_aberto, False) and not st.session_state.get(key_dialog_cadastro, False):
        # Desmarcar outras linhas
        for idx in st.session_state[key_selecionado]:
            if idx != linha_marcada_agora:
                st.session_state[key_selecionado][idx] = False
        
        st.session_state[key_dialog_aberto] = True
        st.session_state[f'id_para_editar_{modalidade}'] = linha_marcada_agora
        st.rerun()
    
    # Se marcou mais de uma linha, mostrar aviso
    if len(ids_para_editar) > 1:
        st.warning(f"⚠️ Você selecionou {len(ids_para_editar)} linhas. Selecione apenas uma para editar.")
    
    # Abrir dialog de edição se necessário (e não há dialog de cadastro aberto)
    if st.session_state.get(key_dialog_aberto, False) and f'id_para_editar_{modalidade}' in st.session_state and not st.session_state.get(key_dialog_cadastro, False):
        id_para_editar = st.session_state[f'id_para_editar_{modalidade}']
        linha_original = tabela_original.loc[id_para_editar].to_dict()
        criar_dialog_edicao(id_para_editar, linha_original, modalidade, mes_abrev, ano)
        
        # Verificar se foi salvo e recarregar
        key_contrato_editado = f'contrato_editado_{modalidade}'
        if st.session_state.get(key_contrato_editado, False):
            st.session_state[key_contrato_editado] = False
            st.session_state[key_dialog_aberto] = False
            st.session_state[key_selecionado][id_para_editar] = False
            st.session_state[key_reset] = True
            # Limpar dados do dialog
            if 'dialog_data' in st.session_state:
                del st.session_state['dialog_data']
            st.rerun()
    
    return tabela_original

def exportar_para_pdf(total_50_percent, num_registros, nome_professor, mes_abrev, ano, pasta_destino, nome_arquivo_base, tabela_dados=None):
    """Exporta um resumo em PDF com total 50%, número de registros, nome do professor e tabela com valores 50%
    
    Args:
        total_50_percent: Total do valor 50%
        num_registros: Número de registros
        nome_professor: Nome do professor ou 'Todos'
        mes_abrev: Mês abreviado
        ano: Ano
        pasta_destino: Path da pasta de destino
        nome_arquivo_base: Nome base do arquivo PDF
        tabela_dados: DataFrame opcional com dados para incluir na tabela (colunas: nome_completo, 50%)
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        
        # Criar nome do arquivo PDF
        nome_pdf = pasta_destino / f'{nome_arquivo_base}.pdf'
        
        # Criar documento PDF
        doc = SimpleDocTemplate(str(nome_pdf), pagesize=A4, 
                               rightMargin=2*cm, leftMargin=2*cm, 
                               topMargin=2*cm, bottomMargin=2*cm)
        story = []
        
        # Estilos
        styles = getSampleStyleSheet()
        titulo_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1f77b4'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=12,
            alignment=TA_LEFT
        )
        
        # Título
        story.append(Paragraph("Relatório de Pagamentos", titulo_style))
        story.append(Spacer(1, 0.5*cm))
        
        # Informações do professor (apenas se fornecido)
        if nome_professor:
            if nome_professor != 'Todos':
                story.append(Paragraph(f"<b>Professor:</b> {nome_professor}", normal_style))
            elif nome_professor == 'Sem Professor':
                story.append(Paragraph("<b>Professor:</b> Sem Professor", normal_style))
            else:
                story.append(Paragraph("<b>Professor:</b> Todos", normal_style))
            story.append(Spacer(1, 0.3*cm))
        
        # Período
        mes_nome_completo = {v: k for k, v in MESES.items()}.get(mes_abrev, mes_abrev)
        story.append(Paragraph(f"<b>Período:</b> {mes_nome_completo}/{ano}", normal_style))
        story.append(Spacer(1, 0.5*cm))
        
        # Tabela com os dados resumidos
        dados_resumo = [
            ['Item', 'Valor'],
            ['Total 50%', f"R$ {total_50_percent:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")],
            ['Número de Registros', str(num_registros)]
        ]
        
        tabela_resumo = Table(dados_resumo, colWidths=[8*cm, 8*cm])
        tabela_resumo.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 12),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        
        story.append(tabela_resumo)
        story.append(Spacer(1, 0.8*cm))
        
        # Adicionar tabela com os dados dos registros se fornecida
        if tabela_dados is not None and not tabela_dados.empty:
            # Título da tabela de registros
            story.append(Paragraph("<b>Detalhamento por Cliente</b>", ParagraphStyle(
                'TableTitle', parent=styles['Heading2'], fontSize=14, 
                textColor=colors.HexColor('#1f77b4'), spaceAfter=10, alignment=TA_LEFT
            )))
            story.append(Spacer(1, 0.3*cm))
            
            # Preparar dados da tabela (nome, início, vencimento e 50%)
            dados_tabela_registros = [['Nome do Cliente', 'Início', 'Vencimento', 'Valor 50%']]
            
            # Função para limitar tamanho do nome
            def limitar_nome(nome_completo, max_caracteres=30):
                """Limita o tamanho do nome e adiciona '...' se necessário"""
                nome = str(nome_completo).upper().strip()
                if len(nome) > max_caracteres:
                    return nome[:max_caracteres-3] + "..."
                return nome
            
            for idx, row in tabela_dados.iterrows():
                nome = limitar_nome(row.get('nome_completo', idx))
                inicio = str(row.get('Início', ''))
                vencimento = str(row.get('Vencimento', ''))
                valor_50 = row.get('50%', 0)
                if isinstance(valor_50, (int, float)):
                    valor_formatado = f"R$ {valor_50:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                else:
                    valor_formatado = str(valor_50)
                dados_tabela_registros.append([nome, inicio, vencimento, valor_formatado])
            
            # Adicionar linha de total
            dados_tabela_registros.append([
                'TOTAL', '', '',
                f"R$ {total_50_percent:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            ])
            
            # Criar tabela com larguras ajustadas para as 4 colunas
            larguras_colunas = [7*cm, 3.5*cm, 3.5*cm, 4*cm]
            tabela_registros = Table(dados_tabela_registros, colWidths=larguras_colunas)
            tabela_registros.setStyle(TableStyle([
                # Cabeçalho
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),
                # Linhas de dados
                ('ALIGN', (0, 1), (0, -2), 'LEFT'),  # Nome - esquerda
                ('ALIGN', (1, 1), (1, -2), 'CENTER'),  # Início - centro
                ('ALIGN', (2, 1), (2, -2), 'CENTER'),  # Vencimento - centro
                ('ALIGN', (3, 1), (3, -2), 'RIGHT'),  # Valor 50% - direita
                ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -2), 10),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.lightgrey]),
                # Limitar largura da coluna de nome para evitar sobreposição
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('WORDWRAP', (0, 1), (0, -2), True),  # Quebrar texto se necessário
                # Linha de total
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#E7E6E6')),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, -1), (-1, -1), 10),
                ('ALIGN', (0, -1), (2, -1), 'LEFT'),
                ('ALIGN', (3, -1), (3, -1), 'RIGHT'),
                ('TOPPADDING', (0, -1), (-1, -1), 6),
                ('BOTTOMPADDING', (0, -1), (-1, -1), 6),
            ]))
            
            story.append(tabela_registros)
            story.append(Spacer(1, 0.5*cm))
        
        # Rodapé
        story.append(Paragraph(f"<i>Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</i>", 
                              ParagraphStyle('CustomFooter', parent=styles['Normal'], fontSize=9, 
                                           textColor=colors.grey, alignment=TA_CENTER)))
        
        # Construir PDF
        doc.build(story)
        
        return str(nome_pdf)
    except ImportError:
        # Se reportlab não estiver instalado, tentar com outra biblioteca ou retornar erro
        st.error("Biblioteca reportlab não encontrada. Instale com: pip install reportlab")
        return None
    except Exception as e:
        st.error(f"Erro ao gerar PDF: {str(e)}")
        return None

# Função carregar_dados_do_mongodb exportada acima

