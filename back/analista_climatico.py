import ee
import google.generativeai as genai
import smtplib
import ssl
# Adicionamos a biblioteca geocoder para detecção de localização
import geocoder
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

# 3. Detalhes do E-mail
EMAIL_DESTINATARIO = "henriquemicael94@gmail.com"
NOME_DESTINATARIO = "ronaldo"
SEU_NOME = "rolaino primeiro jr"

# A localização agora será detectada automaticamente.
# --------------------------------------------------------

def obter_localizacao_atual():
    """
    Tenta obter a localização atual com base no IP.
    Retorna uma localização padrão (São Paulo, SP) em caso de falha.
    """
    try:
        print("Detectando localização atual com base no IP...")
        g = geocoder.ip('me')
        if g.ok and g.latlng:
            lat, lon = g.latlng
            cidade = g.city if g.city else "Cidade Desconhecida"
            estado = g.state if g.state else "Estado Desconhecido"
            nome_local = f"{cidade}, {estado}"
            print(f"Localização detectada: {nome_local}")
            return lat, lon, nome_local
        else:
            raise ValueError("Resposta do geocoder não foi válida.")
    except Exception as e:
        print(f"Não foi possível obter a localização automaticamente: {e}.")
        print("Usando localização padrão: São Paulo, SP.")
        return -23.5505, -46.6333, "São Paulo, SP"


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
    except Exception as e:
        print("Autenticação com o Google Earth Engine necessária.")
        print("Siga as instruções que aparecerão no terminal ou no seu navegador.")
        ee.Authenticate()
        ee.Initialize(project=ID_DO_PROJETO_GCP)
        print("Conexão com o Google Earth Engine estabelecida após autenticação.")


def obter_dados_gee(latitude, longitude, nome_local):
    """
    Busca dados de qualidade do ar (NO2) e precipitação (chuva) no Google Earth Engine.
    Calcula tanto o valor mais recente quanto a média da última semana.
    """
    ponto_de_interesse = ee.Geometry.Point(longitude, latitude)
    data_final = datetime.now()
    data_inicial = data_final - timedelta(days=7)

    dados_climaticos = {
        'concentracao_no2_recente': 'N/A',
        'precipitacao_mm_recente': 'N/A',
        'media_semanal_no2': 'N/A',
        'media_semanal_precipitacao': 'N/A'
    }

    try:
        # --- Qualidade do Ar (NO2 do Satélite Sentinel-5P) ---
        colecao_no2 = ee.ImageCollection('COPERNICUS/S5P/NRTI/L3_NO2') \
            .filterBounds(ponto_de_interesse) \
            .filterDate(data_inicial.strftime('%Y-%m-%d'), data_final.strftime('%Y-%m-%d')) \
            .select('NO2_column_number_density')

        if colecao_no2.size().getInfo() > 0:
            # Dado mais recente
            imagem_no2_recente = colecao_no2.sort('system:time_start', False).first()
            concentracao_no2_recente = imagem_no2_recente.reduceRegion(reducer=ee.Reducer.mean(), geometry=ponto_de_interesse, scale=1000).get('NO2_column_number_density').getInfo()
            if concentracao_no2_recente is not None:
                dados_climaticos['concentracao_no2_recente'] = f"{concentracao_no2_recente:.6f}"

            # Média da semana
            media_no2 = colecao_no2.mean()
            media_semanal_no2 = media_no2.reduceRegion(reducer=ee.Reducer.mean(), geometry=ponto_de_interesse, scale=1000).get('NO2_column_number_density').getInfo()
            if media_semanal_no2 is not None:
                dados_climaticos['media_semanal_no2'] = f"{media_semanal_no2:.6f}"
        else:
            print(f"Aviso: Nenhuma imagem de qualidade do ar (NO2) encontrada para {nome_local} nos últimos 7 dias.")

        # --- Precipitação (Chuva) do Dataset CHIRPS Daily ---
        colecao_chuva = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY') \
            .filterBounds(ponto_de_interesse) \
            .filterDate(data_inicial.strftime('%Y-%m-%d'), data_final.strftime('%Y-%m-%d')) \
            .select('precipitation')

        if colecao_chuva.size().getInfo() > 0:
            # Dado mais recente
            imagem_chuva_recente = colecao_chuva.sort('system:time_start', False).first()
            precipitacao_mm_recente = imagem_chuva_recente.reduceRegion(reducer=ee.Reducer.mean(), geometry=ponto_de_interesse, scale=5000).get('precipitation').getInfo()
            if precipitacao_mm_recente is not None:
                dados_climaticos['precipitacao_mm_recente'] = round(precipitacao_mm_recente, 2)
            
            # Média da semana (soma total de chuva na semana)
            soma_chuva = colecao_chuva.sum()
            soma_semanal_chuva = soma_chuva.reduceRegion(reducer=ee.Reducer.mean(), geometry=ponto_de_interesse, scale=5000).get('precipitation').getInfo()
            if soma_semanal_chuva is not None:
                dados_climaticos['media_semanal_precipitacao'] = round(soma_semanal_chuva, 2)
        else:
            print(f"Aviso: Nenhuma imagem de precipitação encontrada para {nome_local} nos últimos 7 dias.")

    except ee.EEException as e:
        print(f"Erro ao buscar dados no Earth Engine. Verifique a autenticação e as coleções. Erro: {e}")
        return None
    except Exception as e:
        print(f"Ocorreu um erro inesperado ao processar dados do GEE: {e}")
        return None
        
    return dados_climaticos


def gerar_email_com_gemini(dados, nome_local, nome_destinatario, seu_nome):
    """
    Usa a API do Gemini para gerar um e-mail formal a partir dos dados climáticos.
    """
    if not dados:
        print("Não há dados para gerar o e-mail.")
        return None
    
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash-latest')

    prompt = f"""
    Você é um analista ambiental sênior redigindo um comunicado formal e diário.
    Sua tarefa é escrever um e-mail para {nome_destinatario} com base nos seguintes dados de satélite para a região de {nome_local}.
    Seja claro, objetivo e use uma linguagem profissional. Explique os dados em termos simples e forneça recomendações práticas.

    Dados Coletados Hoje (mais recentes):
    - Concentração de Dióxido de Nitrogênio (NO2): {dados.get('concentracao_no2_recente', 'N/A')} mol/m². (Indicador de poluição).
    - Precipitação nas últimas 24 horas: {dados.get('precipitacao_mm_recente', 'N/A')} mm.

    Dados da Média Semanal (últimos 7 dias):
    - Média de Concentração de NO2: {dados.get('media_semanal_no2', 'N/A')} mol/m².
    - Total de Precipitação na Semana: {dados.get('media_semanal_precipitacao', 'N/A')} mm.

    Estrutura do E-mail:
    1.  **Assunto:** Crie um assunto informativo, como "Boletim Ambiental Diário - {nome_local} - {datetime.now().strftime('%d/%m/%Y')}".
    2.  **Saudação:** Use uma saudação formal (Prezado(a) {nome_destinatario},).
    3.  **Análise da Qualidade do Ar (Hoje):**
        -   Analise o valor recente do NO2. Um valor abaixo de 0.0001 mol/m² é BOM. Acima disso, a qualidade é REGULAR a RUIM.
        -   Se a qualidade do ar estiver BOA, incentive atividades ao ar livre.
        -   Se estiver RUIM, recomende evitar exercícios intensos ao ar livre, especialmente para grupos sensíveis.
    4.  **Previsão de Chuva (Hoje):**
        -   Se o valor recente de precipitação for maior que 0 mm, indique que houve ou há chance de chuva.
        -   Recomende medidas apropriadas (guarda-chuva, cautela no trânsito).
        -   Se for 0 ou 'N/A', informe que não há previsão de chuva significativa.
    5.  **NOVO: Resumo da Semana:**
        -   Adicione um parágrafo final chamado "Resumo da Semana".
        -   Com base na média de NO2 e no total de chuva, comente brevemente se a semana foi, em geral, de ar mais limpo ou mais poluído, e se foi seca ou chuvosa.
    6.  **Conclusão e Assinatura:** Finalize cordialmente e assine com seu nome ({seu_nome}).

    O e-mail deve ser gerado completo, começando com "Assunto:".
    """
    
    try:
        print("Gerando texto com a API do Gemini...")
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

        # Extrai os valores da resposta
        partes_lat = texto_resposta.split(',')[0]
        partes_lon = texto_resposta.split(',')[1]

        lat = float(partes_lat.split(':')[1].strip())
        lon = float(partes_lon.split(':')[1].strip())

        print(f"Coordenadas encontradas: Lat={lat}, Lon={lon}")
        return lat, lon

    except Exception as e:
        print(f"Erro ao obter coordenadas com Gemini para '{nome_cidade}': {e}")
        return None, None


