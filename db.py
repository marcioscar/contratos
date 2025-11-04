from bson import ObjectId
from dotenv import load_dotenv
import pandas as pd
from pymongo import MongoClient
import streamlit as st
import pymongo
from datetime import datetime
import os
import requests

filtro = {
    "data": {"$gte": datetime(2025, 1, 1)}  # Data maior ou igual a 1 de janeiro de 2025
}

filtro_despesas = {
    "data": {"$gte": datetime(2025, 1, 1)},  # Data maior ou igual a 1 de janeiro de 2025
    "$or": [
        {"pago": True},   # Registros onde pago é True
        {"pago": {"$exists": False}}  # Registros onde pago não existe
    ]
}
@st.cache_resource
def conexao():
    try:
        load_dotenv()
        uri = os.getenv("MONOGO_EASY_PAINEL")
        client = MongoClient(uri, server_api=pymongo.server_api.ServerApi(
        version="1", strict=True, deprecation_errors=True))
    except Exception as e:
        raise Exception(
            "Erro: ", e)
    db = client["quattor"]
    st.session_state.db = db
    return  db


def calcular_valor_mensal(plano, valor):
    """Calcula o valor mensal baseado no tipo de plano"""
    if pd.isna(plano) or pd.isna(valor):
        return valor
    plano_str = str(plano).upper()
    if "15 MESES" in plano_str:
        return valor / 15
    elif "ANUAL" in plano_str or "12 MESES" in plano_str:
        return valor / 12
    elif "SEMESTRAL" in plano_str:
        return valor / 6
    elif "TRIMESTRAL" in plano_str:
        return valor / 3
    else:
        return valor

def cadastrar_contrato(id_cliente, nome_completo, contratos, valor, inicio, vencimento, valor_mensal, professor, modalidade, mes_abrev, ano):
    """Cadastra um contrato no MongoDB"""
    db = conexao()
    contratos_collection = db["contratos"]
    
    # Tratar professor: garantir que seja None se vazio ou NaN
    professor_final = None
    if professor is not None:
        if isinstance(professor, str):
            professor_final = professor.strip() if professor.strip() else None
        elif not pd.isna(professor):
            professor_final = str(professor).strip() if str(professor).strip() else None
    
    contrato = {
        "id_cliente": str(id_cliente),
        "nome_completo": nome_completo,
        "contratos": contratos,
        "valor": float(valor) if not pd.isna(valor) else 0.0,
        "inicio": inicio,
        "vencimento": vencimento,
        "valor_mensal": float(valor_mensal) if not pd.isna(valor_mensal) else 0.0,
        "professor": professor_final,
        "modalidade": modalidade,
        "mes": mes_abrev,
        "ano": int(ano),
        "criado_em": datetime.now()
    }
    
    # Verificar se já existe contrato com mesmo id_cliente, modalidade, mês e ano
    filtro_existente = {
        "id_cliente": str(id_cliente),
        "modalidade": modalidade,
        "mes": mes_abrev,
        "ano": int(ano)
    }
    
    # Atualizar se existir, inserir se não existir
    contratos_collection.update_one(
        filtro_existente,
        {"$set": contrato},
        upsert=True
    )
    
    return contrato

def importar_planilha_para_mongodb(arquivo_path, modalidade, mes_abrev, ano):
    """Importa dados de uma planilha Excel para o MongoDB"""
    try:
        # Colunas padrão para todas as modalidades
        colunas_base = ['ID do cliente', 'Nome', 'Sobrenome', 'Contratos', 'Início', 'Vencimento', 'Valor']
        
        # Primeiro, ler apenas para verificar quais colunas existem
        df_temp = pd.read_excel(arquivo_path, nrows=0)
        colunas_disponiveis = df_temp.columns.tolist()
        
        # Adicionar Professor se existir na planilha
        colunas = colunas_base.copy()
        if 'Professor' in colunas_disponiveis:
            colunas.append('Professor')
        
        # Ler planilha com as colunas corretas
        df = pd.read_excel(arquivo_path, usecols=colunas)
        
        # Processar dados
        df['nome_completo'] = df['Nome'].fillna('') + ' ' + df['Sobrenome'].fillna('')
        df['nome_completo'] = df['nome_completo'].str.strip()
        
        # Converter datas para string
        if 'Início' in df.columns:
            df['Início'] = pd.to_datetime(df['Início'], errors='coerce').dt.strftime("%d/%m/%Y")
        if 'Vencimento' in df.columns:
            df['Vencimento'] = pd.to_datetime(df['Vencimento'], errors='coerce').dt.strftime("%d/%m/%Y")
        
        # Calcular valor mensal
        df['valor_mensal'] = df.apply(
            lambda row: calcular_valor_mensal(row.get('Contratos', ''), row.get('Valor', 0)), 
            axis=1
        )
        
        # Preparar professor (None se não existir ou se for NaN)
        professor_col = 'Professor' if 'Professor' in df.columns else None
        
        # Inserir no banco
        contratos_inseridos = 0
        for _, row in df.iterrows():
            id_cliente = row.get('ID do cliente', '')
            if pd.isna(id_cliente) or id_cliente == '':
                continue
            
            # Tratar professor: converter NaN para None
            professor_valor = None
            if professor_col and professor_col in df.columns:
                professor_valor = row.get(professor_col)
                if pd.isna(professor_valor) or professor_valor == '':
                    professor_valor = None
                else:
                    professor_valor = str(professor_valor).strip()
                    if professor_valor == '':
                        professor_valor = None
                
            cadastrar_contrato(
                id_cliente=str(id_cliente),
                nome_completo=row.get('nome_completo', ''),
                contratos=str(row.get('Contratos', '')),
                valor=row.get('Valor', 0),
                inicio=row.get('Início', ''),
                vencimento=row.get('Vencimento', ''),
                valor_mensal=row.get('valor_mensal', 0),
                professor=professor_valor,
                modalidade=modalidade,
                mes_abrev=mes_abrev,
                ano=ano
            )
            contratos_inseridos += 1
        
        return contratos_inseridos
    except Exception as e:
        raise Exception(f"Erro ao importar planilha: {str(e)}")

def buscar_contratos(modalidade, mes_abrev, ano, professor=None):
    """Busca contratos do MongoDB filtrados por modalidade, mês e ano"""
    db = conexao()
    contratos_collection = db["contratos"]
    
    filtro = {
        "modalidade": modalidade,
        "mes": mes_abrev,
        "ano": int(ano)
    }
    
    if professor is not None:
        filtro["professor"] = professor
    
    contratos = list(contratos_collection.find(filtro))
    
    if not contratos:
        return pd.DataFrame()
    
    # Converter para DataFrame
    df = pd.DataFrame(contratos)
    
    # Remover campos que não devem aparecer na exibição
    colunas_para_remover = ['_id', 'mes', 'ano', 'criado_em', 'modalidade', 'pago']
    df = df.drop(columns=[col for col in colunas_para_remover if col in df.columns])
    
    # Definir índice como ID do cliente
    if 'id_cliente' in df.columns:
        df = df.set_index('id_cliente')
    
    return df

def deletar_contratos_por_periodo(modalidade, mes_abrev, ano):
    """Deleta todos os contratos de um período específico"""
    db = conexao()
    contratos_collection = db["contratos"]
    
    filtro = {
        "modalidade": modalidade,
        "mes": mes_abrev,
        "ano": int(ano)
    }
    
    resultado = contratos_collection.delete_many(filtro)
    return resultado.deleted_count

def atualizar_contrato(id_cliente, modalidade, mes_abrev, ano, nome_completo=None, contratos=None, valor=None, inicio=None, vencimento=None, valor_mensal=None, professor=None):
    """Atualiza um contrato específico no MongoDB"""
    db = conexao()
    contratos_collection = db["contratos"]
    
    filtro = {
        "id_cliente": str(id_cliente),
        "modalidade": modalidade,
        "mes": mes_abrev,
        "ano": int(ano)
    }
    
    # Construir objeto de atualização apenas com campos fornecidos
    atualizacao = {}
    
    if nome_completo is not None:
        atualizacao["nome_completo"] = nome_completo
    if contratos is not None:
        atualizacao["contratos"] = str(contratos)
    if valor is not None:
        atualizacao["valor"] = float(valor) if not pd.isna(valor) else 0.0
    if inicio is not None:
        atualizacao["inicio"] = inicio
    if vencimento is not None:
        atualizacao["vencimento"] = vencimento
    if valor_mensal is not None:
        atualizacao["valor_mensal"] = float(valor_mensal) if not pd.isna(valor_mensal) else 0.0
    
    # Tratar professor
    if professor is not None:
        professor_final = None
        if isinstance(professor, str):
            professor_final = professor.strip() if professor.strip() else None
        elif not pd.isna(professor):
            professor_final = str(professor).strip() if str(professor).strip() else None
        atualizacao["professor"] = professor_final
    
    if not atualizacao:
        return False
    
    resultado = contratos_collection.update_one(filtro, {"$set": atualizacao})
    return resultado.modified_count > 0

def buscar_professores_unicos(modalidade):
    """Busca todos os professores únicos de uma modalidade"""
    db = conexao()
    contratos_collection = db["contratos"]
    
    filtro = {
        "modalidade": modalidade,
        "professor": {"$ne": None, "$exists": True}
    }
    
    # Buscar apenas o campo professor usando find (compatível com API Version 1)
    cursor = contratos_collection.find(filtro, {"professor": 1})
    
    # Extrair valores únicos manualmente
    professores = set()
    for doc in cursor:
        professor = doc.get("professor")
        if professor and str(professor).strip():
            professores.add(str(professor).strip())
    
    # Ordenar e retornar
    professores_validos = sorted(list(professores))
    
    return professores_validos

def buscar_planos_unicos(modalidade):
    """Busca todos os planos (contratos) únicos de uma modalidade"""
    db = conexao()
    contratos_collection = db["contratos"]
    
    filtro = {
        "modalidade": modalidade,
        "contratos": {"$ne": None, "$exists": True}
    }
    
    # Buscar apenas o campo contratos usando find (compatível com API Version 1)
    cursor = contratos_collection.find(filtro, {"contratos": 1})
    
    # Extrair valores únicos manualmente
    planos = set()
    for doc in cursor:
        contrato = doc.get("contratos")
        if contrato and str(contrato).strip():
            planos.add(str(contrato).strip())
    
    # Ordenar e retornar
    planos_validos = sorted(list(planos))
    
    return planos_validos

def buscar_dados_dashboard(ano=None):
    """Busca dados agregados de todas as modalidades para o dashboard
    
    Args:
        ano: Ano para filtrar (opcional). Se None, busca todos os anos.
    
    Returns:
        DataFrame com colunas: modalidade, mes, ano, total_valor_mensal, total_50_percent, num_registros
    """
    db = conexao()
    contratos_collection = db["contratos"]
    
    # Filtro por ano se fornecido
    filtro = {}
    if ano is not None:
        filtro["ano"] = int(ano)
    
    # Buscar todos os contratos
    cursor = contratos_collection.find(filtro)
    
    # Converter para DataFrame
    contratos_lista = list(cursor)
    
    if not contratos_lista:
        return pd.DataFrame()
    
    df = pd.DataFrame(contratos_lista)
    
    if df.empty:
        return pd.DataFrame()
    
    # Agrupar por modalidade, mês e ano
    # Calcular valor 50% (valor_mensal / 2)
    df['valor_50_percent'] = df['valor_mensal'] / 2
    
    # Agrupar e agregar
    df_agregado = df.groupby(['modalidade', 'mes', 'ano']).agg({
        'valor_mensal': 'sum',
        'valor_50_percent': 'sum',
        'id_cliente': 'count'
    }).reset_index()
    
    # Renomear colunas
    df_agregado.columns = ['modalidade', 'mes', 'ano', 'total_valor_mensal', 'total_50_percent', 'num_registros']
    
    return df_agregado

def df_desp():
    db = conexao()
    despesas = db["despesas"]
    data_desp = despesas.find(filtro_despesas)
    df_desp =  pd.DataFrame(list(data_desp)) 
    df_desp_agrupado = df_desp.groupby(['data'])['valor'].sum().reset_index()
    st.session_state.df_desp = df_desp_agrupado
    return df_desp_agrupado

    

def df_rec():
    db = conexao()
    receitas = db["receitas"]
    data_rec = receitas.find(filtro)
    df_rec =  pd.DataFrame(list(data_rec)) 
    df_rec_agrupado = df_rec.groupby(['data'])['valor'].sum().reset_index()
    st.session_state.df_rec = df_rec_agrupado   
    return df_rec_agrupado

def df_receitas():
    db = conexao()
    receitas = db["receitas"]
    data_rec = receitas.find()
    df_rec =  pd.DataFrame(list(data_rec)) 
    return df_rec

def cadastrar_funcionario(nome, funcao, modalidade,conta):
    db = conexao()
    folha = db["folha"]
    folha.insert_one({"nome": nome, "funcao": funcao, "modalidade": modalidade, "conta": conta})
    return folha

def edit_funcionario(id,nome, funcao, modalidade,conta):
    db = conexao()
    folha = db["folha"]
    filtro = {"_id": ObjectId(id)}
    folha.update_one(filtro, {"$set": {"nome": nome, "funcao": funcao, "modalidade": modalidade, "conta": conta}})
    return folha
    
def apagar_funcionario(id):
    db = conexao()
    folha = db["folha"]
    filtro = {"_id": ObjectId(id)}
    folha.delete_one(filtro)
    return folha

def cancelamentos():
    db = conexao()
    cancelamentos = db["cancelamentos"]
    return cancelamentos