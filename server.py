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
        self.stare_joc = {
            "scoruri_globale": {},
            "progres_jucatori": {}
        }

        self.election = ElectionManager(self.node_id, self.trimite_vecinului)

        try:
            with open('intrebari.json', 'r', encoding='utf-8') as f:
                self.intrebari = json.load(f)
            print(f"[SERVER {self.node_id}] Baza de date a fost încărcată ({len(self.intrebari)} întrebări).")
        except Exception as e:
            print(f"[SERVER {self.node_id}] EROARE critică la încărcarea JSON: {e}")
            self.intrebari = [] # Lista goală ca să nu dea crash mai târziu

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
                    elif tip_mesaj == "SYNC_STARE":
                        if not self.election.este_lider: # Doar followerii ascultă asta
                            print(f"[SERVER {self.node_id}] Am primit backup-ul de memorie de la Lider.")
                            self.stare_joc = pachet.get("stare_joc", self.stare_joc)
                            # Dăm pachetul mai departe pe inel ca să ajungă și la celălalt follower
                            self.trimite_vecinului(pachet)
                        client_socket.close()
                    elif tip_mesaj == "LIDER_MORT":
                        if not self.election.in_electie:
                            print(f"\n[SERVER {self.node_id}] 🚨 ALERTĂ CLIENT: Liderul e mort! Reîncep alegerile!")
                            self.election.incepe_electia()
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
        print(f"[JOC] Începe sesiunea pentru {nume_jucator}")
        
        try:
            time.sleep(0.2) 
            
            # 1. Inițializăm jucătorul în memoria globală dacă e nou
            if nume_jucator not in self.stare_joc["progres_jucatori"]:
                self.stare_joc["progres_jucatori"][nume_jucator] = {"index_intrebare": 0}
                self.stare_joc["scoruri_globale"][nume_jucator] = 0
                
            # 2. Aflăm la ce întrebare a rămas (esențial pentru reconectare mai târziu)
            index_curent = self.stare_joc["progres_jucatori"][nume_jucator]["index_intrebare"]
            
            # 3. Bucla jocului: Cât timp mai are întrebări de parcurs
            while index_curent < len(self.intrebari):
                date_intrebare = self.intrebari[index_curent]
                
                # Trimitem întrebarea
                trimite_mesaj(socket_jucator, {"tip": "INTREBARE", "date": date_intrebare})
                timp_start = time.time() # ⏱️ PORNIM CRONOMETRUL
                
                # Așteptăm răspunsul
                raspuns = primeste_mesaj(socket_jucator)
                if not raspuns or raspuns.get("tip") != "RASPUNS":
                    print(f"[JOC] Jucătorul {nume_jucator} s-a deconectat prematur.")
                    break # Ieșim din buclă dacă a închis fereastra
                    
                timp_scurs = time.time() - timp_start # ⏱️ OPRIM CRONOMETRUL
                
                alegere_client = raspuns.get("alegere")
                este_corect = (alegere_client == date_intrebare["corect"])
                puncte_castigate = 0
                
                if este_corect:
                    # Formula de calcul: 1000 puncte maxim, scade 50 de puncte pe secundă scursă
                    # Minimul de puncte pentru un răspuns corect este 100
                    puncte_castigate = max(100, int(1000 - (timp_scurs * 50)))
                    self.stare_joc["scoruri_globale"][nume_jucator] += puncte_castigate
                
                # Trimitem rezultatul și punctajul
                mesaj_feedback = f"CORECT! Ai primit {puncte_castigate} puncte. (Timp: {timp_scurs:.1f}s)" if este_corect else f"GREȘIT! Răspuns corect: {date_intrebare['corect']}."
                trimite_mesaj(socket_jucator, {"tip": "REZULTAT", "mesaj": mesaj_feedback})
                
                # Salvăm progresul și trecem la următoarea
                index_curent += 1
                self.stare_joc["progres_jucatori"][nume_jucator]["index_intrebare"] = index_curent
                
                # --- NOU: Trimitem backup-ul către celelalte servere ---
                pachet_sync = {
                    "tip": "SYNC_STARE",
                    "stare_joc": self.stare_joc
                }
                # Lansăm pe inel într-un thread separat ca să nu înghețe jocul clientului
                threading.Thread(target=self.trimite_vecinului, args=(pachet_sync,), daemon=True).start()
                # --- Aici vom insera SINCRONIZAREA cu celelalte servere în pasul următor ---
                time.sleep(1.5) # Pauză scurtă ca jucătorul să poată citi rezultatul pe ecran
                
            # 4. Dacă a terminat toate întrebările din listă, îi trimitem Clasamentul Final
            if index_curent >= len(self.intrebari):
                # Sortăm dicționarul de scoruri descrescător pentru a crea Top-ul
                top_sortat = dict(sorted(self.stare_joc["scoruri_globale"].items(), key=lambda item: item[1], reverse=True))
                trimite_mesaj(socket_jucator, {"tip": "JOC_TERMINAT", "clasament": top_sortat})
                print(f"[JOC] {nume_jucator} a terminat jocul.")
                
        except Exception as e:
            print(f"[JOC] Conexiune cu {nume_jucator} s-a pierdut: {e}")
        finally:
            socket_jucator.close()

    def trimite_vecinului(self, pachet):
        # Lista tuturor host-urilor posibile din Docker
        toate_containerele = ['server1', 'server2', 'server3']
        
        try:
            # Încercăm vecinul normal
            sock_vecin = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock_vecin.settimeout(1.5)
            sock_vecin.connect((self.host_vecin_dreapta, self.port_vecin_dreapta))
            trimite_mesaj(sock_vecin, pachet)
            sock_vecin.close()
            return True
        except Exception as e:
            print(f"[SERVER {self.node_id}] Vecinul principal e MORT! Caut alt server viu...")
            
            # Deducem numele nostru ca să nu ne trimitem singuri mesaje
            numele_meu = f"server{int(self.node_id)//10}" 
            
            # Căutăm următorul server viu
            for host_alternativ in toate_containerele:
                if host_alternativ != numele_meu and host_alternativ != self.host_vecin_dreapta:
                    try:
                        sock_alt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock_alt.settimeout(1.5)
                        sock_alt.connect((host_alternativ, self.port_vecin_dreapta))
                        trimite_mesaj(sock_alt, pachet)
                        sock_alt.close()
                        print(f"[SERVER {self.node_id}] Am sărit nodul mort! Pachet trimis la {host_alternativ}.")
                        return True
                    except:
                        pass # E mort și ăsta, trecem la următorul
            
            print(f"[SERVER {self.node_id}] EROARE FATALĂ: Eu sunt singurul server rămas viu.")
            return False
        
if __name__ == "__main__":
    if len(sys.argv) != 5: # <--- Acum avem 5 argumente
        print("Utilizare: python server.py <ID_NOD> <PORT_ASCULTARE> <HOST_VECIN_DREAPTA> <PORT_VECIN_DREAPTA>")
        sys.exit(1)
        
    nod = ServerNode(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    nod.porneste()