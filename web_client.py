import socket
import threading
import time
from flask import Flask, render_template, request
from flask_socketio import SocketIO
from network_utils import trimite_mesaj, primeste_mesaj

app = Flask(__name__)
# Forțăm folosirea thread-urilor standard (evită erori pe Windows)
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins="*") 

PORTURI_SERVERE = [5001, 5002, 5003]
HOST_DOCKER = '127.0.0.1'

# Ținem minte ce conexiune de Docker corespunde fiecărui utilizator web
clienti_web = {}

def gaseste_lider(nume):
    """Caută liderul în Docker, fix ca în vechiul client.py"""
    while True:
        porturi_vii = []
        for port in PORTURI_SERVERE:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((HOST_DOCKER, port))
                trimite_mesaj(sock, {"tip": "CONECTARE_JUCATOR", "nume": nume})
                raspuns = primeste_mesaj(sock)
                if raspuns and raspuns.get("tip") == "ACCES_PERMIS":
                    return sock
                else:
                    porturi_vii.append(port)
                    sock.close()
            except:
                sock.close()
        
        if porturi_vii:
            try:
                sock_alerta = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock_alerta.connect((HOST_DOCKER, porturi_vii[0]))
                trimite_mesaj(sock_alerta, {"tip": "LIDER_MORT"})
                sock_alerta.close()
            except: pass
            time.sleep(3)
        else:
            return None

def asculta_docker(sid, nume):
    """Rulează în fundal pentru fiecare jucător, ascultând Liderul"""
    sock = gaseste_lider(nume)
    if not sock:
        socketio.emit('schimba_ecran', {'ecran': 'eroare', 'mesaj': 'Serverele sunt picate!'}, to=sid)
        return

    clienti_web[sid]['tcp_socket'] = sock

    while True:
        if sid not in clienti_web:
            break # Jucătorul a închis browserul

        try:
            pachet = primeste_mesaj(clienti_web[sid]['tcp_socket'])
            if not pachet:
                raise ConnectionError()
            
            tip = pachet.get("tip")
            if tip == "INTREBARE":
                socketio.emit('schimba_ecran', {'ecran': 'intrebare', 'date': pachet['date']}, to=sid)
            elif tip == "REZULTAT":
                socketio.emit('schimba_ecran', {'ecran': 'rezultat', 'mesaj': pachet['mesaj']}, to=sid)
            elif tip == "ASTEAPTA":
                socketio.emit('schimba_ecran', {'ecran': 'asteptare', 'mesaj': pachet['mesaj']}, to=sid)
            elif tip == "JOC_TERMINAT":
                socketio.emit('schimba_ecran', {'ecran': 'clasament', 'clasament': pachet['clasament']}, to=sid)
                break
        except:
            # --- MAGIA FAILOVER-ULUI: Trimisă direct pe web ---
            socketio.emit('schimba_ecran', {'ecran': 'asteptare', 'mesaj': '🚨 Lider picat! Reconectare...'}, to=sid)
            if sid in clienti_web and clienti_web[sid].get('tcp_socket'):
                try: clienti_web[sid]['tcp_socket'].close()
                except: pass
            
            time.sleep(3)
            sock_nou = gaseste_lider(nume)
            if not sock_nou:
                break
            clienti_web[sid]['tcp_socket'] = sock_nou

# --- Rute Web ---
@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('conectare_nume')
def handle_conectare(data):
    nume = data['nume']
    sid = request.sid
    clienti_web[sid] = {'nume': nume, 'tcp_socket': None}
    threading.Thread(target=asculta_docker, args=(sid, nume), daemon=True).start()

@socketio.on('trimite_raspuns')
def handle_raspuns(data):
    sid = request.sid
    if sid in clienti_web and clienti_web[sid]['tcp_socket']:
        try:
            trimite_mesaj(clienti_web[sid]['tcp_socket'], {"tip": "RASPUNS", "alegere": data['alegere']})
        except: pass

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    if sid in clienti_web:
        sock = clienti_web[sid].get('tcp_socket')
        if sock:
            try: sock.close()
            except: pass
        del clienti_web[sid]

if __name__ == '__main__':
    # Rulăm pe 0.0.0.0 ca să poți accesa de pe telefon/alt laptop prin Wi-Fi!
    socketio.run(app, host='0.0.0.0', port=5000)