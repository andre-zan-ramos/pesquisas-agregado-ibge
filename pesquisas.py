import pandas as pd
import streamlit as st
import requests

url_base = "https://servicodados.ibge.gov.br/api/v3/agregados"

def init():
	dfs = {
		"pesquisas" : pd.DataFrame(columns=["id","nome","label"]),
		"agregados" : pd.DataFrame(columns=["id","nome","label"])
	}
	
	urls = {"pesquisas":"Selecione uma pesquisa para exibir o caminho"}
	
	ids = {"pesquisas":"","agregados":""}

	return dfs, urls, ids

@st.cache_data(show_spinner="Carregando dados das pesquisas no cache...")
def buscar_pesquisas(parametros):
	url = (f"{url_base}?{parametros}")
	response = requests.get(url).json()
	if response:
		df = pd.DataFrame(response)
		df["label"] = df["id"].astype("string") + " - " + df["nome"]
	else:
		df = pd.DataFrame(columns=["id","nome","label"])
	return df, url

@st.cache_data(show_spinner="Carregando dados dos agregados no cache...")
def buscar_agregado(id_agregado):
	url = (f"{url_base}/{id_agregado}/metadados")
	st.write(url)
	response_meta_agregado = requests.get(url).json()
	return response_meta_agregado, url
	
def carregar(parametros):
	dfs,urls,ids = init()
	
	if st.session_state["layout_carregado"]:
		dfs["pesquisas"],urls["pesquisas"] = buscar_pesquisas(parametros)
	
	c = st.container(border=True)
	c.subheader("Lista de pesquisas e agregados")
	
	c1,c2 = c.columns(2)
	
	df = dfs["pesquisas"]
	options_pesquisa = c1.selectbox(
		"Lista de Pesquisas:",
		options=df.label,			
		index=None,
		placeholder="Escolha uma pesquisa"
	)
	
	if options_pesquisa:
		ids["pesquisa"] = df.loc[df["label"]==options_pesquisa,"id"].values[0]
		aux = pd.DataFrame(df.loc[df["id"]==ids["pesquisa"],"agregados"].values[0])
		aux["label"] = aux["id"].astype("string") + " - " + aux["nome"]
		dfs["agregados"] = aux
		
	df = dfs["agregados"]
	options_agregado = c2.selectbox(
		"Lista de Agregados:",
		options=df.label,	
		index=None,
		placeholder="Escolha um agregado"
	)
	
	if options_agregado:
		ids["agregados"] = df.loc[df["label"]==options_agregado,"id"].values[0]
		
	e = c.expander("Dados sobre as pesquisas")
	e.markdown(f'**:blue[Parâmetro:]** Pesquisas  \n*Fonte:* {urls["pesquisas"]} \n\n**:blue[Lista de Agregados:]**')
	e.dataframe(dfs["agregados"]["label"],hide_index=True,use_container_width=True)
	
	return ids["agregados"]