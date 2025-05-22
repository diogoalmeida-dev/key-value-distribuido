FROM python:3.12-slim
WORKDIR /app

RUN apt-get update && apt-get install -y libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py . 
COPY worker.py .

ENV PYTHONUNBUFFERED=1
# ► A imagem serve **apenas** o que o serviço pedir:
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
