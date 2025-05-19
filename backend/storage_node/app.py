from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

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

app = FastAPI(
    title="Storage Node",
    version="0.1.0",
    description="""
API para armazenar pares chave-valor em memória (MVP).  
Endpoints:
- `/health`: verifica estado do serviço.  
- `/store`: criar, obter e eliminar valores por chave.  
- `/store/all`: listar todas as chaves.
""",
    openapi_tags=[
        {"name": "health", "description": "Verificação de estado do serviço"},
        {"name": "store", "description": "Operações CRUD sobre pares chave-valor"},
    ],
)

STORE: dict[str, str] = {}  # MVP em memória; depois troca-se por SQLite

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
    description="Recebe um objeto com `key` e `value` e guarda na store.",
    response_model=StatusResponse,
    status_code=201
)
def put_kv(item: KVRequest):
    """
    Armazena o valor recebido associado à chave fornecida.
    """
    key = item.data["key"]
    STORE[key] = item.data["value"]
    return {"status": "stored"}

@app.get(
    "/store",
    tags=["store"],
    summary="Obter valor por chave",
    description="Recebe um parâmetro de query `key` e retorna o valor associado.",
    response_model=KVResponse,
    responses={
        200: {"description": "Valor encontrado"},
        404: {"description": "Chave não encontrada"}
    }
)
def get_kv(key: str):
    """
    Retorna o valor associado à chave, ou 404 se não existir.
    """
    if key not in STORE:
        raise HTTPException(404, "Key not found")
    return {"data": {"value": STORE[key]}}

@app.delete(
    "/store",
    tags=["store"],
    summary="Eliminar valor por chave",
    description="Recebe um parâmetro de query `key` e elimina o par correspondente.",
    status_code=204,
    responses={204: {"description": "Eliminação bem-sucedida"}}
)
def del_kv(key: str):
    """
    Remove a chave e o valor associado da store.
    """
    STORE.pop(key, None)

@app.get(
    "/store/all",
    tags=["store"],
    summary="Listar todas as chaves guardadas",
    description="Devolve uma lista com todas as chaves atualmente armazenadas.",
    response_model=KeysResponse
)
def list_all_keys():
    """
    Lista todas as chaves presentes na store.
    """
    return {"keys": list(STORE.keys())}