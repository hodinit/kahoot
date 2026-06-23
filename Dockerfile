FROM python:3.11-slim

WORKDIR /app

# Copiem fișierele serverului în container
COPY server.py .
# Adăugați și fișierul cu logica alegerilor
COPY election_manager.py .
COPY network_utils.py .
COPY intrebari.json .

# Dezactivăm buffering-ul în Python pentru a vedea print-urile instant în log-uri
ENV PYTHONUNBUFFERED=1

# Nu punem o comandă fixă (CMD) pentru că fiecare container va porni cu argumente diferite