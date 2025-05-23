# API Gateway

Este repositório contém a **API Gateway** desenvolvida em FastAPI, que enfileira operações de escrita no RabbitMQ e reencaminha leituras para um Storage Node.

## Índice

- [Pré-requisitos](#pré-requisitos)
- [Instalação](#instalação)
- [Configuração](#configuração)
- [Endpoints](#endpoints)
  - [Health Check](#health-check)
  - [PUT /store](#put-store)
  - [GET /store](#get-store)
  - [DELETE /store](#delete-store)
- [Exemplos curl.exe](#exemplos-curlexe)
- [Códigos de Erro (4xx)](#códigos-de-erro-4xx)

## Pré-requisitos

- Python 3.9+
- [RabbitMQ](https://www.rabbitmq.com/) em funcionamento
- Storage Node acessível (via HTTP)
- Variáveis de ambiente:
  - `RABBITMQ_URL`: URL de ligação ao RabbitMQ (ex: `amqp://guest:guest@rabbitmq:5672/`)
  - `NODE_URL`: URL base do Storage Node (ex: `http://envoy:8080`)

## Instalação

```bash
git clone <repositório>
cd <diretório>
pip install -r requirements.txt
```

## Configuração

Defina as variáveis de ambiente antes de arrancar a aplicação:

```bash
export RABBITMQ_URL="amqp://guest:guest@rabbitmq:5672/"
export NODE_URL="http://envoy:8080"
```

## Endpoints

### Health Check

```http
GET /health
```

- **Descrição:** Verifica se o serviço está operacional.
- **Resposta 200 OK:**
  ```json
  { "status": "ok" }
  ```

### PUT /store

```http
PUT /store
Content-Type: application/json
```

- **Descrição:** Enfileira um pedido de escrita (PUT) no RabbitMQ.
- **Corpo (application/json):**
  ```json
  {
    "data": {
      "key": "username",
      "value": "alice"
    }
  }
  ```
- **Resposta 202 Accepted:**
  ```json
  { "status": "queued" }
  ```

### GET /store

```http
GET /store?key={key}
```

- **Descrição:** Obtém o valor associado à chave no Storage Node.
- **Parâmetros:**
  - `key` (string, obrigatório): chave a recuperar.
- **Resposta 200 OK:**
  ```json
  { "data": { "value": "alice" } }
  ```

### DELETE /store

```http
DELETE /store?key={key}
```

- **Descrição:** Enfileira um pedido de eliminação (DELETE) no RabbitMQ.
- **Parâmetros:**
  - `key` (string, obrigatório): chave a eliminar.
- **Resposta 202 Accepted:**
  ```json
  { "status": "queued" }
  ```

## Exemplos curl.exe

```bash
# Health Check
curl.exe -X GET "http://localhost:8000/health"

# Enfileirar PUT
curl.exe -X PUT "http://localhost:8000/store" ^
  -H "Content-Type: application/json" ^
  -d "{"data":{"key":"username","value":"alice"}}"

# Obter valor
curl.exe -X GET "http://localhost:8000/store?key=username"

# Enfileirar DELETE
curl.exe -X DELETE "http://localhost:8000/store?key=username"
```

## Códigos de Erro (4xx)

- **400 Bad Request:** Parâmetro em falta ou formato inválido.
- **404 Not Found:** Chave não encontrada no Storage Node (GET /store).
- **422 Unprocessable Entity:** Falha na validação do corpo JSON.
- **502 Bad Gateway:** Erro ao contactar o Storage Node para leitura.

