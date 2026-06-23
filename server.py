import socket
import sys
import threading
import time
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
            client_socket, _ = server_socket.accept()
            pachet = primeste_mesaj(client_socket)
            
            if pachet:
                # Rutăm pachetele direct către managerul de alegeri
                if pachet.get("tip") == "ELECTION":
                    self.election.proceseaza_electie(pachet)
                elif pachet.get("tip") == "COORDINATOR":
                    self.election.proceseaza_coordonator(pachet)
                
            client_socket.close()

    def trimite_vecinului(self, pachet):
        try:
            sock_vecin = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock_vecin.connect((self.host_vecin_dreapta, self.port_vecin_dreapta)) # <--- Modificat aici
            trimite_mesaj(sock_vecin, pachet)
            sock_vecin.close()
            return True
        except ConnectionRefusedError:
            print(f"[SERVER {self.node_id}] EROARE: Vecinul {self.host_vecin_dreapta}:{self.port_vecin_dreapta} nu răspunde!")
            return False
        
if __name__ == "__main__":
    if len(sys.argv) != 5: # <--- Acum avem 5 argumente
        print("Utilizare: python server.py <ID_NOD> <PORT_ASCULTARE> <HOST_VECIN_DREAPTA> <PORT_VECIN_DREAPTA>")
        sys.exit(1)
        
    nod = ServerNode(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    nod.porneste()