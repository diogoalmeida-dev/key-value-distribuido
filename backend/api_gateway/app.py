from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import os
import json
import httpx
import aio_pika
from aio_pika import Message, DeliveryMode

# ——————————————————————————————
# Configurações de ambiente
# ——————————————————————————————
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
QUEUE_NAME = "kv_requests"
NODE_URL = os.getenv("NODE_URL", "http://node1:8000")

# ——————————————————————————————
# Função para publicar na fila
# ——————————————————————————————
async def publish_kv(data: dict):
    conn = await aio_pika.connect_robust(RABBITMQ_URL)
    async with conn:
        ch = await conn.channel()
        await ch.declare_queue(QUEUE_NAME, durable=True)
        msg = Message(
            body=json.dumps(data).encode(),
            delivery_mode=DeliveryMode.PERSISTENT
        )
        await ch.default_exchange.publish(msg, routing_key=QUEUE_NAME)

# ——————————————————————————————
# Modelos Pydantic
# ——————————————————————————————
class KVRequest(BaseModel):
    data: dict = Field(
        ...,
        example={"key": "username", "value": "alice"},
        description="Dicionário com a chave e o valor a armazenar"
    )

class StatusResponse(BaseModel):
    status: str = Field(..., example="queued", description="Estado da operação")

class KVResponse(BaseModel):
    data: dict = Field(
        ...,
        example={"value": "alice"},
        description="Dicionário com o valor associado à chave"
    )

class KeysResponse(BaseModel):
    keys: list[str] = Field(
        ...,
        example=["username", "email"],
        description="Lista de todas as chaves armazenadas"
    )

# ——————————————————————————————
# Instância FastAPI
# ——————————————————————————————
app = FastAPI(
    title="API Gateway",
    version="0.1.0",
    description="""
Gateway para enfileirar escritas via RabbitMQ e encaminhar leituras ao Storage Node.  
Endpoints:
- `/health`: verifica estado do Gateway.  
- `/store` (PUT): coloca um pedido de escrita na fila.  
- `/store` (GET): lê valor por chave do Storage Node.  
- `/store` (DELETE): remove valor por chave no Storage Node.  
- `/store/all`: lista todas as chaves no Storage Node.
""",
    openapi_tags=[
        {"name": "health", "description": "Verificação de estado do Gateway"},
        {"name": "gateway", "description": "Operações de enfileiramento e leitura"}
    ],
)

@app.get(
    "/health",
    tags=["health"],
    summary="Verificar estado do Gateway",
    response_model=dict[str, str]
)
def health():
    return {"status": "ok"}

@app.put(
    "/store",
    tags=["gateway"],
    summary="Enfileirar par chave-valor",
    description="Publica uma mensagem na fila RabbitMQ com o par chave-valor.",
    response_model=StatusResponse,
    status_code=202
)
async def enqueue_store(item: KVRequest):
    await publish_kv(item.data)
    return {"status": "queued"}

@app.get(
    "/store",
    tags=["gateway"],
    summary="Obter valor por chave",
    description="Encaminha pedido GET para o Storage Node.",
    response_model=KVResponse,
    responses={404: {"description": "Chave não encontrada"}}
)
async def get_item(key: str):
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{NODE_URL}/store", params={"key": key})
    if r.status_code != 200:
        raise HTTPException(r.status_code, r.text)
    return r.json()

@app.delete(
    "/store",
    tags=["gateway"],
    summary="Eliminar valor por chave",
    description="Encaminha pedido DELETE para o Storage Node.",
    status_code=204
)
async def delete_item(key: str):
    async with httpx.AsyncClient() as client:
        r = await client.delete(f"{NODE_URL}/store", params={"key": key})
    if r.status_code != 204:
        raise HTTPException(r.status_code, r.text)

@app.get(
    "/store/all",
    tags=["gateway"],
    summary="Listar todas as chaves",
    description="Encaminha pedido GET `/store/all` para o Storage Node.",
    response_model=KeysResponse
)
async def list_all_keys():
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{NODE_URL}/store/all")
    if r.status_code != 200:
        raise HTTPException(r.status_code, r.text)
    return r.json()
