# 1) Imagem base leve com Python 3.12
FROM python:3.12-slim

# 2) Define o directório de trabalho dentro do container
WORKDIR /app

# 3) Instala as dependências de sistema para psycopg2
RUN apt-get update && \
    apt-get install -y libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

# 4) Copia o ficheiro de dependências e instala-as
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5) Copia o código-fonte (API + worker)
COPY app.py .
COPY worker.py .

# 6) Garante que o output de logs aparece logo no terminal
ENV PYTHONUNBUFFERED=1

# 7) Por omissão o container serve **só** a API
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]