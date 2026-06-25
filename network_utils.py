import socket
import json

def trimite_mesaj(sock, dictionar_date):
    try:
        text_json = json.dumps(dictionar_date)
        sock.sendall(text_json.encode('utf-8'))
        return True
    except Exception as e:
        print(f"[RETEA] Eroare la trimitere: {e}")
        return False

def primeste_mesaj(sock, buffer_size=4096):
    try:
        biti_primiti = sock.recv(buffer_size)
        if not biti_primiti:
            return None
            
        text_json = biti_primiti.decode('utf-8')
        return json.loads(text_json)
    except Exception as e:
        print(f"[RETEA] Eroare la primire: {e}")
        return None