from pathlib import Path
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
from . import analista_climatico as clima

# Importa as funções do seu script original
import back.analista_climatico as clima

def main():
    print(f"--- Iniciando disparos de e-mails em {datetime.now()} ---")
    
    # --- 1. Conectar ao Firebase ---
    try:
        # Constrói o caminho correto para o arquivo de credenciais
        credentials_path = Path(__file__).parent.parent / 'jsons' / 'firebase-credentials.json'
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
    from . import analista_climatico as clima

def main():
    print(f"--- Iniciando disparos de e-mails em {datetime.now()} ---")
    
    # --- 1. Conectar ao Firebase ---
    try:
        # Constrói o caminho correto para o arquivo de credenciais
        credentials_path = Path(__file__).parent.parent / 'jsons' / 'firebase-credentials.json'
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
        cidade = dados_usuario.get('cidade') # <-- Pega a cidade do Firebase
        
        if not all([email, cidade]):
            print(f"AVISO: Registro incompleto para o documento {assinante.id}. Pulando.")
            continue
            
        print(f"\n--- Processando para: {email} | Local: {cidade} ---")
        
        # Etapa A: Obter coordenadas da cidade com o Gemini
        lat, lon = clima.obter_coordenadas_com_gemini(cidade)

        if lat is None or lon is None:
            print(f"Não foi possível obter coordenadas para '{cidade}'. Pulando e-mail.")
            continue

        # Etapa B: Obter dados climáticos para as coordenadas encontradas
        dados_climaticos = clima.obter_dados_gee(lat, lon, cidade)
        
        if not dados_climaticos:
            print(f"Não foi possível obter dados climáticos para {cidade}. Pulando e-mail.")
            continue
            
        print(f"Dados coletados: {dados_climaticos}")
        
        # Etapa C: Gerar e-mail com Gemini
        nome_destinatario = email.split('@')[0]
        # Preenchendo os argumentos corretamente
        conteudo_email = clima.gerar_email_com_gemini(
            dados=dados_climaticos,
            nome_local=cidade,
            nome_destinatario=nome_destinatario,
            seu_nome="Seu Nome ou Nome da Empresa" # Personalize aqui
        )
        
        if not conteudo_email:
            print("Não foi possível gerar o conteúdo do e-mail com o Gemini. Pulando.")
            continue

        # Etapa D: Enviar o e-mail
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