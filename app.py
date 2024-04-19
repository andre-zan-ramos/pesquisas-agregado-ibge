import streamlit as st
import parametros as pa
import pesquisas as pe
import agregado as ag
import resposta as rp

st.set_page_config(
    page_title="Pesquisas IBGE",
    page_icon=":chart_with_upwards_trend:",
	layout="wide"
)

if "layout_carregado" not in st.session_state:
	st.session_state["layout_carregado"] = False

a,b,c = st.columns([1,4,1])
b.title(":chart_with_upwards_trend: Pesquisas por agregados do IBGE :chart_with_downwards_trend:")
st.text("")

parametros, id_nivel, df_acervo_indicadores_nivel = pa.carregar()

id_agregado = pe.carregar(parametros)

options,df_localidades = ag.carregar(id_agregado,id_nivel,df_acervo_indicadores_nivel)

rp.carregar(id_agregado,id_nivel,options,df_localidades)

st.write(f'Parâmetros: {parametros}')

lixo = '''
st.write(f'Parâmetros: {parametros}')
st.write(f'id_agregado: {id_agregado}')
st.write(f'options: {options}')
'''

if st.session_state["layout_carregado"] == False:
	st.session_state["layout_carregado"] = True
	st.rerun()

