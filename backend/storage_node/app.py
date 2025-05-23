from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import os, time, redis
from sqlalchemy import (
    create_engine, Table, Column, String, MetaData, select, text
)
from sqlalchemy.exc import OperationalError
from sqlalchemy.dialects.postgresql import insert

# … imports inalterados …
from redis.sentinel import Sentinel        # << NOVO

# ───────────────────────────── ENV ──────────────────────────────
# deixamos REDIS_URL como fallback, mas passamos a usar REDIS_SENTINELS
REDIS_SENTINELS = os.getenv(
    "REDIS_SENTINELS",
    "sentinel-1:26379,sentinel-2:26379,sentinel-3:26379",
).split(",")

CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))
COCKROACH_URL = os.getenv(
    "COCKROACH_URL",
    "cockroachdb://root@cockroachdb:26257/defaultdb?sslmode=disable",
)

# ───────────────────────── REDIS / SQL ─────────────────────────
sentinel_nodes = [tuple(host.split(":")) for host in REDIS_SENTINELS]
sentinel = Sentinel(sentinel_nodes, socket_timeout=0.2, decode_responses=True)

# liga-se sempre ao master ativo (mymaster → definido em sentinel.conf)
redis_client = sentinel.master_for("mymaster",
                                   socket_timeout=0.2,
                                   decode_responses=True)

engine = create_engine(COCKROACH_URL, connect_args={"sslmode": "disable"})
# … resto do ficheiro permanece igual …

metadata = MetaData()
kv_table = Table(
    "kv_store", metadata,
    Column("key", String, primary_key=True),
    Column("value", String, nullable=False),
    Column("updated_at", String, nullable=False,
           server_default=text("'1970-01-01T00:00:00Z'"))  # fallback
)

# ─────────────────────── Retry à BD ────────────────────────────
for attempt in range(1, 11):
    try:
        with engine.connect():
            print(f"[node1] CockroachDB OK na tentativa {attempt}")
            break
    except OperationalError:
        print(f"[node1] BD indisponível ({attempt}/10)… a dormir 2 s")
        time.sleep(2)
else:
    raise RuntimeError("CockroachDB nunca respondeu")

# ─────────────────────── FASTAPI APP ───────────────────────────
app = FastAPI(title="Storage Node")

# 2️⃣  –––––––––  Retry & schema só no startup  –––––––––
@app.on_event("startup")
def startup():
    """Liga ao Cockroach com retry e cria a tabela se faltar."""
    for attempt in range(1, 11):
        try:
            with engine.connect():
                print(f"[node1] CockroachDB OK na tentativa {attempt}")
                break
        except OperationalError:
            print(f"[node1] BD indisponível ({attempt}/10)… a dormir 2 s")
            time.sleep(2)
    else:
        raise RuntimeError("CockroachDB nunca respondeu")

    metadata.create_all(engine)
    print("[node1] Tabela kv_store pronta")

# ─────────────── MODELOS Pydantic ────────────────
class KVRequest(BaseModel):
    data: dict = Field(..., example={"key": "user", "value": "alice"})

class KVResponse(BaseModel):
    data: dict

class KeysResponse(BaseModel):
    keys: list[str]

class StatusResponse(BaseModel):
    status: str

# ─────────────── ENDPOINTS ────────────────
@app.put("/store", response_model=StatusResponse, status_code=201)
def put_kv(item: KVRequest):
    key, value = item.data["key"], item.data["value"]
    ts = datetime.now(timezone.utc).isoformat()

    stmt = (insert(kv_table)
            .values(key=key, value=value, updated_at=ts)
            .on_conflict_do_update(
                index_elements=["key"],
                set_={"value": value, "updated_at": ts}
            ))

    with engine.begin() as conn:
        conn.execute(stmt)

    redis_client.delete(key)          # invalida cache
    return {"status": "stored"}

@app.get("/store", response_model=KVResponse)
def get_kv(key: str):
    if (val := redis_client.get(key)) is not None:
        return JSONResponse(
            content={"data": {"value": val}, "message": "⚡ cache hit"}
        )

    try:
        with engine.connect() as conn:
            row = conn.execute(select(kv_table.c.value)
                               .where(kv_table.c.key == key)).first()
    except OperationalError:
        raise HTTPException(503, "DB indisponível")

    if not row:
        raise HTTPException(404, "Key not found")

    redis_client.setex(key, CACHE_TTL, row.value)
    return {"data": {"value": row.value}}

@app.delete("/store", status_code=204)
def delete_kv(key: str):
    with engine.begin() as conn:
        conn.execute(kv_table.delete().where(kv_table.c.key == key))
    redis_client.delete(key)

@app.get("/store/all", response_model=KeysResponse)
def list_keys():
    with engine.connect() as conn:
        keys = [r.key for r in conn.execute(select(kv_table.c.key))]
    return {"keys": keys}

@app.get("/health", tags=["health"])
async def health_check():
    """
    Health check endpoint para integração com Envoy.
    Devolve 200 OK se a aplicação estiver a correr.
    """
    return {"status": "ok"}

@app.get("/whoami")
async def whoami():
    return {"host": os.getenv("HOSTNAME", "unknown")}