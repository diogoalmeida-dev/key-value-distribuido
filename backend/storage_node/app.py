from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import os
import redis
from sqlalchemy import create_engine, Table, Column, String, MetaData, select

# Pydantic models
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

# Configurações de ambiente
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))  # segundos

# URL de conexão ao CockroachDB (via SQLAlchemy)
# Exemplo: cockroachdb://<user>:<pass>@<host>:<port>/<database>?sslmode=require
COCKROACH_URL = os.getenv("COCKROACH_URL", "cockroachdb://root@cockroach:26257/defaultdb?sslmode=disable")

# Inicialização do Redis
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

# Inicialização do CockroachDB com SQLAlchemy
engine = create_engine(COCKROACH_URL, connect_args={"sslmode": "require"})
metadata = MetaData()
kv_table = Table(
    "kv_store", metadata,
    Column("key", String, primary_key=True),
    Column("value", String, nullable=False)
)
metadata.create_all(engine)

# Instância FastAPI
app = FastAPI(
    title="Storage Node com Redis e CockroachDB (Cache-Aside)",
    version="0.1.0",
    description="""
API para armazenar pares chave-valor utilizando Redis como cache e CockroachDB como armazenamento persistente.

EndPoints:
- `/health`: verifica disponibilidade do serviço.
- `/store`: operações CRUD para pares chave-valor.
- `/store/all`: lista todas as chaves armazenadas.
""",
    openapi_tags=[
        {"name": "health", "description": "Verificação de estado do serviço"},
        {"name": "store", "description": "Operações CRUD sobre pares chave-valor"},
    ],
)

@app.get(
    "/health",
    tags=["health"],
    summary="Verificar estado do serviço",
    response_model=dict[str, str],
    responses={200: {"description": "Serviço ativo"}}
)
def health():
    """
    Retorna o estado atual do serviço.
    """
    return {"status": "ok"}

@app.put(
    "/store",
    tags=["store"],
    summary="Armazenar um par chave-valor",
    description="Grava o par chave-valor no CockroachDB (sem tocar na cache).",
    response_model=StatusResponse,
    status_code=201
)
def put_kv(item: KVRequest):
    """
    Armazena o valor recebido associado à chave no CockroachDB,
    sem escrever imediatamente na cache Redis.
    """
    key = item.data["key"]
    value = item.data["value"]
    # Persistência no CockroachDB
    with engine.begin() as conn:
        conn.execute(
            kv_table.insert().values(key=key, value=value)
            .prefix_with("ON CONFLICT (key) DO UPDATE")
        )
    return {"status": "stored"}

@app.get(
    "/store",
    tags=["store"],
    summary="Obter valor por chave",
    description="Tenta obter do Redis, e se faltar, busca no CockroachDB e popula a cache.",
    response_model=KVResponse,
    responses={
        200: {"description": "Valor encontrado"},
        404: {"description": "Chave não encontrada"}
    }
)
def get_kv(key: str):
    """
    Retorna o valor associado à chave.
    """
    # Tentar cache
    value = redis_client.get(key)
    if value is not None:
        return JSONResponse(
            status_code=200,
            content={"data": {"value": value}, "message": f"⚡ Cache hit para a chave '{key}'"}
        )

    # Cache miss: buscar no CockroachDB
    with engine.connect() as conn:
        row = conn.execute(
            select(kv_table.c.value).where(kv_table.c.key == key)
        ).first()
    if not row:
        raise HTTPException(404, "Key not found")

    value = row[0]
    # Popula a cache
    redis_client.setex(key, CACHE_TTL, value)
    return {"data": {"value": value}}

@app.delete(
    "/store",
    tags=["store"],
    summary="Eliminar valor por chave",
    description="Remove do CockroachDB e da cache Redis.",
    status_code=204,
    responses={204: {"description": "Eliminação bem-sucedida"}}
)
def del_kv(key: str):
    """
    Remove a chave e o valor associado.
    """
    # Remover do CockroachDB
    with engine.begin() as conn:
        conn.execute(kv_table.delete().where(kv_table.c.key == key))
    # Remover da cache
    redis_client.delete(key)

@app.get(
    "/store/all",
    tags=["store"],
    summary="Listar todas as chaves guardadas",
    description="Devolve lista de todas as chaves armazenadas.",
    response_model=KeysResponse
)
def list_all_keys():
    """
    Lista todas as chaves presentes no CockroachDB.
    """
    with engine.connect() as conn:
        keys = [row[0] for row in conn.execute(select(kv_table.c.key))]
    return {"keys": keys}