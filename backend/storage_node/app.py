from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import os
import time
import redis
from sqlalchemy import create_engine, Table, Column, String, MetaData, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.dialects.postgresql import insert

# ——————————————————————————————
# 1) Configurações de ambiente (uma só vez)
# ——————————————————————————————
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))
COCKROACH_URL = os.getenv(
    "COCKROACH_URL",
    "cockroachdb://root@cockroachdb:26257/defaultdb?sslmode=disable"
)

# ——————————————————————————————
# 2) Inicialização de clientes e engine
# ——————————————————————————————
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

engine = create_engine(
    COCKROACH_URL,
    connect_args={"sslmode": "disable"}
)

metadata = MetaData()
kv_table = Table(
    "kv_store", metadata,
    Column("key", String, primary_key=True),
    Column("value", String, nullable=False)
)

# ——————————————————————————————
# 3) Retry loop para a BD
# ——————————————————————————————
max_retries = 10
for attempt in range(1, max_retries + 1):
    try:
        with engine.connect():
            print(f"[node1] Ligação ao CockroachDB no intento {attempt} bem-sucedida")
            break
    except OperationalError:
        print(f"[node1] CockroachDB não disponível ({attempt}/{max_retries}), a aguardar 2s…")
        time.sleep(2)
else:
    raise RuntimeError("Falha ao ligar ao CockroachDB após vários intentos")

# ——————————————————————————————
# 4) Instância FastAPI
# ——————————————————————————————
app = FastAPI(
    title="Storage Node com Redis e CockroachDB",
    version="0.1.0",
    description="Cache-aside com Redis e CockroachDB",
)

# ——————————————————————————————
# 5) Criar o schema no startup
# ——————————————————————————————
@app.on_event("startup")
def on_startup():
    metadata.create_all(engine)
    print("[node1] Tabelas criadas ou confirmadas no CockroachDB")

# ——————————————————————————————
# 6) Modelos Pydantic
# ——————————————————————————————
class KVRequest(BaseModel):
    data: dict = Field(
        ...,
        example={"key": "username", "value": "alice"},
        description="Dicionário com a chave e o valor a armazenar"
    )

class StatusResponse(BaseModel):
    status: str = Field(..., example="stored", description="Estado da operação")

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
# 7) Endpoints
# ——————————————————————————————
@app.get("/health", response_model=dict[str, str])
def health():
    return {"status": "ok"}

@app.put(
    "/store",
    tags=["store"],
    summary="Armazenar um par chave-valor",
    description="Upsert no CockroachDB com conflito tratado no SQL.",
    response_model=StatusResponse,
    status_code=201
)
def put_kv(item: KVRequest):
    key = item.data["key"]
    value = item.data["value"]

    stmt = insert(kv_table).values(key=key, value=value)
    stmt = stmt.on_conflict_do_update(
        index_elements=["key"],
        set_={"value": stmt.excluded.value}
    )
    with engine.begin() as conn:
        conn.execute(stmt)
    return {"status": "stored"}

@app.get(
    "/store",
    tags=["store"],
    summary="Obter valor por chave",
    description="Cache-aside: tenta Redis e, em cache miss, CockroachDB.",
    response_model=KVResponse,
    responses={404: {"description": "Chave não encontrada"}, 503: {"description": "Serviço indisponível"}}
)
def get_kv(key: str):
    # 1) Cache
    val = redis_client.get(key)
    if val is not None:
        return JSONResponse(
            status_code=200,
            content={"data": {"value": val}, "message": f"⚡ Cache hit para '{key}'"}
        )

    # 2) DB
    try:
        with engine.connect() as conn:
            row = conn.execute(
                select(kv_table.c.value).where(kv_table.c.key == key)
            ).first()
    except OperationalError:
        raise HTTPException(503, "Serviço de armazenamento indisponível")

    if not row:
        raise HTTPException(404, "Key not found")

    # 3) Popula cache
    redis_client.setex(key, CACHE_TTL, row[0])
    return {"data": {"value": row[0]}}

@app.delete(
    "/store",
    tags=["store"],
    summary="Eliminar valor por chave",
    description="Remove do CockroachDB e da cache Redis.",
    status_code=204
)
def del_kv(key: str):
    with engine.begin() as conn:
        conn.execute(kv_table.delete().where(kv_table.c.key == key))
    redis_client.delete(key)

@app.get(
    "/store/all",
    tags=["store"],
    summary="Listar todas as chaves guardadas",
    description="Devolve lista de todas as chaves armazenadas.",
    response_model=KeysResponse
)
def list_all_keys():
    with engine.connect() as conn:
        keys = [row[0] for row in conn.execute(select(kv_table.c.key))]
    return {"keys": keys}
