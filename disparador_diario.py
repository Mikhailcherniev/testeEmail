# Arquivo: back/disparador_diario.py

import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
from pathlib import Path

# Importa o módulo de análise que está na mesma pasta ('back')
import analista_climatico as clima

def main():
    print(f"--- Iniciando disparos de e-mails em {datetime.now()} ---")
    
    # --- 1. Conectar ao Firebase ---
    try:
        credentials_path = Path(__file__).parent / 'firebase-credentials.json'
        cred = credentials.Certificate(credentials_path)
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("Conexão com Firebase OK.")
    except Exception as e:
        print(f"Falha fatal ao conectar ao Firebase: {e}")
        return

    # --- 2. Conectar ao Google Earth Engine ---
    clima.inicializar_gee()

    # --- 3. Buscar todos os assinantes no Firestore ---
    try:
        assinantes_ref = db.collection('assinantes')
        lista_assinantes = assinantes_ref.stream()
        print("Buscando lista de assinantes...")
    except Exception as e:
        print(f"Não foi possível buscar os assinantes: {e}")
        return

    # --- 4. Loop para processar cada assinante ---
    for assinante in lista_assinantes:
        dados_usuario = assinante.to_dict()
        email = dados_usuario.get('email')
        cidade = dados_usuario.get('cidade')
        
        if not all([email, cidade]):
            print(f"AVISO: Registro incompleto para o documento {assinante.id}. Pulando.")
            continue
            
        print(f"\n--- Processando para: {email} | Local: {cidade} ---")
        
        # Etapa A: Obter coordenadas da cidade com o Gemini
        lat, lon = clima.obter_coordenadas_com_gemini(cidade)
        if lat is None or lon is None:
            print(f"Não foi possível obter coordenadas para '{cidade}'. Pulando.")
            continue

        # Etapa B: Obter dados de satélite do Earth Engine
        dados_climaticos_gee = clima.obter_dados_gee(lat, lon, cidade)
        
        # Etapa C: Buscar previsão do tempo na internet
        previsoes_da_web = clima.buscar_previsao_tempo_online(cidade)
        
        # Etapa D: Gerar o boletim integrado com todas as informações
        nome_destinatario = email.split('@')[0]
        conteudo_email = clima.gerar_boletim_integrado_com_gemini(
            dados_gee=dados_climaticos_gee,
            previsoes_online=previsoes_da_web,
            nome_local=cidade,
            nome_destinatario=nome_destinatario,
            seu_nome="Seu Analista Climático" # Personalize aqui
        )
        
        if not conteudo_email:
            print("Não foi possível gerar o conteúdo do e-mail com o Gemini. Pulando.")
            continue

        # Etapa E: Enviar o e-mail
        try:
            partes = conteudo_email.split('\n', 1)
            assunto = partes[0].replace("Assunto: ", "").strip()
            corpo = partes[1].strip()
            clima.enviar_email_smtp(email, assunto, corpo)
        except Exception as e:
            print(f"Falha ao processar e enviar o e-mail para {email}. Erro: {e}")
            
    print("\n--- Processo de disparos finalizado. ---")

if __name__ == '__main__':
    main()