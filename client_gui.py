import tkinter as tk
from tkinter import messagebox
import socket
import threading
import time
from network_utils import trimite_mesaj, primeste_mesaj

class KahootClientGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Trivia Distribuit - Client")
        self.root.geometry("600x550")
        self.root.configure(bg="#2c3e50")
        
        self.client_socket = None
        self.nume_utilizator = ""
        self.joc_terminat = False

        self.setup_ui()

    def setup_ui(self):
        self.frame_login = tk.Frame(self.root, bg="#2c3e50")
        
        lbl_titlu = tk.Label(self.frame_login, text="Kahoot Distribuit", font=("Helvetica", 28, "bold"), fg="white", bg="#2c3e50")
        lbl_titlu.pack(pady=40)

        self.entry_nume = tk.Entry(self.frame_login, font=("Helvetica", 16), justify="center")
        self.entry_nume.insert(0, "Nume Jucător")
        self.entry_nume.pack(pady=20, ipady=5, ipadx=10)

        btn_conectare = tk.Button(self.frame_login, text="Intră în Joc", font=("Helvetica", 16, "bold"), bg="#27ae60", fg="white", command=self.start_joc)
        btn_conectare.pack(pady=10, ipadx=20, ipady=5)

        self.frame_asteptare = tk.Frame(self.root, bg="#2c3e50")
        self.lbl_asteptare = tk.Label(self.frame_asteptare, text="Așteptăm serverul...", font=("Helvetica", 16), fg="white", bg="#2c3e50", wraplength=500, justify="center")
        self.lbl_asteptare.pack(expand=True)

        self.frame_intrebare = tk.Frame(self.root, bg="#2c3e50")
        self.lbl_intrebare = tk.Label(self.frame_intrebare, text="Aici va fi întrebarea?", font=("Helvetica", 18, "bold"), fg="white", bg="#2c3e50", wraplength=550, justify="center")
        self.lbl_intrebare.pack(pady=20)

        grid_butoane = tk.Frame(self.frame_intrebare, bg="#2c3e50")
        grid_butoane.pack(expand=True, fill="both", padx=20, pady=10)
        grid_butoane.columnconfigure(0, weight=1)
        grid_butoane.columnconfigure(1, weight=1)

        self.btn_a = tk.Button(grid_butoane, text="A", font=("Helvetica", 14, "bold"), bg="#e74c3c", fg="white", command=lambda: self.trimite_raspuns("A"))
        self.btn_b = tk.Button(grid_butoane, text="B", font=("Helvetica", 14, "bold"), bg="#3498db", fg="white", command=lambda: self.trimite_raspuns("B"))
        self.btn_c = tk.Button(grid_butoane, text="C", font=("Helvetica", 14, "bold"), bg="#f1c40f", fg="black", command=lambda: self.trimite_raspuns("C"))
        self.btn_d = tk.Button(grid_butoane, text="D", font=("Helvetica", 14, "bold"), bg="#2ecc71", fg="white", command=lambda: self.trimite_raspuns("D"))

        self.btn_a.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.btn_b.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.btn_c.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.btn_d.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)


        self.frame_clasament = tk.Frame(self.root, bg="#2c3e50")
        lbl_titlu_clasament = tk.Label(self.frame_clasament, text="CLASAMENT FINAL", font=("Helvetica", 24, "bold"), fg="#f1c40f", bg="#2c3e50")
        lbl_titlu_clasament.pack(pady=30)
        
        self.lbl_scoruri = tk.Label(self.frame_clasament, text="", font=("Helvetica", 18), fg="white", bg="#2c3e50", justify="left")
        self.lbl_scoruri.pack(pady=10)

        self.arata_cadru(self.frame_login)

    def arata_cadru(self, frame_activ):
        """Schimba ecranul vizibil"""
        for frame in (self.frame_login, self.frame_asteptare, self.frame_intrebare, self.frame_clasament):
            frame.pack_forget()
        frame_activ.pack(fill="both", expand=True)

    def actualizeaza_text_asteptare(self, text):
        """Metoda sigura pentru a schimba textul din thread-ul secundar"""
        self.lbl_asteptare.config(text=text)
        self.arata_cadru(self.frame_asteptare)

    def start_joc(self):
        self.nume_utilizator = self.entry_nume.get().strip()
        if not self.nume_utilizator or self.nume_utilizator == "Nume Jucator":
            messagebox.showwarning("Atentie", "Te rugam sa introduci un nume valid!")
            return

        self.joc_terminat = False
        self.actualizeaza_text_asteptare("Se initializeaza sesiunea de joc...")
        
        threading.Thread(target=self.fir_executie_retea, daemon=True).start()

    def conectare_la_lider(self):
        """Cauta liderul activ. Dacă niciunul nu e lider, da alarma transparent."""
        PORTURI_SERVERE = [5001, 5002, 5003]
        HOST = '127.0.0.1'

        while not self.joc_terminat:
            porturi_vii = []
            for port in PORTURI_SERVERE:
                try:
                    self.root.after(0, self.actualizeaza_text_asteptare, "Se stabileste conexiunea...")
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.connect((HOST, port))
                    
                    trimite_mesaj(sock, {"tip": "CONECTARE_JUCATOR", "nume": self.nume_utilizator})
                    raspuns = primeste_mesaj(sock)
                    
                    if raspuns and raspuns.get("tip") == "ACCES_PERMIS":
                        self.root.after(0, self.actualizeaza_text_asteptare, "Conectat! Asteptam datele jocului...")
                        return sock
                    else:
                        porturi_vii.append(port)
                        sock.close()
                except ConnectionRefusedError:
                    pass

            if porturi_vii:
                self.root.after(0, self.actualizeaza_text_asteptare, "Se sincronizeaza reteaua...\nTe rugam sa astepti.")
                try:
                    sock_alerta = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock_alerta.connect((HOST, porturi_vii[0]))
                    trimite_mesaj(sock_alerta, {"tip": "LIDER_MORT"})
                    sock_alerta.close()
                except:
                    pass
                time.sleep(3) 
            else:
                self.root.after(0, self.actualizeaza_text_asteptare, "Asteptam un server disponibil...\nReincercare automata in curs.")
                time.sleep(3)
        return None

    def fir_executie_retea(self):
        """Gestioneaza conexiunea, deconectarea si reconectarea automata (transparent pentru user)"""
        while not self.joc_terminat:
            self.client_socket = self.conectare_la_lider()
            if not self.client_socket:
                break
            
            try:
                while True:
                    pachet_primit = primeste_mesaj(self.client_socket)
                    if not pachet_primit:
                        raise ConnectionError("Conexiune rupta brusc!")
                    
                    tip_mesaj = pachet_primit.get("tip")
                    
                    if tip_mesaj == "INTREBARE":
                        self.root.after(0, self.afiseaza_intrebare, pachet_primit["date"])
                    
                    elif tip_mesaj == "REZULTAT":
                        self.root.after(0, self.actualizeaza_text_asteptare, f"Rezultat:\n\n{pachet_primit.get('mesaj')}")
                    
                    elif tip_mesaj == "JOC_TERMINAT":
                        self.joc_terminat = True
                        self.root.after(0, self.afiseaza_clasament, pachet_primit.get("clasament", {}))
                        break

            except Exception as e:
                if not self.joc_terminat:
                    print(f"[Log Ascuns] Eroare retea / Failover declansat: {e}")
                    
                    self.root.after(0, self.actualizeaza_text_asteptare, "Se actualizeaza starea jocului...\nTe rugam sa astepti cateva momente.")
                    if self.client_socket:
                        self.client_socket.close()
                    time.sleep(3)

    def afiseaza_intrebare(self, date_intrebare):
        text_q = date_intrebare.get("text", date_intrebare.get("question", ""))
        variante = date_intrebare.get("variante", date_intrebare.get("options", {}))

        self.lbl_intrebare.config(text=text_q)
        
        self.btn_a.config(text=f"A) {variante.get('A', '')}", state="normal")
        self.btn_b.config(text=f"B) {variante.get('B', '')}", state="normal")
        self.btn_c.config(text=f"C) {variante.get('C', '')}", state="normal")
        self.btn_d.config(text=f"D) {variante.get('D', '')}", state="normal")
        
        self.arata_cadru(self.frame_intrebare)

    def trimite_raspuns(self, alegere):
        pachet_raspuns = {
            "tip": "RASPUNS",
            "alegere": alegere
        }
        trimite_mesaj(self.client_socket, pachet_raspuns)
        
        self.btn_a.config(state="disabled")
        self.btn_b.config(state="disabled")
        self.btn_c.config(state="disabled")
        self.btn_d.config(state="disabled")
        
        self.lbl_intrebare.config(text=f"Ai ales varianta {alegere}!\nAsteptam validarea de la server...")

    def afiseaza_clasament(self, clasament):
        text_scoruri = ""
        loc = 1
        for nume, scor in clasament.items():
            text_scoruri += f"{loc}. {nume}  -  {scor} puncte\n"
            loc += 1
            
        self.lbl_scoruri.config(text=text_scoruri)
        self.arata_cadru(self.frame_clasament)

if __name__ == "__main__":
    root = tk.Tk()
    app = KahootClientGUI(root)
    root.mainloop()