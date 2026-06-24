import socket
import sys
import threading
import time
import json
from network_utils import trimite_mesaj, primeste_mesaj
from election_manager import ElectionManager

class ServerNode:
    def __init__(self, node_id, port_ascultare, host_vecin_dreapta, port_vecin_dreapta):
        self.node_id = int(node_id)
        self.port_ascultare = int(port_ascultare)
        self.host_vecin_dreapta = host_vecin_dreapta
        self.port_vecin_dreapta = int(port_vecin_dreapta)
        self.host = '0.0.0.0'
        
        # Starea globală a jocului (esențială pentru reluarea jocului dacă pică un server)
        self.stare_joc = {
            "scoruri_globale": {},
            "progres_jucatori": {}
        }
        
        self.election = ElectionManager(self.node_id, self.trimite_vecinului)

        # Încărcăm baza de date o singură dată la pornire
        try:
            with open('intrebari.json', 'r', encoding='utf-8') as f:
                self.intrebari = json.load(f)
        except FileNotFoundError:
            # Fallback în caz că fișierul se numește questions.json
            try:
                with open('questions.json', 'r', encoding='utf-8') as f:
                    self.intrebari = json.load(f)
            except Exception as e:
                print(f"[SERVER {self.node_id}] Eroare critică JSON: {e}")
                self.intrebari = []
                
        print(f"[SERVER {self.node_id}] Am încărcat {len(self.intrebari)} întrebări.")

    def porneste(self):
        print(f"\n[SERVER {self.node_id}] PORNIT pe portul {self.port_ascultare}.")
        
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port_ascultare))
        server_socket.listen(5)
        
        threading.Thread(target=self.asculta_conexiuni, args=(server_socket,), daemon=True).start()
        
        time.sleep(2) 
        self.election.incepe_electia()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n[SERVER {self.node_id}] Se închide...")

    def asculta_conexiuni(self, server_socket):
        while True:
            try:
                client_socket, adresa = server_socket.accept()
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
                        if not self.election.este_lider: 
                            self.stare_joc = pachet.get("stare_joc", self.stare_joc)
                            self.trimite_vecinului(pachet) # Forward pe inel
                        client_socket.close()
                    elif tip_mesaj == "LIDER_MORT":
                        if not self.election.in_electie:
                            print(f"\n[SERVER {self.node_id}] 🚨 ALERTĂ: Liderul a picat! Reîncep alegerile!")
                            self.election.incepe_electia()
                        client_socket.close()
                        
                    elif tip_mesaj == "CONECTARE_JUCATOR":
                        if self.election.este_lider:
                            print(f"[SERVER {self.node_id}] Jucătorul '{pachet.get('nume')}' a intrat în joc.")
                            trimite_mesaj(client_socket, {"tip": "ACCES_PERMIS", "mesaj": "Succes!"})
                            threading.Thread(target=self.gestioneaza_jucator, args=(client_socket, pachet.get('nume')), daemon=True).start()
                        else:
                            trimite_mesaj(client_socket, {"tip": "ACCES_RESPINS", "mesaj": "Nu sunt liderul."})
                            client_socket.close()
                else:
                    client_socket.close()
                    
            except Exception as e:
                continue

    def gestioneaza_jucator(self, socket_jucator, nume_jucator):
        print(f"[JOC] Începe sesiunea pentru {nume_jucator}")
        
        try:
            time.sleep(0.5) 
            
            # Inițializăm scorul jucătorului și statusul dacă e prima dată când intră
            if nume_jucator not in self.stare_joc["progres_jucatori"]:
                self.stare_joc["progres_jucatori"][nume_jucator] = {"index_intrebare": 0, "terminat": False}
                self.stare_joc["scoruri_globale"][nume_jucator] = 0
            
            # Îl marcăm ca fiind conectat/activ
            self.stare_joc["progres_jucatori"][nume_jucator]["activ"] = True
                
            index_curent = self.stare_joc["progres_jucatori"][nume_jucator]["index_intrebare"]
            
            # Bucla care trece prin întrebări de unde a rămas
            while index_curent < len(self.intrebari):
                date_intrebare = self.intrebari[index_curent]
                
                # Trimitem întrebarea către GUI
                trimite_mesaj(socket_jucator, {"tip": "INTREBARE", "date": date_intrebare})
                
                # Pornim cronometrul imediat după ce am trimis întrebarea
                timp_start = time.time()
                
                # Așteptăm răspunsul
                raspuns = primeste_mesaj(socket_jucator)
                
                # Oprim cronometrul de îndată ce am primit pachetul
                timp_scurs = time.time() - timp_start
                
                if not raspuns or raspuns.get("tip") != "RASPUNS":
                    print(f"[JOC] {nume_jucator} s-a deconectat prematur.")
                    break 
                    
                alegere_client = raspuns.get("alegere")
                
                # Verificăm dacă răspunsul e corect
                raspuns_corect = date_intrebare.get("corect", date_intrebare.get("correct"))
                este_corect = (alegere_client == raspuns_corect)
                
                if este_corect:
                    # Formula: 1000 puncte din care scădem 50 puncte pentru fiecare secundă. Minim 100 puncte.
                    puncte_castigate = max(100, int(1000 - (timp_scurs * 50)))
                    self.stare_joc["scoruri_globale"][nume_jucator] += puncte_castigate
                    mesaj_feedback = f"Felicitări! Ai primit {puncte_castigate} puncte. (Timp: {timp_scurs:.1f}s) 🎉\nScor total: {self.stare_joc['scoruri_globale'][nume_jucator]}"
                else:
                    mesaj_feedback = f"Greșit! Răspunsul corect era {raspuns_corect}. ❌\nScor total: {self.stare_joc['scoruri_globale'][nume_jucator]}"
                
                # Trimitem rezultatul la interfață
                trimite_mesaj(socket_jucator, {"tip": "REZULTAT", "mesaj": mesaj_feedback})
                
                # Salvăm progresul și trecem la următoarea
                index_curent += 1
                self.stare_joc["progres_jucatori"][nume_jucator]["index_intrebare"] = index_curent
                
                # Backup către celelalte servere (Sincronizare stare)
                pachet_sync = {"tip": "SYNC_STARE", "stare_joc": self.stare_joc}
                threading.Thread(target=self.trimite_vecinului, args=(pachet_sync,), daemon=True).start()
                
                # Pauză ca jucătorul să vadă cu roșu/verde rezultatul pe interfață
                time.sleep(2.5) 
                
            # --- ZONA DE AȘTEPTARE LA FINAL DE JOC ---
            if index_curent >= len(self.intrebari):
                self.stare_joc["progres_jucatori"][nume_jucator]["terminat"] = True
                
                # Îi trimitem un mesaj temporar ca să știe că trebuie să aștepte
                trimite_mesaj(socket_jucator, {"tip": "REZULTAT", "mesaj": "Ai răspuns la toate întrebările!\nAșteptăm să termine și ceilalți jucători..."})
                
                # Bucla stă aici până când toți jucătorii ACTIVI au terminat
                while True:
                    toti_gata = True
                    for j_nume, j_date in self.stare_joc["progres_jucatori"].items():
                        # Dacă cineva e conectat și nu a terminat, nu suntem toți gata
                        if j_date.get("activ", False) and not j_date.get("terminat", False):
                            toti_gata = False
                            break
                    
                    if toti_gata:
                        break # Ieșim din buclă când toți sunt gata
                        
                    time.sleep(1) # Verificăm din nou peste 1 secundă
                
                # Abia acum calculăm și trimitem clasamentul final tuturor
                top_sortat = dict(sorted(self.stare_joc["scoruri_globale"].items(), key=lambda item: item[1], reverse=True))
                trimite_mesaj(socket_jucator, {"tip": "JOC_TERMINAT", "clasament": top_sortat})
                print(f"[JOC] {nume_jucator} a primit clasamentul final.")
                
        except Exception as e:
            print(f"[JOC] Eroare sesiune {nume_jucator}: {e}")
        finally:
            # La deconectare, îl marcăm ca "inactiv" ca să nu îi țină blocați pe ceilalți în sala de așteptare
            if nume_jucator in self.stare_joc["progres_jucatori"]:
                self.stare_joc["progres_jucatori"][nume_jucator]["activ"] = False
                # Sincronizăm rapid abandonul cu restul serverelor
                pachet_sync = {"tip": "SYNC_STARE", "stare_joc": self.stare_joc}
                threading.Thread(target=self.trimite_vecinului, args=(pachet_sync,), daemon=True).start()
                
            socket_jucator.close()

    def trimite_vecinului(self, pachet):
        """Trimite mesaj vecinului, și sare peste el dacă a picat!"""
        toate_containerele = ['server1', 'server2', 'server3']
        try:
            sock_vecin = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock_vecin.settimeout(1.5)
            sock_vecin.connect((self.host_vecin_dreapta, self.port_vecin_dreapta))
            trimite_mesaj(sock_vecin, pachet)
            sock_vecin.close()
            return True
        except Exception:
            numele_meu = f"server{int(self.node_id)//10}" 
            for host_alternativ in toate_containerele:
                if host_alternativ != numele_meu and host_alternativ != self.host_vecin_dreapta:
                    try:
                        sock_alt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock_alt.settimeout(1.5)
                        sock_alt.connect((host_alternativ, self.port_vecin_dreapta))
                        trimite_mesaj(sock_alt, pachet)
                        sock_alt.close()
                        return True
                    except:
                        pass
            return False
        
if __name__ == "__main__":
    if len(sys.argv) != 5: 
        print("Utilizare: python server.py <ID_NOD> <PORT_ASCULTARE> <HOST_VECIN_DREAPTA> <PORT_VECIN_DREAPTA>")
        sys.exit(1)
        
    nod = ServerNode(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    nod.porneste()