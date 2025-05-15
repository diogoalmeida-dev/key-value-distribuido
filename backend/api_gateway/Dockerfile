# 1) Imagem base leve com Python 3.12
FROM python:3.12-slim

# 2) Define o directório de trabalho dentro do container
WORKDIR /app

# 3) Copia o ficheiro de dependências primeiro …
COPY requirements.txt .

# 4) … instala as dependências (mantém a camada de cache pequena)
RUN pip install --no-cache-dir -r requirements.txt

# 5) Copia o código-fonte do serviço para a imagem
COPY app.py .

# 6) Garante que o output de logs aparece logo no terminal
ENV PYTHONUNBUFFERED=1

# 7) Comando que arranca o micro-serviço FastAPI
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
