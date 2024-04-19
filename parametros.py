import pandas as pd
import streamlit as st
import requests

url_base = "https://servicodados.ibge.gov.br/api/v3/agregados"

def init():
	dfs = {
		"acervo_indicadores_assunto":pd.DataFrame(columns=["id","literal","tipo","label"]),
		"acervo_indicadores_nivel":pd.DataFrame([["N6","","Nível geográfico","N6 - Município"]],columns=["id","literal","tipo","label"]),
		"acervo_indicadores_periodos":pd.DataFrame(columns=["id","literal","tipo","label"])
	}
	
	urls = {
		"acervo_indicadores_assunto":"",
		"acervo_indicadores_nivel":""}
	
	parametros = {"assunto":"","nivel":"N6"}

	return dfs, urls, parametros

@st.cache_data(show_spinner="Carregando dados do acervo de parâmetros no cache...")
def buscar(tipo):
	url = (f"{url_base}?acervo={tipo}")
	response = requests.get(url).json()
	df = pd.DataFrame(response, columns=["id","literal","tipo"])
	df["tipo"]=tipo
	if tipo == "P":
		df = df[df["id"]==df["literal"]].sort_values("literal",ascending=False)
		df["label"] = df["literal"]
	else:
		df["label"] = df["id"].astype("string") + " - " + df["literal"]
	
	return df, url
	
def carregar():
	dfs,urls,parametros = init()
	
	if st.session_state["layout_carregado"]:
		dfs["acervo_indicadores_assunto"],urls["acervo_indicadores_assunto"] = buscar("A")
		dfs["acervo_indicadores_nivel"],urls["acervo_indicadores_nivel"] = buscar("N")
		dfs["acervo_indicadores_periodos"],urls["acervo_indicadores_periodos"] = buscar("P")
	
	c = st.container(border=True)
	c.subheader("Lista de parâmetros de pesquisa")
	
	c1,c2,c3 = c.columns([2,2,1])
	
	df = dfs["acervo_indicadores_assunto"]
	options_assunto = c1.selectbox(
		"Assunto:",
		options=df.label,			
		index=None,
		placeholder="Escolha um assunto"
	)
	
	if options_assunto:
		parametros["assunto"] = df.loc[df["label"]==options_assunto,"id"].values[0]
	
	df = dfs["acervo_indicadores_nivel"]
	options_nivel = c2.selectbox(
		"Nível:",
		options=df.label,			
		index=int(df[df["id"]=="N6"].index.values[0]),
		placeholder="Escolha um nível"
	)
	
	if options_nivel:
		parametros["nivel"] = df.loc[df["label"]==options_nivel,"id"].values[0]
	
	df = dfs["acervo_indicadores_periodos"]
	options_ano = c3.selectbox(
		"Ano que contenha a pesquisa:",
		options=df.label,
		index=None,
		placeholder="Escolha um ano"
	)
	if options_ano:
		parametros["periodo"] = options_ano
	
	if urls["acervo_indicadores_assunto"] and urls["acervo_indicadores_nivel"] and urls["acervo_indicadores_periodos"]:
		e = c.expander("Dados sobre os parâmetros")
		e.markdown(f'**:blue[Parâmetro:]** Assunto  \n*Fonte:* {urls["acervo_indicadores_assunto"]}')
		e.markdown("<br>", unsafe_allow_html=True)
		e.markdown(f'**:blue[Parâmetro:]** Nível  \n*Fonte:* {urls["acervo_indicadores_nivel"]}')
		e.markdown("<br>", unsafe_allow_html=True)
		e.markdown(f'**:blue[Parâmetro:]** Períodos (*filtrados apenas os anos*)  \n*Fonte:* {urls["acervo_indicadores_periodos"]}')
	
	parametros_string = '&'.join([f'{key}={value}' for key, value in parametros.items() if value!=""])
	
	return parametros_string,parametros["nivel"],dfs["acervo_indicadores_nivel"]