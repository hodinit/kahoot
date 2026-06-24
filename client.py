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
    socket_joc = conectare_la_lider()
    if not socket_joc:
        print("[CLIENT] Eroare critică: Nu am găsit niciun Lider activ în rețea!")
        return

    # Intrăm într-o buclă infinită pentru a primi pachete de la server
    while True:
        pachet_primit = primeste_mesaj(socket_joc)
        
        if not pachet_primit:
            print("\n[CLIENT] Conexiunea cu serverul s-a întrerupt brusc!")
            break
            
        tip_mesaj = pachet_primit.get("tip")
        
        if tip_mesaj == "INTREBARE":
            date_intrebare = pachet_primit["date"]
            print("\n" + "="*40)
            print(f" ÎNTREBARE: {date_intrebare['text']}")
            print("-" * 40)
            for litera, varianta in date_intrebare["variante"].items():
                print(f"   {litera}) {varianta}")
            print("="*40)

            alegere = input("\n 👉 Răspunsul tău (A, B, C): ").strip().upper()
            trimite_mesaj(socket_joc, {"tip": "RASPUNS", "alegere": alegere})
            print("[CLIENT] Răspuns trimis! Evaluăm...")
            
        elif tip_mesaj == "REZULTAT":
            print("\n" + "-"*40)
            print(f" 🎯 {pachet_primit.get('mesaj')}")
            print("-" * 40)
            print("Așteaptă următoarea întrebare...")
            
        elif tip_mesaj == "JOC_TERMINAT":
            print("\n" + "#"*40)
            print(" 🎉 JOCUL S-A TERMINAT! CLASAMENT FINAL 🎉")
            print("#"*40)
            loc = 1
            clasament = pachet_primit.get("clasament", {})
            for nume, scor in clasament.items():
                print(f"  {loc}. {nume} - {scor} puncte")
                loc += 1
            print("#"*40)
            break # Ieșim din buclă pentru că jocul e gata
            
    socket_joc.close()
    print("\n[CLIENT] Sesiune încheiată.")

if __name__ == "__main__":
    ruleaza_joc()