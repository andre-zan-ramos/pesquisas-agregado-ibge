import pandas as pd
import streamlit as st

def main():
	st.session_state["acervo_indicadores_assunto"] = pd.DataFrame(columns=["id","literal","tipo","label"])
	st.session_state["acervo_indicadores_nivel"] = pd.DataFrame([["N6","","Nível geográfico","N6 - Município"]],columns=["id","literal","tipo","label"])
	
	st.session_state["indicadores"] = ('nivel=N6')
	
	st.session_state["pesquisas"] = pd.DataFrame(columns=["id","nome","label"])
	st.session_state["agregados"] = pd.DataFrame(columns=["id","nome","label"])
	
	st.session_state["variaveis"] = pd.DataFrame(columns=["id","nome","label"])
	st.session_state["localidades"] = pd.DataFrame(columns=["id","nome","label"])
	
	st.session_state["url_acervo_indicadores_assunto"] = ""
	st.session_state["url_acervo_indicadores_nivel"] = ""
	st.session_state["url_pesquisas"] = ""
	st.session_state["url_agregados"] = "Escolha um agregado"
	
	if "rerun_main" not in st.session_state:
		st.session_state["rerun_main"] = False
	
	if "rerun_agregados" not in st.session_state:
		st.session_state["rerun_agregados"] = False
	
	if "rerun_resposta" not in st.session_state:
		st.session_state["rerun_resposta"] = False
		
	st.session_state["response_meta_agregado"] = {
		"id": "",
		"nome": "",
		"URL":"",
		"pesquisa": "",
		"assunto": "",
		"periodicidade": {
			"frequencia": "",
			"inicio": "",
			"fim": ""
		},
		"nivelTerritorial": {
			"Administrativo": [
			  "N1",
			  "N2",
			  "N6",
			  "N3"
			],
			"Especial": [
			  
			],
			"IBGE": [
			  
			]
		},
		"variaveis": [
			{
			  "id": "",
			  "nome": "",
			  "unidade": "",
			}
		]
	}
		
	