import socket
import time
from network_utils import trimite_mesaj, primeste_mesaj

def conectare_la_lider():
    PORTURI_SERVERE = [5001, 5002, 5003]
    HOST = '127.0.0.1'
    nume_utilizator = input("Introdu numele tău de jucător: ").strip()

    # Buclă care se repetă până găsește un Lider valid
    while True:
        porturi_vii = [] # Ținem minte cine ne-a răspuns (ca să știm la cine să dăm alarma)
        
        for port in PORTURI_SERVERE:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                print(f"[CLIENT] Încercăm poarta {port}...")
                client_socket.connect((HOST, port))
                
                trimite_mesaj(client_socket, {"tip": "CONECTARE_JUCATOR", "nume": nume_utilizator})
                raspuns = primeste_mesaj(client_socket)
                
                if raspuns and raspuns.get("tip") == "ACCES_PERMIS":
                    print(f"[CLIENT] Succes! Te-ai conectat la Lider! (Port {port})\n")
                    return client_socket 
                else:
                    print(f"[CLIENT] Serverul de la {port} a răspuns, deci e viu. (Nu e lider)")
                    porturi_vii.append(port) 
                    client_socket.close()
                    
            except ConnectionRefusedError:
                print(f"[CLIENT] Portul {port} este închis (server picat).")
                client_socket.close()

        # Faza 2: Dacă am ieșit din for, înseamnă că nu am găsit liderul curent.
        if len(porturi_vii) > 0:
            print("\n[CLIENT] Niciun server nu e lider. Alarma! Liderul a murit!")
            port_salvator = porturi_vii[0] # Alegem primul server viu pe care îl știm
            
            try:
                sock_alerta = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock_alerta.connect((HOST, port_salvator))
                trimite_mesaj(sock_alerta, {"tip": "LIDER_MORT"})
                sock_alerta.close()
            except:
                pass
            
            print(f"[CLIENT] Am dat alarma la portul {port_salvator}. Aștept 3 secunde alegerile...\n")
            time.sleep(3) # Așteptăm ca inelul Docker să își aleagă șeful, apoi while-ul reîncepe
        else:
            print("[CLIENT] Eroare critică: Absolut toate serverele sunt moarte!")
            return None
        

def ruleaza_joc():
    socket_joc = conectare_la_lider()
    if not socket_joc:
        return

    # Folosim o buclă "părinte" care ne lasă să reluăm tot jocul în caz de crash
    while True:
        try:
            pachet_primit = primeste_mesaj(socket_joc)
            
            # Dacă Liderul moare subit, conexiunea se rupe și pachetul e None
            if not pachet_primit:
                raise ConnectionError("Conexiunea cu liderul s-a rupt brusc!")
                
            tip_mesaj = pachet_primit.get("tip")
            
            if tip_mesaj == "INTREBARE":
                date_intrebare = pachet_primit["date"]
                print("\n" + "="*40)
                print(f" ÎNTREBARE: {date_intrebare['text']}")
                for litera, varianta in date_intrebare["variante"].items():
                    print(f"   {litera}) {varianta}")
                print("="*40)

                alegere = input("\n 👉 Răspunsul tău: ").strip().upper()
                trimite_mesaj(socket_joc, {"tip": "RASPUNS", "alegere": alegere})
                
            elif tip_mesaj == "REZULTAT":
                print(f"\n 🎯 {pachet_primit.get('mesaj')}")
                
            elif tip_mesaj == "JOC_TERMINAT":
                print("\n" + "#"*40)
                print(" 🎉 CLASAMENT FINAL 🎉")
                loc = 1
                for nume, scor in pachet_primit.get("clasament", {}).items():
                    print(f"  {loc}. {nume} - {scor} puncte")
                    loc += 1
                print("#"*40)
                socket_joc.close()
                break # Ieșim definitiv, jocul e complet
                
        except Exception as e:
            # --- AICI SE FACE MAGIA DE RELUARE A JOCULUI ---
            print(f"\n[CLIENT] Eroare de rețea ({e}). Liderul a picat!")
            socket_joc.close()
            
            print("[CLIENT] Aștept 3 secunde ca serverele să-și aleagă noul Lider...")
            time.sleep(3)
            
            print("[CLIENT] Încerc reconectarea...")
            socket_joc = conectare_la_lider()
            
            if not socket_joc:
                print("[CLIENT] Reluarea a eșuat. Toate serverele sunt moarte.")
                break
            print("[CLIENT] M-am reconectat! Reluăm exact de unde ai rămas...\n")

    print("\n[CLIENT] Sesiune încheiată.")
    
if __name__ == "__main__":
    ruleaza_joc()