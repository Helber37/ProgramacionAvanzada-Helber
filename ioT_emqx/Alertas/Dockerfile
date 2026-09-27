FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=America/Bogota

RUN apt-get update && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alertas_umbral.py .
COPY destinatarios.txt .

RUN useradd --create-home --uid 10001 app
USER app

CMD ["python", "alertas_umbral.py"]