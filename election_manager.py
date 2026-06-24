class ElectionManager:
    def __init__(self, node_id, functie_trimitere):
        self.node_id = node_id
        self.trimite_la_vecin = functie_trimitere # Funcția primită de la server
        
        # Stările specifice algoritmului
        self.este_lider = False
        self.id_lider_curent = None
        self.in_electie = False

    def incepe_electia(self):
        if not self.in_electie:
            self.in_electie = True
            print(f"[ELECȚIE {self.node_id}] ---- INIȚIAZĂ ELECȚIE ----")
            pachet = {
                "tip": "ELECTION",
                "lista_id": [self.node_id]
            }
            succes = self.trimite_la_vecin(pachet)
            
            # --- SOLUȚIA PENTRU ULTIMUL SUPRAVIEȚUITOR ---
            if not succes:
                print(f"[ELECȚIE {self.node_id}] Toți ceilalți sunt morți! Sunt singurul supraviețuitor. MĂ DECLAR LIDER!")
                self.este_lider = True
                self.id_lider_curent = self.node_id
                self.in_electie = False

    def proceseaza_electie(self, pachet):
        lista_id = pachet.get("lista_id", [])
        print(f"[ELECȚIE {self.node_id}] Pachet ELECTION primit. Lista: {lista_id}")
        
        if self.node_id in lista_id:
            noul_lider_id = max(lista_id)
            print(f"[ELECȚIE {self.node_id}] Cercul e complet. Lider maxim: {noul_lider_id}.")
            
            pachet_coord = {
                "tip": "COORDINATOR",
                "id_lider": noul_lider_id,
                "vizitate": [self.node_id]
            }
            self.trimite_la_vecin(pachet_coord)
            self.in_electie = False
        else:
            lista_id.append(self.node_id)
            pachet["lista_id"] = lista_id
            self.in_electie = True
            self.trimite_la_vecin(pachet)

    def proceseaza_coordonator(self, pachet):
        vizitate = pachet.get("vizitate", [])
        lider_anuntat = pachet.get("id_lider")
        
        self.id_lider_curent = lider_anuntat
        self.in_electie = False
        
        if lider_anuntat == self.node_id:
            self.este_lider = True
            print(f"\n[ELECȚIE {self.node_id}] >>> EU SUNT NOUL LIDER! <<<")
        else:
            self.este_lider = False
            print(f"\n[ELECȚIE {self.node_id}] Noul lider este: {lider_anuntat}")

        if self.node_id not in vizitate:
            vizitate.append(self.node_id)
            pachet["vizitate"] = vizitate
            self.trimite_la_vecin(pachet)