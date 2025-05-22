# worker.py  ─────────────────────────────────────────────────────────
import os, json, asyncio
from datetime import datetime, timezone

import redis, aio_pika
from aio_pika import IncomingMessage
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app import engine, redis_client   # importa CACHE_TTL se quiseres reaproveitar

RABBIT = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
QUEUE  = "kv_requests"

# SQL para last-write-wins
UPSERT_LWW = text("""
INSERT INTO kv_store (key, value, updated_at)
VALUES (:k, :v, :ts)
ON CONFLICT (key) DO UPDATE
SET    value      = EXCLUDED.value,
       updated_at = EXCLUDED.updated_at
WHERE  kv_store.updated_at < EXCLUDED.updated_at
""")

DELETE_SQL = text("DELETE FROM kv_store WHERE key = :k")

# ----- helpers ------------------------------------------------------
async def upsert(key, value, ts):
    with engine.begin() as c:
        c.execute(UPSERT_LWW, {"k": key, "v": value, "ts": ts})
    redis_client.delete(key)

async def delete(key, ts):
    with engine.begin() as c:
        c.execute(DELETE_SQL, {"k": key})
    redis_client.delete(key)

# ----- callback -----------------------------------------------------
async def handle(msg: IncomingMessage):
    async with msg.process(requeue=True):
        data = json.loads(msg.body)
        cmd  = data.get("cmd", "put")
        key  = data["key"]
        ts   = data.get("ts") or datetime.now(timezone.utc).isoformat()

        if cmd == "put":
            value = data.get("value")
            if value is None:
                print("[worker] PUT sem value ⇒ descarta", flush=True)
                return
            await upsert(key, value, ts)
            print(f"[worker] PUT  {key}={value}", flush=True)

        elif cmd == "del":
            await delete(key, ts)
            print(f"[worker] DEL  {key}", flush=True)

        else:
            print(f"[worker] cmd desconhecido '{cmd}' ⇒ descarta", flush=True)


# ----- main ---------------------------------------------------------
async def main():
    conn = await aio_pika.connect_robust(RABBIT)
    async with conn:
        ch = await conn.channel()
        await ch.set_qos(prefetch_count=1)
        q  = await ch.declare_queue(
                 QUEUE, durable=True,
                 arguments={"x-queue-type": "quorum"})
        print("[worker] a escutar a fila…")
        await q.consume(handle)
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())