import socket
import threading
import time
import tkinter as tk
from tkinter import messagebox
from network_utils import trimite_mesaj, primeste_mesaj

class KahootClientGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Distributed Kahoot Quiz")
        self.root.geometry("500x400")
        self.root.configure(bg="#f3f4f6")
        
        self.socket_joc = None
        self.nume_jucator = ""
        self.porturi_servere = [5001, 5002, 5003]
        self.host = '127.0.0.1'
        
        # Containerul principal în care vom schimba ecranele
        self.main_frame = tk.Frame(self.root, bg="#383838")
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Pornim cu primul ecran (Login)
        self.ecran_login()

    def curata_ecranul(self):
        """Șterge toate widget-urile din fereastră pentru a face loc unui ecran nou."""
        for widget in self.main_frame.winfo_children():
            widget.destroy()

    def executa_pe_ui(self, functie, *args):
        """Metodă thread-safe care execută modificări vizuale pe thread-ul principal."""
        self.root.after(0, functie, *args)

    # ================= ECRAN 1: LOGIN =================
    def ecran_login(self):
        self.curata_ecranul()
        
        lbl_titlu = tk.Label(self.main_frame, text="Distributed Kahoot", font=("Arial", 22, "bold"), fg="#4f46e5", bg="#f3f4f6")
        lbl_titlu.pack(pady=30)
        
        lbl_nume = tk.Label(self.main_frame, text="Introdu numele tău de jucător:", font=("Arial", 12), bg="#f3f4f6")
        lbl_nume.pack(pady=5)
        
        self.entry_nume = tk.Entry(self.main_frame, font=("Arial", 14), justify="center")
        self.entry_nume.pack(pady=10, ipady=4)
        self.entry_nume.focus()
        
        self.btn_conectare = tk.Button(self.main_frame, text="Intră în Lobby", font=("Arial", 12, "bold"), 
                                       bg="#10b981", fg="white", relief="flat", command=self.actioneaza_conectare)
        self.btn_conectare.pack(pady=20, ipadx=10, ipady=5)

    def actioneaza_conectare(self):
        self.nume_jucator = self.entry_nume.get().strip()
        if not self.nume_jucator:
            messagebox.showwarning("Atenție", "Numele nu poate fi gol!")
            return
        
        self.btn_conectare.config(state="disabled", text="Se conectează...")
        # Lansăm logica de căutare a rețelei în fundal ca să nu înghețe ferestra
        threading.Thread(target=self.thread_background_joc, daemon=True).start()

    # ================= LOGICA DE REȚEA (BACKGROUND THREAD) =================
    def gaseste_si_conecteaza_lider(self):
        while True:
            porturi_vii = []
            for port in self.porturi_servere:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    sock.connect((self.host, port))
                    trimite_mesaj(sock, {"tip": "CONECTARE_JUCATOR", "nume": self.nume_jucator})
                    raspuns = primeste_mesaj(sock)
                    
                    if raspuns and raspuns.get("tip") == "ACCES_PERMIS":
                        return sock
                    else:
                        porturi_vii.append(port)
                        sock.close()
                except:
                    sock.close()
            
            # Dacă nu am găsit liderul, dăm alarma
            if porturi_vii:
                try:
                    sock_alerta = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock_alerta.connect((self.host, porturi_vii[0]))
                    trimite_mesaj(sock_alerta, {"tip": "LIDER_MORT"})
                    sock_alerta.close()
                except: pass
                time.sleep(3.0) # Așteptăm alegerile
            else:
                self.executa_pe_ui(messagebox.showerror, "Eroare", "Toate serverele sunt picate!")
                self.executa_pe_ui(self.ecran_login)
                return None

    def thread_background_joc(self):
        self.socket_joc = self.gaseste_si_conecteaza_lider()
        if not self.socket_joc:
            return
            
        while True:
            try:
                pachet = primeste_mesaj(self.socket_joc)
                if not pachet:
                    raise ConnectionError()
                
                tip = pachet.get("tip")
                if tip == "INTREBARE":
                    self.executa_pe_ui(self.ecran_intrebare, pachet["date"])
                elif tip == "REZULTAT":
                    self.executa_pe_ui(self.ecran_rezultat, pachet["mesaj"])
                elif tip == "ASTEAPTA":
                    self.executa_pe_ui(self.ecran_asteptare, pachet["mesaj"])
                elif tip == "JOC_TERMINAT":
                    self.executa_pe_ui(self.ecran_clasament, pachet["clasament"])
                    break
                    
            except:
                # Tratat scenariu de CRASH Lider în mijlocul gameplay-ului
                self.executa_pe_ui(self.ecran_asteptare, "Liderul a picat! Se alege un nou șef, nu te deconecta...")
                self.socket_joc.close()
                time.sleep(3.0)
                self.socket_joc = self.gaseste_si_conecteaza_lider()
                if not self.socket_joc:
                    break

    # ================= ECRAN 2: ÎNTREBARE =================
    def ecran_intrebare(self, date_intrebare):
        self.curata_ecranul()
        
        lbl_q = tk.Label(self.main_frame, text=date_intrebare["text"], font=("Arial", 14, "bold"), 
                         wraplength=440, justify="center", bg="#f3f4f6", fg="#1f2937")
        lbl_q.pack(pady=20)
        
        # Generăm dinamic butoane pentru opțiunile din JSON (A, B, C etc.)
        for litera, text_varianta in date_intrebare["variante"].items():
            btn = tk.Button(self.main_frame, text=f"{litera}) {text_varianta}", font=("Arial", 12),
                            bg="#ffffff", fg="#374151", activebackground="#e5e7eb", relief="groove", bd=1,
                            command=lambda l=litera: self.trimite_raspuns(l))
            btn.pack(fill="x", pady=5, ipady=6)

    def trimite_raspuns(self, varianta_aleasa):
        # Dezactivăm ecranul scurt timp după click ca să nu poată da dublu-click
        for widget in self.main_frame.winfo_children():
            if isinstance(widget, tk.Button):
                widget.config(state="disabled")
        
        threading.Thread(target=lambda: trimite_mesaj(self.socket_joc, {"tip": "RASPUNS", "alegere": varianta_aleasa}), daemon=True).start()

    # ================= ECRAN 3: REZULTAT INTERMEDIAR =================
    def ecran_rezultat(self, mesaj):
        self.curata_ecranul()
        
        culoare = "#10b981" if "CORECT" in mesaj else "#ef4444"
        lbl_res = tk.Label(self.main_frame, text=mesaj, font=("Arial", 16, "bold"), fg=culoare, bg="#f3f4f6", wraplength=440)
        lbl_res.pack(expand=True)

    # ================= ECRAN 4: SALA DE AȘTEPTARE =================
    def ecran_asteptare(self, mesaj):
        self.curata_ecranul()
        
        lbl_wait = tk.Label(self.main_frame, text=mesaj, font=("Arial", 14, "italic"), fg="#4b5563", bg="#f3f4f6", wraplength=440)
        lbl_wait.pack(expand=True)

    # ================= ECRAN 5: CLASAMENT FINAL =================
    def ecran_clasament(self, clasament):
        self.curata_ecranul()
        
        lbl_titlu = tk.Label(self.main_frame, text="🏆 CLASAMENT FINAL 🏆", font=("Arial", 18, "bold"), fg="#d97706", bg="#f3f4f6")
        lbl_titlu.pack(pady=15)
        
        frame_top = tk.Frame(self.main_frame, bg="#ffffff", bd=1, relief="solid")
        frame_top.pack(fill="both", expand=True, pady=10, padx=10)
        
        loc = 1
        for nume, scor in clasament.items():
            font_stil = ("Arial", 12, "bold") if loc == 1 else ("Arial", 11)
            text_linie = f" Locul {loc}: {nume} —  {scor} puncte"
            
            lbl_linie = tk.Label(frame_top, text=text_linie, font=font_stil, bg="#ffffff", anchor="w")
            lbl_linie.pack(fill="x", pady=4, padx=10)
            loc += 1

if __name__ == "__main__":
    root = tk.Tk()
    app = KahootClientGUI(root)
    root.mainloop()