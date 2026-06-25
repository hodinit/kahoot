FROM python:3.11-slim

WORKDIR /app

COPY server.py .
COPY election_manager.py .
COPY network_utils.py .
COPY intrebari.json .

ENV PYTHONUNBUFFERED=1
