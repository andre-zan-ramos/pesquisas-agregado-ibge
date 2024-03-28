import pandas as pd
import streamlit as st
import requests
import altair as alt

url_base = "https://servicodados.ibge.gov.br/api/v3/agregados"

@st.cache_data(show_spinner="Buscando resultados...")
def buscar_resultados(id_agregado,id_nivel,options):
	url = (f'{url_base}/{id_agregado}/periodos/{options["periodos"]}/variaveis/{options["variaveis"]}?localidades={id_nivel}[{options["localidades"]}]')
	response = requests.get(url).json()
	return response,url

def desenha_grafico(resposta,df,df_localidades):
	data_long = pd.melt(df, id_vars=['ano'], value_vars=df_localidades["nome"], var_name='Localidade', value_name='dado')
	
	grafico = alt.Chart(data_long).encode(
			x=alt.X("ano").title(""),
			y=alt.Y("dado").title(f'{resposta["unidade"]}'),
			tooltip=["ano","Localidade","dado"],
			color="Localidade:N"
		).mark_line(
			point=alt.OverlayMarkDef(size=100,filled=False,fill="white")
		).properties(
			title=(f'{resposta["id"]} - {resposta["variavel"]}')
		)
	
	return grafico
	
def carregar(id_agregado,id_nivel,options,df_localidades):
	options["periodos"] = "all"
	c = st.container(border=True)	
	c.subheader("Resultados")	
	if options["variaveis"] and options["localidades"] and options["btn_buscar"]:
		respostas,url_resultado = buscar_resultados(id_agregado,id_nivel,options)
		
		row1 = c.columns(2)
		row2 = c.columns(2)
		row3 = c.columns(2)
		
		k = 0
		for col in row1 + row2 + row3:
			ct = col.container(border=True)
			resposta = respostas[k]
			
			df = pd.DataFrame(columns=["ano"])
			
			for res in resposta["resultados"][0]["series"]:
				local = res["localidade"]["nome"]
				df_aux = pd.DataFrame.from_dict(res["serie"],orient='index').reset_index().rename(columns={"index":"ano",0:local})
				df_aux[local] = df_aux[local].astype(float)
				
				df = pd.merge(df,df_aux,on="ano",how="outer")
			
			#Desenhando o gráfico			
			grafico = desenha_grafico(resposta,df,df_localidades.loc[df_localidades['id'].isin(options["localidades"].split(','))].reset_index(drop=True))			
			ct.altair_chart(grafico, use_container_width=True)
			
			#Criando a tabela de resumos
			df_resumo = df.describe().transpose()[["mean","std","min","max"]].reset_index()				
			df_resumo["CV (%)"] = df_resumo["std"] * 100 / df_resumo["mean"]				
			df_resumo = df_resumo.round(2)
			
			df_resumo["Ano Mínimo"] = df.loc[df[df_resumo["index"]].idxmin(),"ano"].reset_index(drop=True)
			df_resumo["Ano Máximo"] = df.loc[df[df_resumo["index"]].idxmax(),"ano"].reset_index(drop=True)
			
			df_resumo.rename(columns={"index":"Localidade","mean":"Média","std":"Desvio","min":"Mínimo","max":"Máximo"},inplace=True)

			df_resumo = df_resumo[["Localidade","Média","Desvio","CV (%)","Mínimo","Ano Mínimo","Máximo","Ano Máximo"]]				
			
			#Exibindo resumo dos indicadores
			ct.dataframe(df_resumo.style.format(thousands=".",decimal=",",precision=2),hide_index=True,use_container_width=True)									
			e = ct.expander(f'Dados das localidades sobre **{resposta["variavel"]}**')
			e.dataframe(df)
			
			k += 1
			if k >= len(respostas):
				break
		
		c.caption(f'*Fonte:* {url_resultado}')	
		
	else:
		c.write("Não há resultados a exibir:")
		if not options["variaveis"]:
			c.write("- Escolha uma ou mais variáveis")
		if not options["localidades"]:
			c.write("- Escolha uma ou mais localidades")
		if not options["btn_buscar"]:
			c.write("- Clicar no botão buscar")
		
		options["btn_buscar"] = False