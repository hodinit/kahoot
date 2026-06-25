const socket = io();

function schimbaEcran(idEcran) {
    document.querySelectorAll('.ecran').forEach(e => {
        e.classList.remove('activ');
    });
    document.getElementById(idEcran).classList.add('activ');
}

function intraInJoc() {
    const nume = document.getElementById('nume_jucator').value.trim();
    if(!nume) return alert("Introdu un nume!");
    
    socket.emit('conectare_nume', { nume: nume });
    schimbaEcran('ecran-asteptare');
    document.getElementById('text_asteptare').innerText = "Se cauta liderul in retea...";
}

function trimiteRaspuns(litera) {
    socket.emit('trimite_raspuns', { alegere: litera });
    schimbaEcran('ecran-asteptare');
    document.getElementById('text_asteptare').innerText = "Raspuns trimis. Evaluam...";
}

socket.on('schimba_ecran', function(data) {
    if(data.ecran === 'intrebare') {
        document.getElementById('text_intrebare').innerText = data.date.text;
        const container = document.getElementById('variante_container');
        container.innerHTML = ""; 
        
        for(const [litera, text] of Object.entries(data.date.variante)) {
            container.innerHTML += `
                <button onclick="trimiteRaspuns('${litera}')">
                    <strong>${litera})</strong> ${text}
                </button>
            `;
        }
        schimbaEcran('ecran-intrebare');
    } 
    else if(data.ecran === 'rezultat') {
        document.getElementById('text_rezultat').innerText = data.mesaj;
        schimbaEcran('ecran-rezultat');
    }
    else if(data.ecran === 'asteptare') {
        document.getElementById('text_asteptare').innerText = data.mesaj;
        schimbaEcran('ecran-asteptare');
    }
    else if(data.ecran === 'clasament') {
        const ul = document.getElementById('lista_clasament');
        ul.innerHTML = "";
        let loc = 1;
        for(const [nume, scor] of Object.entries(data.clasament)) {
            ul.innerHTML += `<li>
                #${loc} ${nume} - ${scor} pct
            </li>`;
            loc++;
        }
        schimbaEcran('ecran-clasament');
    }
});