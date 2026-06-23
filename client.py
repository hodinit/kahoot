import socket
import time
from network_utils import trimite_mesaj, primeste_mesaj

def conectare_la_lider():
    # Toate porturile expuse de Docker pe PC-ul nostru
    PORTURI_SERVERE = [5001, 5002, 5003]
    HOST = '127.0.0.1'
    
    nume_utilizator = input("Introdu numele tău de jucător: ").strip()

    for port in PORTURI_SERVERE:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            print(f"[CLIENT] Încercăm poarta {port}...")
            client_socket.connect((HOST, port))
            
            # Întrebăm serverul dacă ne primește
            pachet_cerere = {"tip": "CONECTARE_JUCATOR", "nume": nume_utilizator}
            trimite_mesaj(client_socket, pachet_cerere)
            
            # Citim răspunsul de validare
            raspuns = primeste_mesaj(client_socket)
            
            if raspuns and raspuns.get("tip") == "ACCES_PERMIS":
                print(f"[CLIENT] Succes! {raspuns.get('mesaj')} (Port {port})\n")
                return client_socket # Returnăm socket-ul deschis cu liderul
            else:
                print(f"[CLIENT] Serverul de pe portul {port} a zis: {raspuns.get('mesaj') if raspuns else 'Fără răspuns'}. Trecem la următorul...")
                client_socket.close()
                
        except ConnectionRefusedError:
            print(f"[CLIENT] Portul {port} este închis (server picat). Trecem la următorul...")
            client_socket.close()
            
    return None

def ruleaza_joc():
    # 1. Găsim și ne conectăm la lider
    socket_joc = conectare_la_lider()
    if not socket_joc:
        print("[CLIENT] Eroare critică: Nu am găsit niciun Lider activ în rețea!")
        return

    # 2. Dacă am ajuns aici, suntem conectați la Lider. Așteptăm întrebarea.
    pachet_primit = primeste_mesaj(socket_joc)
    
    if pachet_primit and pachet_primit.get("tip") == "INTREBARE":
        date_intrebare = pachet_primit["date"]
        
        print("="*40)
        print(f" ÎNTREBARE KAHOOT: {date_intrebare['text']}")
        print("-" * 40)
        for litera, varianta in date_intrebare["variante"].items():
            print(f"   {litera}) {varianta}")
        print("="*40)

        alegere = input("\n 👉 Răspunsul tău (A, B, C): ").strip().upper()

        pachet_raspuns = {
            "tip": "RASPUNS",
            "alegere": alegere
        }
        trimite_mesaj(socket_joc, pachet_raspuns)
        print("[CLIENT] Răspuns trimis! Așteptăm serverul...")

        pachet_rezultat = primeste_mesaj(socket_joc)
        
        if pachet_rezultat and pachet_rezultat.get("tip") == "REZULTAT":
            print("="*40)
            print(f" REZULTAT JOC: {pachet_rezultat.get('mesaj')}")
            print("="*40)
        else:
            print("[CLIENT] Serverul a închis conexiunea fără să trimită rezultatul.")
        
    socket_joc.close()
    print("[CLIENT] Joc încheiat.")

if __name__ == "__main__":
    ruleaza_joc()