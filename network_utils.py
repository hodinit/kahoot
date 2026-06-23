import socket
import json

def trimite_mesaj(sock, dictionar_date):
    """Transformă un dicționar Python în JSON binar și îl trimite pe socket."""
    try:
        # 1. Transformăm dicționarul în text JSON
        text_json = json.dumps(dictionar_date)
        # 2. Codificăm textul în biți (utf-8) și îl trimitem
        sock.sendall(text_json.encode('utf-8'))
        return True
    except Exception as e:
        print(f"Eroare la trimitere: {e}")
        return False

def primeste_mesaj(sock, buffer_size=4096):
    """Așteaptă date de pe socket, le decodifică din biți și returnează un dicționar."""
    try:
        # 1. Citim biții de pe rețea
        biti_primiti = sock.recv(buffer_size)
        if not biti_primiti:
            return None # Conexiunea s-a închis
            
        # 2. Transformăm biții înapoi în text, apoi în dicționar Python
        text_json = biti_primiti.decode('utf-8')
        return json.loads(text_json)
    except Exception as e:
        print(f"Eroare la primire: {e}")
        return None