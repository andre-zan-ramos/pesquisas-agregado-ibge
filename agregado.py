import pandas as pd
import streamlit as st
import requests

url_base = "https://servicodados.ibge.gov.br/api/v3/agregados"

def init():
	dfs = {
		"variaveis" : pd.DataFrame(columns=["id","nome","label"]),
		"localidades" : pd.DataFrame(columns=["id","nome","label"])
	}
	
	urls = {"agregados":""}
	
	response_meta_agregado = {
		"id": "","nome": "","URL":"","pesquisa": "","assunto": "",
		"periodicidade": {"frequencia": "","inicio": "","fim": ""},
		"nivelTerritorial": {"Administrativo": [],"Especial": [],"IBGE": []},
		"variaveis": [{"id": "", "nome": "","unidade": ""}]
	}
	
	options = {"variaveis":"","localidades":"",'btn_buscar': False}

	return dfs, urls, response_meta_agregado,options

@st.cache_data(show_spinner="Carregando dados dos municípios no cache...")
def busca_municipios():
	cols = ["municipio-id","municipio-nome","UF-id","UF-sigla","UF-nome"]
	response = requests.get("https://servicodados.ibge.gov.br/api/v1/localidades/municipios?view=nivelado")
	response_json = response.json()
	df_response = pd.DataFrame(response_json)[cols]
	
	ufs_list = df_response[["UF-id","UF-sigla"]].drop_duplicates().sort_values("UF-sigla").reset_index(drop=True)

	df_response["municipio-uf"] = df_response["municipio-nome"] + " (" + df_response["UF-sigla"] + ")"

	df_municipios = df_response[["municipio-id","municipio-uf","UF-sigla"]]
	df_municipios = df_municipios.iloc[df_municipios["municipio-uf"].str.normalize('NFKD').argsort()].reset_index(drop=True)
	df_municipios["municipio-id"] = df_municipios["municipio-id"].astype(str)
		
	return df_municipios

@st.cache_data(show_spinner=False)
def buscar_agregado(id_agregado):
	url = (f"{url_base}/{id_agregado}/metadados")
	response_meta_agregado = requests.get(url).json()
	return response_meta_agregado, url

@st.cache_data(show_spinner=False)
def buscar_variaveis(response_meta_agregado):
	df = pd.DataFrame(response_meta_agregado["variaveis"])[["id","nome","unidade"]]
	df["label"] = df["id"].astype("string") + " - " + df["nome"]
	return df

@st.cache_data(show_spinner=False)
def buscar_localidades_nivel_agregado(id_agregado,id_nivel):
	url = (f"{url_base}/{id_agregado}/localidades/{id_nivel}")
	response_localidades = requests.get(url).json()
	st.write(url)
	st.write(response_localidades)
	df_localidades = pd.DataFrame(response_localidades)[["id","nome"]]
	
	if id_nivel == "N6":
		df_municipios = busca_municipios()
		df_localidades = pd.merge(df_localidades,df_municipios,left_on="id",right_on="municipio-id")[["id","municipio-uf"]].rename(columns={"municipio-uf":"nome"})
		df_localidades = df_localidades.iloc[df_localidades["nome"].str.normalize('NFKD').argsort()].reset_index(drop=True)
	
	df_localidades["label"] = df_localidades["id"].astype("string") + " - " + df_localidades["nome"]
	
	return df_localidades
	
def carregar(id_agregado,id_nivel,df_acervo_indicadores_nivel):
	dfs,urls,response_meta_agregado,options = init()
	
	if st.session_state["layout_carregado"] and id_agregado:		
		response_meta_agregado, urls["agregados"] = buscar_agregado(id_agregado)
		dfs["variaveis"] = buscar_variaveis(response_meta_agregado)
		dfs["localidades"] = buscar_localidades_nivel_agregado(id_agregado,id_nivel)
	
	c = st.container(border=True)
		
	c.subheader("Dados do agregado")
	
	#Ver detalhes do agregado
	e = c.expander("Ver detalhes do agregado")
	nome = ""
	
	if response_meta_agregado["nome"]:
		nome = (f'{response_meta_agregado["nome"]} (*Fonte:* {urls["agregados"]}) ')
	
	e.info(f'**Nome:** {nome}')	
	
	col1,col2,col3 = e.columns(3)
	
	col1.info(f'**Pesquisa:** \n {response_meta_agregado["pesquisa"]}')
	col1.info(f'**Assunto:** \n {response_meta_agregado["assunto"]}')
	
	col2.info(f'**URL:** \n {response_meta_agregado["URL"]}')
	col2.info(f'**Periodicidade:** \n {response_meta_agregado["periodicidade"]["frequencia"]}')
	
	col3.info(f'**Início:** \n {response_meta_agregado["periodicidade"]["inicio"]}')
	col3.info(f'**Fim:** \n {response_meta_agregado["periodicidade"]["fim"]}')
	
	nivelTerritorial = df_acervo_indicadores_nivel[df_acervo_indicadores_nivel["id"].isin(response_meta_agregado["nivelTerritorial"]["Administrativo"])]["label"].values
	e.info(f'**Nível territorial:** {", ".join(nivelTerritorial)}')
		
	
	#Lista de variáveis e localidades
	col1,col2 = c.columns(2)
	
	df = dfs["variaveis"]
	options_variaveis = col1.multiselect(
		"Lista de Variáveis:",
		options=df.label,	
		placeholder="Escolha uma ou mais variáveis",
		default=None,
		max_selections=6
	)
	if options_variaveis:
		aux = df.loc[df["label"].isin(options_variaveis),"id"]
		options["variaveis"] = ("|".join(str(x) for x in aux))
		
	
	df = dfs["localidades"]
	options_localidades = col2.multiselect(
		"Lista de Localidades:",
		options=df.label,	
		placeholder="Escolha uma ou mais localidades",
		default=None,
		max_selections=5
	)
	if options_localidades:
		aux = df.loc[df["label"].isin(options_localidades),"id"]
		options["localidades"] = (",".join(str(x) for x in aux))
	
	#Botão de busca - para evitar que toda hora fique atualizando quando selecionar mais de uma localidade
	a,col,b = c.columns([4,1,4])
	options["btn_buscar"] = col.button("Buscar")
	
	return options, dfs["localidades"]