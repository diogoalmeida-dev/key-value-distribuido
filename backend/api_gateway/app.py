from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
import os
import json
import httpx
import aio_pika
from aio_pika import Message, DeliveryMode
from datetime import datetime, timezone
from typing import Any, List

# ——————————————————————————————
# Configurações de ambiente
# ——————————————————————————————
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
QUEUE_NAME   = "kv_requests"
NODE_URL     = os.getenv("NODE_URL", "http://envoy:8080")
INTERNAL_HEADERS = {"Host": "storage.internal"}

# ────────────────────────────────
#  Utilitários de publicação RabbitMQ
# ────────────────────────────────
async def _publish_raw(payload: dict[str, Any]) -> None:
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    async with connection:
        channel = await connection.channel(publisher_confirms=True)
        await channel.declare_queue(
            QUEUE_NAME,
            durable=True,
            arguments={"x-queue-type": "quorum"},
        )
        message = Message(
            body=json.dumps(payload).encode(),
            delivery_mode=DeliveryMode.PERSISTENT,
        )
        await channel.default_exchange.publish(
            message, routing_key=QUEUE_NAME, mandatory=True
        )

async def publish_cmd(cmd: str, key: str, value: str | None = None):
    payload = {
        "cmd": cmd,
        "key": key,
        "value": value,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    await _publish_raw(payload)

# ────────────────────────────────
#  Modelos Pydantic
# ────────────────────────────────
class KVRequest(BaseModel):
    data: dict[str, str] = Field(
        ...,
        example={"key": "username", "value": "alice"},
        description="Par chave/valor a armazenar",
    )

class StatusResponse(BaseModel):
    status: str = Field(..., example="queued")

class KVResponse(BaseModel):
    data: dict[str, str] = Field(
        ..., example={"value": "alice"}, description="Valor obtido"
    )

class KeysResponse(BaseModel):
    keys: List[str] = Field(..., example=["username", "email"])

class RedisKeysResponse(BaseModel):
    master: str
    keys: List[str]

# ────────────────────────────────
#  FastAPI App
# ────────────────────────────────
app = FastAPI(
    title="API Gateway",
    version="0.1.0",
    description="""
Gateway que enfileira alterações no RabbitMQ (quorum queue) e reencaminha leituras
para o Storage Node, incluindo um endpoint para listar todas as chaves e o master activo.
""",
    openapi_tags=[
        {"name": "health", "description": "Estado do Gateway"},
        {"name": "gateway", "description": "Operações chave-valor"},
    ],
)

# ───────  PUT (escrita)  ───────
@app.put(
    "/store",
    tags=["gateway"],
    summary="Enfileia PUT",
    response_model=StatusResponse,
    status_code=202,
)
async def enqueue_put(item: KVRequest) -> StatusResponse:
    key = item.data["key"]
    value = item.data["value"]
    await publish_cmd("put", key, value)
    return StatusResponse(status="queued")

@app.get("/health", status_code=status.HTTP_200_OK)
def healthcheck():
    return {"status": "ok"}

# ───────  GET (leitura por chave)  ───────
@app.get(
    "/store",
    tags=["gateway"],
    summary="Obter valor por chave",
    response_model=KVResponse
)
async def get_item(key: str) -> KVResponse:
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{NODE_URL}/store",
            params={"key": key},
            headers=INTERNAL_HEADERS
        )
    if r.status_code != 200:
        raise HTTPException(r.status_code, r.text)
    return KVResponse(**r.json())

# ───────  DELETE (escrita)  ───────
@app.delete(
    "/store",
    tags=["gateway"],
    summary="Enfileia DELETE",
    response_model=StatusResponse,
    status_code=202,
)
async def enqueue_delete(key: str) -> StatusResponse:
    await publish_cmd("del", key)
    return StatusResponse(status="queued")
