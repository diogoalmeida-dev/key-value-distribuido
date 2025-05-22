from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import os
import json
import httpx
import aio_pika
from aio_pika import Message, DeliveryMode
from datetime import datetime, timezone
from typing import Any           #  <<<  adiciona isto


# ——————————————————————————————
# Configurações de ambiente
# ——————————————————————————————
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
QUEUE_NAME = "kv_requests"
NODE_URL = os.getenv("NODE_URL", "http://node1:8000")

# ——————————————————————————————
# Função para publicar na fila
# ——————————————————————————————
# app.py  (gateway)  ────────────────────────────────────────────────
from datetime import datetime, timezone
import aio_pika, json, os
from aio_pika import Message, DeliveryMode

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
QUEUE_NAME   = "kv_requests"


# ────────────────────────────────
#  Utilidades de publicação
# ────────────────────────────────
async def _publish_raw(payload: dict[str, Any]) -> None:
    """
    Publica JSON codificado em UTF-8 na fila quorum `QUEUE_NAME`
    usando *publisher-confirms*.
    """
    # 1) Estabelecer ligação
    connection: aio_pika.RobustConnection = await aio_pika.connect_robust(
        RABBITMQ_URL
    )

    async with connection:
        # 2) Canal com publisher-confirms
        channel: aio_pika.RobustChannel = await connection.channel(
            publisher_confirms=True
        )

        # 3) Garantir que a fila existe (quorum & durável)
        await channel.declare_queue(
            QUEUE_NAME,
            durable=True,
            arguments={"x-queue-type": "quorum"},
        )

        # 4) Publicar mensagem persistente
        message = Message(
            body=json.dumps(payload).encode(),
            delivery_mode=DeliveryMode.PERSISTENT,
        )
        await channel.default_exchange.publish(
            message,
            routing_key=QUEUE_NAME,
            mandatory=True,  # erro imediato se não houver rota/fila
        )


async def publish_cmd(cmd: str, key: str, value: str | None = None) -> None:
    """
    Publica um comando `put` ou `del` com carimbo temporal ISO-8601 UTC.
    """
    payload: dict[str, Any] = {
        "cmd": cmd,  # "put" | "del"
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
    keys: list[str] = Field(..., example=["username", "email"])


# ────────────────────────────────
#  FastAPI
# ────────────────────────────────
app = FastAPI(
    title="API Gateway",
    version="0.1.0",
    description="""
Gateway que **enfileira** alterações no RabbitMQ (quorum queue) e reencaminha leituras
para o Storage Node.
""",
    openapi_tags=[
        {"name": "health", "description": "Estado do Gateway"},
        {"name": "gateway", "description": "Operações chave-valor"},
    ],
)


@app.get("/health", tags=["health"], response_model=dict[str, str])
def health() -> dict[str, str]:
    return {"status": "ok"}


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


# ───────  DELETE (escrita)  ───────
@app.delete(
    "/store",
    tags=["gateway"],
    summary="Enfileia DELETE",
    status_code=202,
    response_model=StatusResponse,
)
async def enqueue_delete(key: str) -> StatusResponse:
    await publish_cmd("del", key)
    return StatusResponse(status="queued")


# ───────  GET (leitura)  ───────
@app.get(
    "/store",
    tags=["gateway"],
    summary="Obter valor por chave",
    response_model=KVResponse,
)
async def get_item(key: str) -> KVResponse:
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{NODE_URL}/store", params={"key": key})
    if r.status_code != 200:
        raise HTTPException(r.status_code, r.text)
    return KVResponse(**r.json())


# ───────  LISTAGEM  ───────
@app.get(
    "/store/all",
    tags=["gateway"],
    summary="Listar todas as chaves",
    response_model=KeysResponse,
)
async def list_all_keys() -> KeysResponse:
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{NODE_URL}/store/all")
    if r.status_code != 200:
        raise HTTPException(r.status_code, r.text)
    return KeysResponse(**r.json())