import streamlit as st  
import pandas as pd
import plotly.express as px
st.set_page_config(page_title='Home', layout='wide')

col1, col2 = st.columns(2)

if "pilates" in st.session_state:
    df_pilates = st.session_state["pilates"]
    planos = df_pilates.pivot_table(index='Contratos', values='VALOR_MENSAL', aggfunc='sum')
    planos_grafico = planos.reset_index().copy()
    planos.loc[:,"VALOR_MENSAL"] = planos["VALOR_MENSAL"].apply(lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    col1.markdown("### Planos de Pilates")
    col1.dataframe(planos ,height=300)

    fig = px.pie(planos_grafico, names='Contratos', values= 'VALOR_MENSAL',title='Planos de Pilates')
    col2.plotly_chart(fig ,use_container_width=True, height=300)
else:
    col2.warning("pilates não foi carregado na sessão")            
st.divider()
col1, col2 = st.columns(2)
if "judo" in st.session_state:
    df_judo = st.session_state["judo"]
    
    planos = df_judo.pivot_table(index='Contratos', values='VALOR_MENSAL', aggfunc='sum')
    planos_grafico = planos.reset_index().copy()
    planos.loc[:,"VALOR_MENSAL"] = planos["VALOR_MENSAL"].apply(lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    col1.markdown("### Planos de Judo")
    col1.dataframe(planos)
    fig = px.pie(planos_grafico, names='Contratos', values= 'VALOR_MENSAL',title='Planos de Judo')
    col2.plotly_chart(fig, use_container_width=True)
else:
    col2.warning("judo não foi carregado na sessão") 

st.divider()

col1, col2 = st.columns(2)
if "prime" in st.session_state:
    df_prime = st.session_state["prime"]
    planos = df_prime.pivot_table(index='Contratos', values='VALOR_MENSAL', aggfunc='sum')
    planos_grafico = planos.reset_index().copy()
    planos.loc[:,"VALOR_MENSAL"] = planos["VALOR_MENSAL"].apply(lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    col1.markdown("### Planos de Prime")
    col1.dataframe(planos)
    fig = px.pie(planos_grafico, names='Contratos', values= 'VALOR_MENSAL',title='Planos de Prime')
    col2.plotly_chart(fig, use_container_width=True)
else:
    col1.warning("Prime não foi carregado na sessão")       
st.divider()

col1, col2 = st.columns(2)
if "muay" in st.session_state:
    df_muay = st.session_state["muay"]
    planos = df_muay.pivot_table(index='Contratos', values='VALOR_MENSAL', aggfunc='sum')
    planos_grafico = planos.reset_index().copy()
    planos.loc[:,"VALOR_MENSAL"] = planos["VALOR_MENSAL"].apply(lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    col1.markdown("### Planos de Muai Thay")
    col1.dataframe(planos)
    fig = px.pie(planos_grafico, names='Contratos', values= 'VALOR_MENSAL',title='Planos de Muai Thay')
    col2.plotly_chart(fig, use_container_width=True)
else:
    st.warning("MuayThay não foi carregado na sessão")    
st.divider()
col1, col2 = st.columns(2)
if "kravmaga" in st.session_state:
    df_kravmaga = st.session_state["kravmaga"]
    planos = df_kravmaga.pivot_table(index='Contratos', values='VALOR_MENSAL', aggfunc='sum')
    planos_grafico = planos.reset_index().copy()
    planos.loc[:,"VALOR_MENSAL"] = planos["VALOR_MENSAL"].apply(lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    col1.markdown("### Planos de Kravmaga")
    col1.dataframe(planos)
    fig = px.pie(planos_grafico, names='Contratos', values= 'VALOR_MENSAL',title='Planos de Kravmaga')
    col2.plotly_chart(fig, use_container_width=True)
else:
    st.warning("KravMaga não foi carregado na sessão")

     

           