import socket
from network_utils import trimite_mesaj, primeste_mesaj

def ruleaza_client():
    # 1. Configurăm conexiunea către server
    HOST = '127.0.0.1'  # Ne conectăm la propriul PC
    PORT = 5000

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        print(f" [CLIENT] Încercăm conectarea la {HOST}:{PORT}...")
        client_socket.connect((HOST, PORT))
        print(" [CLIENT] Conectat cu succes la server!\n")
    except ConnectionRefusedError:
        print(" [CLIENT] Eroare: Serverul nu este pornit sau nu ascultă pe acest port.")
        return

    # 2. Așteptăm prima întrebare de la server
    pachet_primit = primeste_mesaj(client_socket)
    
    if pachet_primit and pachet_primit.get("tip") == "INTREBARE":
        date_intrebare = pachet_primit["date"]
        
        # 3. Afișăm întrebarea frumos în terminal
        print("="*40)
        print(f" ÎNTREBARE: {date_intrebare['text']}")
        print("-" * 40)
        for litera, varianta in date_intrebare["variante"].items():
            print(f"   {litera}) {varianta}")
        print("="*40)

        # 4. Cerem input de la jucător
        alegere = input("\n 👉 Alege varianta corectă (A, B sau C): ").strip().upper()

        # 5. Împachetăm răspunsul și îl trimitem la server
        pachet_raspuns = {
            "tip": "RASPUNS",
            "nume_jucator": "Player_1", # Hardcodat pentru acest test
            "id_intrebare": date_intrebare["id"],
            "alegere": alegere
        }
        
        trimite_mesaj(client_socket, pachet_raspuns)
        print(" [CLIENT] Răspunsul a fost trimis către server.")
    else:
        print(" [CLIENT] Nu am primit formatul corect de la server.")

    # 6. Închidem conexiunea
    client_socket.close()
    print(" [CLIENT] Sesiune încheiată.")

if __name__ == "__main__":
    ruleaza_client()