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
        self.stare_joc = {
            "scoruri_globale": {},
            "progres_jucatori": {}
        }
        self.election = ElectionManager(self.node_id, self.trimite_vecinului)

        with open('intrebari.json', 'r', encoding='utf-8') as f:
            self.intrebari = json.load(f)
        print(f"[SERVER {self.node_id}] Baza de date a fost incarcata cu succes.")

    def porneste(self):
        print(f"[SERVER {self.node_id}] Initiat pe portul {self.port_ascultare}.")
        
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port_ascultare))
        server_socket.listen(5)
        
        threading.Thread(target=self.asculta_conexiuni, args=(server_socket,), daemon=True).start()
        
        time.sleep(2) 
        self.election.incepe_electia()

        while True:
            time.sleep(1)

    def asculta_conexiuni(self, server_socket):
        while True:
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
                        print(f"[SERVER {self.node_id}] Pachet SYNC_STARE inregistrat.")
                        self.stare_joc = pachet.get("stare_joc", self.stare_joc)
                        self.trimite_vecinului(pachet)
                    client_socket.close()
                elif tip_mesaj == "LIDER_MORT":
                    if not self.election.in_electie:
                        print(f"[SERVER {self.node_id}] Alerta LIDER_MORT. Reinitiere proces electie.")
                        self.election.incepe_electia()
                    client_socket.close()
                elif tip_mesaj == "CONECTARE_JUCATOR":
                    if self.election.este_lider:
                        print(f"[SERVER {self.node_id}] Conexiune acceptata pentru: {pachet.get('nume')}")
                        trimite_mesaj(client_socket, {"tip": "ACCES_PERMIS", "mesaj": "Conexiune Lider stabilita."})
                        threading.Thread(target=self.gestioneaza_jucator, args=(client_socket, pachet.get('nume')), daemon=True).start()
                    else:
                        print(f"[SERVER {self.node_id}] Conexiune refuzata pentru: {pachet.get('nume')} (Nod follower).")
                        trimite_mesaj(client_socket, {"tip": "ACCES_RESPINS", "mesaj": "Acces refuzat. Nodul nu este lider."})
                        client_socket.close()
            else:
                client_socket.close()

    def gestioneaza_jucator(self, socket_jucator, nume_jucator):
        print(f"[JOC] Sesiune activa: {nume_jucator}")
        
        time.sleep(0.2) 
        
        if nume_jucator not in self.stare_joc["progres_jucatori"]:
            self.stare_joc["progres_jucatori"][nume_jucator] = {
                "index_intrebare": 0,
                "terminat": False
            }
            self.stare_joc["scoruri_globale"][nume_jucator] = 0
            
        index_curent = self.stare_joc["progres_jucatori"][nume_jucator]["index_intrebare"]
        
        while index_curent < len(self.intrebari):
            date_intrebare = self.intrebari[index_curent]
            
            trimite_mesaj(socket_jucator, {"tip": "INTREBARE", "date": date_intrebare})
            timp_start = time.time()
            
            raspuns = primeste_mesaj(socket_jucator)
            if not raspuns or raspuns.get("tip") != "RASPUNS":
                print(f"[JOC] Deconectare detectata: {nume_jucator}.")
                break
                
            timp_scurs = time.time() - timp_start
            alegere_client = raspuns.get("alegere")
            este_corect = (alegere_client == date_intrebare["corect"])
            puncte_castigate = 0
            
            if este_corect:
                puncte_castigate = max(100, int(1000 - (timp_scurs * 50)))
                self.stare_joc["scoruri_globale"][nume_jucator] += puncte_castigate
            
            mesaj_feedback = f"CORECT! +{puncte_castigate}p (Timp: {timp_scurs:.1f}s)" if este_corect else f"GRESIT! Raspuns corect: {date_intrebare['corect']}."
            trimite_mesaj(socket_jucator, {"tip": "REZULTAT", "mesaj": mesaj_feedback})
            
            index_curent += 1
            self.stare_joc["progres_jucatori"][nume_jucator]["index_intrebare"] = index_curent
            
            pachet_sync = {"tip": "SYNC_STARE", "stare_joc": self.stare_joc}
            threading.Thread(target=self.trimite_vecinului, args=(pachet_sync,), daemon=True).start()
            
            time.sleep(2.0)
            
        if index_curent >= len(self.intrebari):
            self.stare_joc["progres_jucatori"][nume_jucator]["terminat"] = True
            
            pachet_sync = {"tip": "SYNC_STARE", "stare_joc": self.stare_joc}
            threading.Thread(target=self.trimite_vecinului, args=(pachet_sync,), daemon=True).start()
            
            trimite_mesaj(socket_jucator, {"tip": "ASTEAPTA", "mesaj": "Sesiune finalizata. Se asteapta restul jucatorilor."})
            
            print(f"[JOC] Jucator {nume_jucator} mutat in lobby asteptare.")
            while True:
                toti_au_terminat = True
                for nume, info in self.stare_joc["progres_jucatori"].items():
                    if not info.get("terminat", False):
                        toti_au_terminat = False
                        break
                
                if toti_au_terminat:
                    break
                time.sleep(1.0)
            
            top_sortat = dict(sorted(self.stare_joc["scoruri_globale"].items(), key=lambda item: item[1], reverse=True))
            trimite_mesaj(socket_jucator, {"tip": "JOC_TERMINAT", "clasament": top_sortat})
            print(f"[JOC] Date clasament transmise catre {nume_jucator}.")
            
        socket_jucator.close()

    def trimite_vecinului(self, pachet):
        toate_containerele = ['server1', 'server2', 'server3']
        
        try:
            sock_vecin = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock_vecin.settimeout(1.5)
            sock_vecin.connect((self.host_vecin_dreapta, self.port_vecin_dreapta))
            trimite_mesaj(sock_vecin, pachet)
            sock_vecin.close()
            return True
        except Exception:
            print(f"[SERVER {self.node_id}] Nod principal indisponibil. Initiere protocol bypass.")
            
            numele_meu = f"server{int(self.node_id)//10}" 
            
            for host_alternativ in toate_containerele:
                if host_alternativ != numele_meu and host_alternativ != self.host_vecin_dreapta:
                    try:
                        sock_alt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock_alt.settimeout(1.5)
                        sock_alt.connect((host_alternativ, self.port_vecin_dreapta))
                        trimite_mesaj(sock_alt, pachet)
                        sock_alt.close()
                        print(f"[SERVER {self.node_id}] Bypass reusit. Pachet trimis la {host_alternativ}.")
                        return True
                    except Exception:
                        pass
            
            print(f"[SERVER {self.node_id}] Eroare retea: Niciun alt nod activ disponibil.")
            return False
            
if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Utilizare: python server.py <ID_NOD> <PORT_ASCULTARE> <HOST_VECIN_DREAPTA> <PORT_VECIN_DREAPTA>")
        sys.exit(1)
        
    nod = ServerNode(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    nod.porneste()