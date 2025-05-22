import os
import json
import time
import asyncio
import redis
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.dialects.postgresql import insert
import aio_pika

from app import engine, kv_table, redis_client, CACHE_TTL  # assumindo que APP expõe estas vars

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
QUEUE_NAME = "kv_requests"

# --- Retry para RabbitMQ ---
async def get_rabbit_connection(max_retries=10, delay=2):
    for attempt in range(1, max_retries + 1):
        try:
            return await aio_pika.connect_robust(RABBITMQ_URL)
        except Exception as e:
            print(f"[worker] RabbitMQ não disponível ({attempt}/{max_retries}), aguardar {delay}s…")
            await asyncio.sleep(delay)
    raise RuntimeError("Falha ao ligar ao RabbitMQ após vários intentos")

async def handle_message(msg: aio_pika.IncomingMessage):
    async with msg.process():
        data = json.loads(msg.body)
        key, value = data["key"], data["value"]
        print(f"[worker] Processando mensagem {{'key':'{key}','value':'{value}'}}")

        # 1) Persistência com upsert
        try:
            with engine.begin() as conn:
                stmt = insert(kv_table).values(key=key, value=value)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["key"],
                    set_={"value": stmt.excluded.value}
                )
                conn.execute(stmt)
        except OperationalError:
            print(f"[worker] Erro BD, devolver mensagem à fila")
            raise  # nack automático para retry

        # 2) Invalidação da cache
        redis_client.delete(key)
        print(f"[worker] Persistido e cache invalidado para '{key}'")

async def main():
    # 1) Esperar RabbitMQ
    conn = await get_rabbit_connection()
    async with conn:
        ch = await conn.channel()
        queue = await ch.declare_queue(QUEUE_NAME, durable=True)
        print("[worker] A escutar a fila…")
        await queue.consume(handle_message, no_ack=False)
        await asyncio.Future()  # fica a correr para sempre

if __name__ == "__main__":
    asyncio.run(main())