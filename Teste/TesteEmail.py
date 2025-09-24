import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- INFORMAÇÕES DE LOGIN (PREENCHA AQUI) ---
seu_email = "marcos.lacerda374@gmail.com"  # O e-mail que vai enviar a mensagem
senha_de_app = "khkg cmlk pqkf fnst"  # A senha de 16 letras que você gerou
# ---------------------------------------------

# --- INFORMAÇÕES DO E-MAIL A SER ENVIADO ---
email_destinatario = "henriquemicael94@gmail.com"
assunto = "Teste de E-mail com Senha de App"
corpo = """
Olá,

Este é um e-mail enviado usando o protocolo SMTP
e uma Senha de App do Google diretamente no código Python.

Atenciosamente,
gay.
"""
# ---------------------------------------------

# --- CONSTRUÇÃO DO E-MAIL ---
# Cria o objeto da mensagem
mensagem = MIMEMultipart()
mensagem["From"] = seu_email
mensagem["To"] = email_destinatario
mensagem["Subject"] = assunto

# Adiciona o corpo do e-mail como texto puro (plain text)
mensagem.attach(MIMEText(corpo, "plain"))
# ---------------------------------------------


# --- PROCESSO DE ENVIO ---
try:
    # Cria um contexto SSL seguro
    context = ssl.create_default_context()

    # Conecta-se ao servidor SMTP do Gmail na porta 587 (para TLS)
    # Usamos with para garantir que a conexão seja fechada automaticamente
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        print("Conectando ao servidor SMTP do Gmail...")
        server.starttls(context=context)  # Inicia a criptografia TLS
        print("Conexão segura estabelecida (TLS).")
        
        print("Realizando login...")
        server.login(seu_email, senha_de_app) # Faz o login com seu e-mail e a senha de app
        print("Login bem-sucedido.")

        # Envia o e-mail
        texto_da_mensagem = mensagem.as_string()
        server.sendmail(seu_email, email_destinatario, texto_da_mensagem)
        print(f"E-mail enviado com sucesso para {email_destinatario}!")

except smtplib.SMTPAuthenticationError:
    print("Falha na autenticação. Verifique seu e-mail e a Senha de App.")
    print("Lembre-se: use a Senha de App de 16 letras, não a senha da sua conta.")
except Exception as e:
    print(f"Ocorreu um erro inesperado: {e}")