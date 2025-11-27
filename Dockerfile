# Dockerfile for SOXauto C-PG-1
# Target: n8n Integration via FastAPI

# Stage 1: Builder
FROM python:3.11-slim as builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Installation des dépendances système (Build tools + ODBC)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    gnupg2 \
    unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

# Ajout des clés Microsoft pour le Driver ODBC 17 (Compatible avec votre connection string)
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql17 \
    && rm -rf /var/lib/apt/lists/*

# Environnement virtuel
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Installation des dépendances Python
COPY requirements.txt .
# On s'assure d'avoir fastapi et uvicorn pour l'interface n8n
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install fastapi uvicorn python-multipart

# Stage 2: Production Runner
FROM python:3.11-slim as production

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/opt/venv/bin:$PATH"

# Installation des dépendances Runtime (ODBC uniquement)
RUN apt-get update && apt-get install -y \
    curl \
    gnupg2 \
    unixodbc \
    && rm -rf /var/lib/apt/lists/*

# Installation du Driver ODBC 17 (Runtime)
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql17 \
    && rm -rf /var/lib/apt/lists/*

# Copie de l'environnement virtuel
COPY --from=builder /opt/venv /opt/venv

# Création user non-root
RUN groupadd --gid 1000 appuser && useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser
WORKDIR /app

# Copie du code source
COPY --chown=appuser:appuser src/ /app/src/
COPY --chown=appuser:appuser scripts/ /app/scripts/
COPY --chown=appuser:appuser tests/ /app/tests/

# Création des dossiers de sortie
RUN mkdir -p /app/evidence_output && chown -R appuser:appuser /app/evidence_output

USER appuser

# Port pour l'API n8n
EXPOSE 8000

# Lancement via Uvicorn (API)
CMD ["uvicorn", "src.frontend.n8n_api:app", "--host", "0.0.0.0", "--port", "8000"]