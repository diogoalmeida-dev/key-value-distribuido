from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx, os

NODE_URL = os.getenv("NODE_URL", "http://node1:8000")

class KV(BaseModel):
    data: dict  # { "key": "...", "value": "..." }

app = FastAPI(title="API Gateway", version="0.1.0")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.put("/store", status_code=201)
async def put_item(item: KV):
    async with httpx.AsyncClient() as client:
        r = await client.put(f"{NODE_URL}/store", json=item.dict())
    if r.status_code != 201:
        raise HTTPException(r.status_code, r.text)
    return {"status": "stored"}

@app.get("/store")
async def get_item(key: str):
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{NODE_URL}/store", params={"key": key})
    if r.status_code != 200:
        raise HTTPException(r.status_code, r.text)
    return r.json()

@app.delete("/store", status_code=204)
async def delete_item(key: str):
    async with httpx.AsyncClient() as client:
        r = await client.delete(f"{NODE_URL}/store", params={"key": key})
    if r.status_code != 204:
        raise HTTPException(r.status_code, r.text)
    
@app.get("/store/all", summary="Listar todas as keys guardadas (via Gateway)")
async def list_all_keys_gateway():
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{NODE_URL}/store/all")
    if r.status_code != 200:
        raise HTTPException(r.status_code, r.text)
    return r.json()
