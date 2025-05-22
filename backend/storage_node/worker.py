import os
import json
import asyncio
from datetime import datetime, timezone
from collections import defaultdict, deque

import redis
import aio_pika
from aio_pika import IncomingMessage
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

# Estes objetos vêm do app.py (storage_node)
from app import engine, kv_table, redis_client, CACHE_TTL

# ------------------------------------------------------------------
# Configuração
# ------------------------------------------------------------------
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
QUEUE_NAME   = os.getenv("QUEUE_NAME",   "kv_requests")
MAX_RETRIES  = 10
RETRY_DELAY  = 2

# ------------------------------------------------------------------
# Estado local para ordenação por chave
# ------------------------------------------------------------------
buffers: dict[str, deque]       = defaultdict(deque)   # chave -> deque de (ts, value)
last_ts_processed: dict[str, str] = {}                 # chave -> ISO ts mais recente

# ------------------------------------------------------------------
# Liga-se ao RabbitMQ com retry
# ------------------------------------------------------------------
async def get_rabbit_connection():
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return await aio_pika.connect_robust(RABBITMQ_URL)
        except Exception:
            print(f"[worker] RabbitMQ não disponível ({attempt}/{MAX_RETRIES}), aguardar {RETRY_DELAY}s…")
            await asyncio.sleep(RETRY_DELAY)
    raise RuntimeError("Falha ao ligar ao RabbitMQ")

# ------------------------------------------------------------------
# UPSERT last-write-wins (timestamp ISO8601)
# ------------------------------------------------------------------
UPSERT_SQL = text("""
INSERT INTO kv_store (key, value, updated_at)
VALUES (:k, :v, :ts)
ON CONFLICT (key) DO UPDATE
SET    value       = EXCLUDED.value,
       updated_at  = EXCLUDED.updated_at
WHERE  kv_store.updated_at < EXCLUDED.updated_at
""")

def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()

# ------------------------------------------------------------------
# Processamento ordenado por chave
# ------------------------------------------------------------------
async def persist_and_cache(key: str, value: str, ts: str):
    """Persiste no CockroachDB se for mais recente e invalida cache."""
    try:
        with engine.begin() as conn:
            conn.execute(UPSERT_SQL, {"k": key, "v": value, "ts": ts})
    except OperationalError:
        print(f"[worker] Erro BD; mensagem será reenfileirada")
        raise             # Faz nack automático

    redis_client.delete(key)      # invalidar cache
    print(f"[worker] Persistido '{key}'@{ts} e cache invalidada")

async def process_buffer(key: str):
    """Processa em ordem crescente de ts todas as mensagens no buffer
    que sejam mais recentes que a última já aplicada."""
    while buffers[key]:
        ts, value = buffers[key][0]        # peek
        last_ts   = last_ts_processed.get(key)
        if last_ts and ts <= last_ts:
            # mensagem antiga / duplicada – descarta
            buffers[key].popleft()
            continue
        # este é o próximo a aplicar
        await persist_and_cache(key, value, ts)
        last_ts_processed[key] = ts
        buffers[key].popleft()

# ------------------------------------------------------------------
# Callback por mensagem
# ------------------------------------------------------------------
async def handle_message(msg: IncomingMessage):
    async with msg.process():             # ack/nack automático
        data = json.loads(msg.body)

        key   = data["key"]
        value = data["value"]
        ts    = data.get("ts") or iso_now()

        print(f"[worker] Recebida msg key='{key}', ts='{ts}'")

        # Adiciona ao buffer da chave e processa
        buffers[key].append((ts, value))
        # Mantém ordem no buffer
        buffers[key] = deque(sorted(buffers[key], key=lambda x: x[0]))
        await process_buffer(key)

# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
async def main():
    conn = await get_rabbit_connection()
    async with conn:
        ch = await conn.channel()
        await ch.set_qos(prefetch_count=1)                   # FIFO estrito por consumer
        await ch.declare_queue(
            QUEUE_NAME,
            durable=True,
            arguments={"x-queue-type": "quorum"}             # segurança extra; remove se não quiseres
        )
        queue = await ch.get_queue(QUEUE_NAME)
        print("[worker] A escutar a fila…")
        await queue.consume(handle_message, no_ack=False)
        await asyncio.Future()  # executa para sempre

if __name__ == "__main__":
    asyncio.run(main())