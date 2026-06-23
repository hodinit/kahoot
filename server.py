import socket
import json
from network_utils import trimite_mesaj, primeste_mesaj

def ruleaza_server_test():
    # 1. Citim baza de date cu întrebări
    try:
        with open('intrebari.json', 'r', encoding='utf-8') as f:
            intrebari = json.load(f)
    except FileNotFoundError:
        print("Eroare: Fișierul intrebari.json nu a fost găsit!")
        return

    # 2. Configurăm setările rețelei (Socket)
    HOST = '127.0.0.1' # Localhost (doar pe PC-ul vostru)
    PORT = 5000

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # Permite refolosirea portului imediat după ce oprim scriptul 
    # (previne eroarea "Address already in use" când dați restart des)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    server_socket.bind((HOST, PORT))
    
    # Ascultăm o singură conexiune pentru acest test inițial
    server_socket.listen(1) 
    print(f" [SERVER] Baza de date încărcată. Așteptăm jucători pe {HOST}:{PORT}...")

    # 3. Așteptăm să se conecteze clientul (aici codul se oprește și așteaptă)
    client_socket, adresa_client = server_socket.accept()
    print(f" [SERVER] Jucător nou conectat de la: {adresa_client}")

    # 4. Pregătim și trimitem prima întrebare din listă
    prima_intrebare = intrebari[0]
    pachet_intrebare = {
        "tip": "INTREBARE",
        "date": prima_intrebare
    }

    print(" [SERVER] Trimitem prima întrebare către jucător...")
    trimite_mesaj(client_socket, pachet_intrebare)

    # 5. Așteptăm răspunsul jucătorului
    print(" [SERVER] Așteptăm răspunsul...")
    raspuns = primeste_mesaj(client_socket)
    
    if raspuns:
        print(f" [SERVER] Am primit pachetul de la client: {raspuns}")
        
        # O mică validare de logică
        if raspuns.get("alegere") == prima_intrebare["corect"]:
            print(" [SERVER] REZULTAT: Jucătorul a răspuns corect!")
        else:
            print(" [SERVER] REZULTAT: Jucătorul a greșit.")
    else:
        print(" [SERVER] Clientul s-a deconectat fără să răspundă.")

    # 6. Închidem conexiunile pentru a încheia testul curat
    client_socket.close()
    server_socket.close()
    print(" [SERVER] Testul s-a încheiat cu succes.")

if __name__ == "__main__":
    ruleaza_server_test()