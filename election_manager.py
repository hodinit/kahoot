class ElectionManager:
    def __init__(self, node_id, functie_trimitere):
        self.node_id = node_id
        self.trimite_la_vecin = functie_trimitere
        self.este_lider = False
        self.id_lider_curent = None
        self.in_electie = False

    def incepe_electia(self):
        if not self.in_electie:
            self.in_electie = True
            print(f"[ELECTIE {self.node_id}] Initiaza proces de electie.")
            pachet = {
                "tip": "ELECTION",
                "lista_id": [self.node_id]
            }
            succes = self.trimite_la_vecin(pachet)
            
            if not succes:
                print(f"[ELECTIE {self.node_id}] Niciun alt nod activ detectat. Nodul curent declarat lider.")
                self.este_lider = True
                self.id_lider_curent = self.node_id
                self.in_electie = False

    def proceseaza_electie(self, pachet):
        lista_id = pachet.get("lista_id", [])
        print(f"[ELECTIE {self.node_id}] Pachet ELECTION primit. Lista: {lista_id}")
        
        if self.node_id in lista_id:
            noul_lider_id = max(lista_id)
            print(f"[ELECTIE {self.node_id}] Inel complet. Lider determinat: {noul_lider_id}")
            
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
            print(f"[ELECTIE {self.node_id}] Acest nod a preluat rolul de lider.")
        else:
            self.este_lider = False
            print(f"[ELECTIE {self.node_id}] Lider curent setat la: {lider_anuntat}")

        if self.node_id not in vizitate:
            vizitate.append(self.node_id)
            pachet["vizitate"] = vizitate
            self.trimite_la_vecin(pachet)