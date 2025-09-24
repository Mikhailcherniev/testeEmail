import ee
import google.generativeai as genai
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

# --- CONFIGURAÇÃO (PREENCHA COM SUAS INFORMAÇÕES) ---
# ATENÇÃO: Nunca compartilhe este arquivo com suas chaves preenchidas.
# É recomendado usar variáveis de ambiente para mais segurança.

# 1. Chave de API do Gemini
# Obtenha em: https://aistudio.google.com/app/apikey
GEMINI_API_KEY = "AIzaSyDJDZOgBzmR3PEXsQFtR_EhM2ZzmeYWI7k"

# 2. Credenciais do Gmail para envio via SMTP
SEU_EMAIL_GMAIL = "suporteclima.teste@gmail.com"
# Crie uma senha de app em: https://myaccount.google.com/apppasswords
SENHA_DE_APP_GMAIL = "mxih lhil oazi itrh"

# --------------------------------------------------------

def inicializar_gee():
    """
    Tenta inicializar o Earth Engine. Se não autenticado, pede autenticação.
    Passa explicitamente o ID do projeto do Google Cloud.
    """
    # --------------------------------------------------------------------------
    # IMPORTANTE: COLOQUE O ID DO SEU PROJETO DO GOOGLE CLOUD AQUI
    ID_DO_PROJETO_GCP = "testeapi-473103"
    # --------------------------------------------------------------------------

    try:
        ee.Initialize(project=ID_DO_PROJETO_GCP)
        print("Conexão com o Google Earth Engine estabelecida.")
    except Exception:
        print("Autenticação com o Google Earth Engine necessária.")
        print("Siga as instruções que aparecerão no terminal ou no seu navegador.")
        ee.Authenticate()
        ee.Initialize(project=ID_DO_PROJETO_GCP)
        print("Conexão com o Google Earth Engine estabelecida após autenticação.")


def obter_coordenadas_com_gemini(nome_cidade):
    """
    Usa a API do Gemini para obter a latitude e longitude de uma cidade.
    Retorna (latitude, longitude) ou (None, None) em caso de falha.
    """
    print(f"Usando Gemini para encontrar coordenadas de: {nome_cidade}")
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        prompt = f"""
        Qual a latitude e a longitude aproximadas do centro da cidade de "{nome_cidade}"?
        Responda APENAS no formato "lat: VALOR, lon: VALOR".
        Por exemplo: "lat: -23.5505, lon: -46.6333"
        """
        response = model.generate_content(prompt)
        texto_resposta = response.text.strip()
        partes_lat = texto_resposta.split(',')[0]
        partes_lon = texto_resposta.split(',')[1]
        lat = float(partes_lat.split(':')[1].strip())
        lon = float(partes_lon.split(':')[1].strip())
        print(f"Coordenadas encontradas: Lat={lat}, Lon={lon}")
        return lat, lon
    except Exception as e:
        print(f"Erro ao obter coordenadas com Gemini para '{nome_cidade}': {e}")
        return None, None


def obter_dados_gee(latitude, longitude, nome_local):
    """
    Busca dados de qualidade do ar (NO2) e precipitação (chuva) no Google Earth Engine.
    """
    ponto_de_interesse = ee.Geometry.Point(longitude, latitude)
    data_final = datetime.now()
    data_inicial = data_final - timedelta(days=7)

    dados_climaticos = {
        'concentracao_no2_recente': 'N/A',
        'precipitacao_mm_recente': 'N/A',
        'media_semanal_no2': 'N/A',
        'total_semanal_precipitacao': 'N/A'
    }

    try:
        # Qualidade do Ar (NO2)
        colecao_no2 = ee.ImageCollection('COPERNICUS/S5P/NRTI/L3_NO2').filterBounds(ponto_de_interesse).filterDate(data_inicial.strftime('%Y-%m-%d'), data_final.strftime('%Y-%m-%d')).select('NO2_column_number_density')
        if colecao_no2.size().getInfo() > 0:
            imagem_no2_recente = colecao_no2.sort('system:time_start', False).first()
            concentracao_no2_recente = imagem_no2_recente.reduceRegion(reducer=ee.Reducer.mean(), geometry=ponto_de_interesse, scale=1000).get('NO2_column_number_density').getInfo()
            if concentracao_no2_recente is not None:
                dados_climaticos['concentracao_no2_recente'] = f"{concentracao_no2_recente:.6f}"
            
            media_semanal_no2 = colecao_no2.mean().reduceRegion(reducer=ee.Reducer.mean(), geometry=ponto_de_interesse, scale=1000).get('NO2_column_number_density').getInfo()
            if media_semanal_no2 is not None:
                dados_climaticos['media_semanal_no2'] = f"{media_semanal_no2:.6f}"
        else:
            print(f"Aviso: Nenhuma imagem de qualidade do ar (NO2) encontrada para {nome_local} nos últimos 7 dias.")

        # Precipitação (Chuva)
        colecao_chuva = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY').filterBounds(ponto_de_interesse).filterDate(data_inicial.strftime('%Y-%m-%d'), data_final.strftime('%Y-%m-%d')).select('precipitation')
        if colecao_chuva.size().getInfo() > 0:
            imagem_chuva_recente = colecao_chuva.sort('system:time_start', False).first()
            precipitacao_mm_recente = imagem_chuva_recente.reduceRegion(reducer=ee.Reducer.mean(), geometry=ponto_de_interesse, scale=5000).get('precipitation').getInfo()
            if precipitacao_mm_recente is not None:
                dados_climaticos['precipitacao_mm_recente'] = round(precipitacao_mm_recente, 2)
            
            soma_semanal_chuva = colecao_chuva.sum().reduceRegion(reducer=ee.Reducer.mean(), geometry=ponto_de_interesse, scale=5000).get('precipitation').getInfo()
            if soma_semanal_chuva is not None:
                dados_climaticos['total_semanal_precipitacao'] = round(soma_semanal_chuva, 2)
        else:
            print(f"Aviso: Nenhuma imagem de precipitação encontrada para {nome_local} nos últimos 7 dias.")
    except Exception as e:
        print(f"Ocorreu um erro inesperado ao processar dados do GEE: {e}")
        return None
    return dados_climaticos


# NOVA FUNÇÃO ADICIONADA
def buscar_previsao_tempo_online(nome_cidade):
    """
    Usa o Gemini para buscar a previsão do tempo online para uma cidade.
    """
    print(f"Buscando previsão do tempo online para: {nome_cidade}")
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        # Ativa a busca na internet com uma ferramenta
        tool = genai.protos.Tool(
            function_declarations=[
                genai.protos.FunctionDeclaration(
                    name='find_weather_forecast',
                    description=f'Find the weather forecast for {nome_cidade}.',
                    parameters=genai.protos.Schema(
                        type=genai.protos.Type.OBJECT,
                        properties={
                            'city': genai.protos.Schema(type=genai.protos.Type.STRING, description='The city name'),
                        }
                    )
                )
            ]
        )
        
        prompt = f'Qual é a previsão do tempo para hoje em {nome_cidade}? Inclua temperatura mínima, máxima, condição do tempo (ensolarado, nublado, etc) e chance de chuva.'
        
        response = model.generate_content(prompt)
        
        # Se a resposta for um texto direto, use-o.
        if response.text:
            return response.text.strip()
        return "Não foi possível obter a previsão do tempo online."

    except Exception as e:
        print(f"Erro ao buscar previsão do tempo online: {e}")
        return "Falha ao buscar previsão do tempo."


# FUNÇÃO AJUSTADA E RENOMEADA
def gerar_boletim_integrado_com_gemini(dados_gee, previsoes_online, nome_local, nome_destinatario, seu_nome):
    """
    Usa a API do Gemini para gerar um e-mail formal a partir dos dados de satélite E da previsão online.
    """
    if not dados_gee:
        print("Não há dados do GEE para gerar o e-mail.")
        return None
    
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash-latest')

    prompt = f"""
    Você é um analista ambiental sênior redigindo um comunicado formal e diário.
    Sua tarefa é escrever um e-mail para {nome_destinatario} combinando duas fontes de dados para a região de {nome_local}.
    Seja claro, objetivo e use uma linguagem profissional. Explique os dados em termos simples e forneça recomendações práticas.

    Fonte 1: Dados de Satélite (Visão macro da atmosfera)
    - Concentração de Dióxido de Nitrogênio (NO2) Hoje: {dados_gee.get('concentracao_no2_recente', 'N/A')} mol/m².
    - Média Semanal de NO2: {dados_gee.get('media_semanal_no2', 'N/A')} mol/m².
    - Precipitação (Chuva) nas últimas 24h: {dados_gee.get('precipitacao_mm_recente', 'N/A')} mm.
    - Total de Chuva na Semana: {dados_gee.get('total_semanal_precipitacao', 'N/A')} mm.

    Fonte 2: Previsão do Tempo Online (Condições locais)
    - Previsão para hoje: {previsoes_online}

    Estrutura do E-mail:
    1.  **Assunto:** Crie um assunto informativo, como "Boletim Climático e Ambiental - {nome_local} - {datetime.now().strftime('%d/%m/%Y')}".
    2.  **Saudação:** Use uma saudação formal (Prezado(a) {nome_destinatario},).
    3.  **Resumo do Dia:** Comece com um parágrafo curto resumindo a previsão do tempo online (Fonte 2).
    4.  **Análise da Qualidade do Ar (Satélite):**
        - Analise o valor recente do NO2. Um valor abaixo de 0.0001 mol/m² é BOM. Acima disso, a qualidade é REGULAR a RUIM.
        - Com base nisso, recomende ou desaconselhe atividades ao ar livre.
    5.  **Análise de Chuva (Satélite):**
        - Comente se os dados de satélite indicam chuva recente na região.
    6.  **Resumo da Semana (Satélite):**
        - Com base na média de NO2 e no total de chuva, comente se a semana foi, em geral, de ar mais limpo ou poluído, e se foi seca ou chuvosa.
    7.  **Conclusão e Assinatura:** Finalize cordialmente e assine com seu nome ({seu_nome}).

    O e-mail deve ser gerado completo, começando com "Assunto:".
    """
    
    try:
        print("Gerando boletim integrado com a API do Gemini...")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Erro ao chamar a API do Gemini: {e}")
        return None


def enviar_email_smtp(destinatario, assunto, corpo):
    """
    Envia o e-mail usando o servidor SMTP do Gmail.
    """
    if not all([destinatario, assunto, corpo]):
        print("Faltam informações para enviar o e-mail (destinatário, assunto ou corpo).")
        return

    mensagem = MIMEMultipart()
    mensagem["From"] = SEU_EMAIL_GMAIL
    mensagem["To"] = destinatario
    mensagem["Subject"] = assunto
    mensagem.attach(MIMEText(corpo, "plain", "utf-8"))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            print("Conectando ao servidor SMTP do Gmail...")
            server.starttls(context=context)
            print("Fazendo login...")
            server.login(SEU_EMAIL_GMAIL, SENHA_DE_APP_GMAIL)
            print("Enviando e-mail...")
            server.sendmail(SEU_EMAIL_GMAIL, destinatario, mensagem.as_string())
            print(f"E-mail enviado com sucesso para {destinatario}!")
    except smtplib.SMTPAuthenticationError:
        print("Falha na autenticação. Verifique seu e-mail e a Senha de App.")
    except Exception as e:
        print(f"Falha ao enviar o e-mail: {e}")