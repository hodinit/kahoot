import socket
import sys
import threading
import time
import json
from network_utils import trimite_mesaj, primeste_mesaj
from election_manager import ElectionManager # Importăm logica separată

class ServerNode:
    def __init__(self, node_id, port_ascultare, host_vecin_dreapta, port_vecin_dreapta):
        self.node_id = int(node_id)
        self.port_ascultare = int(port_ascultare)
        self.host_vecin_dreapta = host_vecin_dreapta  # <--- NOU: poate fi 'server2' sau '127.0.0.1'
        self.port_vecin_dreapta = int(port_vecin_dreapta)

        self.host = '0.0.0.0'
        
        self.election = ElectionManager(self.node_id, self.trimite_vecinului)

    def porneste(self):
        print(f"\n[SERVER {self.node_id}] PORNIT pe portul {self.port_ascultare}.")
        
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port_ascultare))
        server_socket.listen(5)
        
        threading.Thread(target=self.asculta_conexiuni, args=(server_socket,), daemon=True).start()
        
        time.sleep(2) 
        self.election.incepe_electia() # Apelăm logica din celălalt fișier

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n[SERVER {self.node_id}] Se închide...")

    def asculta_conexiuni(self, server_socket):
        while True:
            try:
                client_socket, adresa = server_socket.accept()
                # Log de debug: vedem dacă Docker trimite conexiunea în container
                # print(f"[SERVER {self.node_id}] Conexiune detectată de la {adresa}")
                
                pachet = primeste_mesaj(client_socket)
                
                if pachet:
                    tip_mesaj = pachet.get("tip")
                    
                    if tip_mesaj == "ELECTION":
                        self.election.proceseaza_electie(pachet)
                        client_socket.close()
                    elif tip_mesaj == "COORDINATOR":
                        self.election.proceseaza_coordonator(pachet)
                        client_socket.close()
                        
                    elif tip_mesaj == "CONECTARE_JUCATOR":
                        if self.election.este_lider:
                            print(f"[SERVER {self.node_id}] Jucătorul '{pachet.get('nume')}' cere acces. Răspund: PERMIS.")
                            trimite_mesaj(client_socket, {"tip": "ACCES_PERMIS", "mesaj": "Te-ai conectat la Lider!"})
                            threading.Thread(target=self.gestioneaza_jucator, args=(client_socket, pachet.get('nume')), daemon=True).start()
                        else:
                            print(f"[SERVER {self.node_id}] Jucătorul '{pachet.get('nume')}' cere acces, dar NU sunt lider. Răspund: RESPINS.")
                            trimite_mesaj(client_socket, {"tip": "ACCES_RESPINS", "mesaj": "Nu sunt liderul."})
                            client_socket.close()
                else:
                    # Dacă pachetul e None, înseamnă că s-au primit biți defecți sau o conexiune goală
                    client_socket.close()
                    
            except Exception as e:
                print(f"[SERVER {self.node_id}] EROARE CRITICĂ în thread-ul de rețea: {e}")
                # Nu lăsăm loop-ul să se oprească, trecem la următoarea conexiune
                continue

    def gestioneaza_jucator(self, socket_jucator, nume_jucator):
        """Aici se va desfășura logica jocului pentru fiecare jucător conectat la Lider."""
        print(f"[JOC] Începe sesiunea pentru {nume_jucator}")
        
        try:
            time.sleep(0.2) 
            
            with open('intrebari.json', 'r', encoding='utf-8') as f:
                intrebari = json.load(f)
            
            # Luăm prima întrebare pentru test
            date_intrebare = intrebari[0]
            pachet_intrebare = {"tip": "INTREBARE", "date": date_intrebare}
            trimite_mesaj(socket_jucator, pachet_intrebare)
            
            # Așteptăm răspunsul jucătorului
            raspuns = primeste_mesaj(socket_jucator)
            
            if raspuns and raspuns.get("tip") == "RASPUNS":
                alegere_client = raspuns.get("alegere")
                print(f"[JOC] {nume_jucator} a ales varianta: {alegere_client}")
                
                # Evaluăm dacă e corect
                este_corect = (alegere_client == date_intrebare["corect"])
                
                # Pregătim pachetul de răspuns de la server
                pachet_rezultat = {
                    "tip": "REZULTAT",
                    "corect": este_corect,
                    "mesaj": "Felicitări! Ai răspuns CORECT! 🎉" if este_corect else f"Greșit! Răspunsul corect era {date_intrebare['corect']}. ❌"
                }
                
                # Trimitem feedback-ul înapoi la client
                trimite_mesaj(socket_jucator, pachet_rezultat)
                
        except Exception as e:
            print(f"[JOC] Conexiunea cu {nume_jucator} s-a pierdut: {e}")
        finally:
            socket_jucator.close()

    def trimite_vecinului(self, pachet):
        """Deschide o conexiune scurtă către vecinul din dreapta și îi trimite un mesaj."""
        try:
            sock_vecin = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Adăugăm un timeout scurt ca să nu rămână blocat dacă vecinul e ocupat
            sock_vecin.settimeout(2.0) 
            sock_vecin.connect((self.host_vecin_dreapta, self.port_vecin_dreapta))
            trimite_mesaj(sock_vecin, pachet)
            sock_vecin.close()
            return True
        except Exception as e: # <--- Am schimbat aici ca să prindem ORICE eroare
            # Schimbăm în print simplu, e normal la pornire până se ridică toate containerele
            print(f"[SERVER {self.node_id}] Notificare rețea: Vecinul nu e gata încă sau eroare temporară ({e})")
            return False
        
if __name__ == "__main__":
    if len(sys.argv) != 5: # <--- Acum avem 5 argumente
        print("Utilizare: python server.py <ID_NOD> <PORT_ASCULTARE> <HOST_VECIN_DREAPTA> <PORT_VECIN_DREAPTA>")
        sys.exit(1)
        
    nod = ServerNode(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    nod.porneste()