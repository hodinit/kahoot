import socket
import threading
import time
from flask import Flask, render_template, request
from flask_socketio import SocketIO
from network_utils import trimite_mesaj, primeste_mesaj

app = Flask(__name__)
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins="*") 

PORTURI_SERVERE = [5001, 5002, 5003]
HOST_DOCKER = '127.0.0.1'

clienti_web = {}

def gaseste_lider(nume):
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
            except Exception:
                sock.close()
        
        if porturi_vii:
            try:
                sock_alerta = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock_alerta.connect((HOST_DOCKER, porturi_vii[0]))
                trimite_mesaj(sock_alerta, {"tip": "LIDER_MORT"})
                sock_alerta.close()
            except Exception: 
                pass
            time.sleep(3)
        else:
            return None

def asculta_docker(sid, nume):
    sock = gaseste_lider(nume)
    if not sock:
        socketio.emit('schimba_ecran', {'ecran': 'eroare', 'mesaj': 'Nodurile de backend sunt indisponibile.'}, to=sid)
        return

    clienti_web[sid]['tcp_socket'] = sock

    while True:
        if sid not in clienti_web:
            break

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
        except Exception:
            socketio.emit('schimba_ecran', {'ecran': 'asteptare', 'mesaj': 'Conexiune pierduta. Se reinitiaza procesul de failover...'}, to=sid)
            if sid in clienti_web and clienti_web[sid].get('tcp_socket'):
                try: 
                    clienti_web[sid]['tcp_socket'].close()
                except Exception: 
                    pass
            
            time.sleep(3)
            sock_nou = gaseste_lider(nume)
            if not sock_nou:
                break
            clienti_web[sid]['tcp_socket'] = sock_nou

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
        except Exception: 
            pass

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    if sid in clienti_web:
        sock = clienti_web[sid].get('tcp_socket')
        if sock:
            try: 
                sock.close()
            except Exception: 
                pass
        del clienti_web[sid]

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)