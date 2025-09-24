from pathlib import Path
import tkinter as tk
from tkinter import messagebox
import geocoder
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
credentials_path = Path(__file__).parent / 'json' / 'firebase-credentials.json'
# --- CONFIGURAÇÃO DO FIREBASE ---
# Certifique-se de que o arquivo 'firebase-credentials.json' está na mesma pasta.
try:
    cred = credentials.Certificate(credentials_path)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("Conexão com o Firebase estabelecida com sucesso!")
except Exception as e:
    print(f"Erro ao conectar com o Firebase: {e}")
    db = None

def subscribe_user():
    """Função chamada quando o botão é pressionado."""
    email = entry_email.get().strip()
    # Mudamos o nome da variável para ser mais claro
    cidade = entry_address.get().strip() 

    if not email or not cidade:
        messagebox.showerror("Erro", "Por favor, preencha ambos os campos.")
        return

    if not db:
        messagebox.showerror("Erro de Sistema", "Não foi possível conectar ao banco de dados.")
        return
        
    status_label.config(text="Salvando inscrição...")
    window.update_idletasks()


    # 2. Salvar no Firebase
  # 2. Salvar no Firebase
    try:
        doc_ref = db.collection('assinantes').document(email)
        
        # Salvamos apenas o e-mail e a cidade!
        user_data = {
            'email': email,
            'cidade': cidade, # <-- MUDANÇA AQUI
            'data_inscricao': datetime.now()
        }
        
        doc_ref.set(user_data)
        
        messagebox.showinfo("Sucesso", f"Inscrição realizada com sucesso para {email}!\nVocê começará a receber os boletins diários.")
        entry_email.delete(0, tk.END)
        entry_address.delete(0, tk.END)
        status_label.config(text="")

    except Exception as e:
        messagebox.showerror("Erro de Sistema", f"Ocorreu um erro ao salvar os dados: {e}")
        status_label.config(text="")

# --- CRIAÇÃO DA INTERFACE GRÁFICA ---
window = tk.Tk()
window.title("Inscrição para Alertas Climáticos")
window.geometry("400x200")

frame = tk.Frame(window, padx=10, pady=10)
frame.pack(expand=True)

label_email = tk.Label(frame, text="Seu E-mail:")
label_email.pack(pady=5)
entry_email = tk.Entry(frame, width=50)
entry_email.pack()

label_address = tk.Label(frame, text="Sua cidade e estado (EX: cidade, estado):")
label_address.pack(pady=5)
entry_address = tk.Entry(frame, width=50)
entry_address.pack()

subscribe_button = tk.Button(frame, text="Inscrever-se", command=subscribe_user)
subscribe_button.pack(pady=15)

status_label = tk.Label(frame, text="")
status_label.pack()

window.mainloop()