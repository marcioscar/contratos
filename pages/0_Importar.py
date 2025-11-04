import streamlit as st
import pandas as pd
from pathlib import Path
import sys
from datetime import datetime

# Adicionar raiz do projeto ao path para imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils import MESES, obter_ano_atual

st.set_page_config(page_title='Importar Arquivos', layout='wide')

st.header('📥 Importar Arquivos Excel')

MODALIDADES = {
    'Judo': 'judo',
    'Pilates': 'pilates',
    'Prime': 'prime',
    'Muay': 'muay',
    'Kravmaga': 'krav'
}

def obter_pasta_modalidade(modalidade):
    """Retorna o caminho da pasta da modalidade"""
    base_path = Path(__file__).parent.parent
    return base_path / modalidade

# Seleção de modalidade
modalidade_nome = st.selectbox(
    'Selecione a modalidade',
    options=list(MODALIDADES.keys()),
    index=0
)
modalidade = MODALIDADES[modalidade_nome]

# Seleção de ano
ano_atual = obter_ano_atual()
anos = list(range(ano_atual - 2, ano_atual + 2))
ano = st.selectbox(
    'Selecione o ano',
    options=anos,
    index=anos.index(ano_atual) if ano_atual in anos else len(anos) - 1
)

# Seleção de mês
mes_nome = st.selectbox(
    'Selecione o mês de referência',
    options=list(MESES.keys()),
    index=0
)
mes_abrev = MESES[mes_nome]

# Upload de arquivo
st.divider()
arquivo_upload = st.file_uploader(
    f'Faça upload do arquivo Excel para {modalidade_nome} - {mes_nome}/{ano}',
    type=['xlsx', 'xls'],
    key=f'upload_{modalidade}_{mes_abrev}_{ano}'
)

if arquivo_upload is not None:
    # Obter pasta da modalidade
    pasta_modalidade = obter_pasta_modalidade(modalidade)
    
    # Criar pasta se não existir
    pasta_modalidade.mkdir(parents=True, exist_ok=True)
    
    # Salvar arquivo na pasta da modalidade
    nome_arquivo_sugerido = f"{modalidade}_{mes_abrev}_{ano}.xlsx"
    arquivo_destino = pasta_modalidade / nome_arquivo_sugerido
    
    # Verificar se arquivo já existe
    if arquivo_destino.exists():
        st.warning(f"⚠️ Arquivo já existe: {nome_arquivo_sugerido}")
        sobrescrever = st.checkbox('Sobrescrever arquivo existente?')
        if not sobrescrever:
            st.stop()
    
    # Salvar arquivo e importar para MongoDB
    try:
        with open(arquivo_destino, 'wb') as f:
            f.write(arquivo_upload.getvalue())
        
        st.success(f"✅ Arquivo salvo com sucesso: {nome_arquivo_sugerido}")
        st.info(f"📁 Localização: {arquivo_destino}")
        
        # Importar automaticamente para MongoDB
        try:
            # Importar função do db.py
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from db import importar_planilha_para_mongodb, deletar_contratos_por_periodo
            
            with st.spinner('Importando dados para MongoDB...'):
                # Deletar contratos existentes do mesmo período antes de importar
                deletados = deletar_contratos_por_periodo(modalidade, mes_abrev, ano)
                if deletados > 0:
                    st.info(f'🗑️ {deletados} contratos antigos removidos')
                
                # Importar novos contratos
                contratos_inseridos = importar_planilha_para_mongodb(
                    arquivo_destino, 
                    modalidade, 
                    mes_abrev, 
                    ano
                )
                
                st.success(f"✅ {contratos_inseridos} contratos importados com sucesso para o MongoDB!")
                st.info(f"📊 Modalidade: {modalidade_nome} | Mês: {mes_nome}/{ano}")
        except Exception as e:
            st.error(f"Erro ao importar para MongoDB: {str(e)}")
            st.exception(e)
        
        # Mostrar preview do arquivo
        st.divider()
        st.subheader('Preview do arquivo importado')
        try:
            df_preview = pd.read_excel(arquivo_destino, nrows=5)
            st.dataframe(df_preview)
        except Exception as e:
            st.error(f"Erro ao ler preview: {str(e)}")
            
    except Exception as e:
        st.error(f"Erro ao salvar arquivo: {str(e)}")
        st.exception(e)
else:
    st.info("👆 Selecione a modalidade, ano e mês, depois faça upload do arquivo Excel.")

