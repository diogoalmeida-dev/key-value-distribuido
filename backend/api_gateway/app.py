from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import httpx, os

NODE_URL = os.getenv("NODE_URL", "http://node1:8000")

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
    title="API Gateway",
    version="0.1.0",
    description="""
Gateway para encaminhar operações de pares chave-valor ao Storage Node.  
Endpoints:
- `/health`: verifica estado do Gateway.  
- `/store`: criar, obter e eliminar valores por chave.  
- `/store/all`: listar todas as chaves via Gateway.
""",
    openapi_tags=[
        {"name": "health", "description": "Verificação de estado do Gateway"},
        {"name": "gateway", "description": "Encaminhamento de operações ao Storage Node"},
    ],
)

@app.get(
    "/health",
    tags=["health"],
    summary="Verificar estado do Gateway",
    response_model=dict[str, str],
    responses={200: {"description": "Gateway ativo"}}
)
def health():
    """
    Retorna o estado atual do API Gateway.
    """
    return {"status": "ok"}

@app.put(
    "/store",
    tags=["gateway"],
    summary="Armazenar um par chave-valor (via Gateway)",
    description="Encaminha pedido PUT para o Storage Node para guardar o par chave-valor.",
    response_model=StatusResponse,
    status_code=201
)
async def put_item(item: KVRequest):
    """
    Envia o par `key`/`value` ao Storage Node.
    """
    async with httpx.AsyncClient() as client:
        r = await client.put(f"{NODE_URL}/store", json=item.dict())
    if r.status_code != 201:
        raise HTTPException(r.status_code, r.text)
    return {"status": "stored"}

@app.get(
    "/store",
    tags=["gateway"],
    summary="Obter valor por chave (via Gateway)",
    description="Encaminha pedido GET para o Storage Node com parâmetro `key`.",
    response_model=KVResponse,
    responses={
        200: {"description": "Valor encontrado"},
        404: {"description": "Chave não encontrada"}
    }
)
async def get_item(key: str):
    """
    Requisita ao Storage Node o valor associado à chave.
    """
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{NODE_URL}/store", params={"key": key})
    if r.status_code != 200:
        raise HTTPException(r.status_code, r.text)
    return r.json()

@app.delete(
    "/store",
    tags=["gatewayyy"],
    summary="Eliminar valor por chave (via Gateway)",
    description="Encaminha pedido DELETE para o Storage Node com parâmetro `key`.",
    status_code=204,
    responses={204: {"description": "Eliminação bem-sucedida"}}
)
async def delete_item(key: str):
    """
    Envia ao Storage Node pedido para remover a chave.
    """
    async with httpx.AsyncClient() as client:
        r = await client.delete(f"{NODE_URL}/store", params={"key": key})
    if r.status_code != 204:
        raise HTTPException(r.status_code, r.text)

@app.get(
    "/store/all",
    tags=["gateway"],
    summary="Listar todas as chaves (via Gateway)",
    description="Encaminha pedido GET para `/store/all` do Storage Node.",
    response_model=KeysResponse
)
async def list_all_keys_gateway():
    """
    Requisita ao Storage Node a lista de todas as chaves armazenadas.
    """
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{NODE_URL}/store/all")
    if r.status_code != 200:
        raise HTTPException(r.status_code, r.text)
    return r.json()
