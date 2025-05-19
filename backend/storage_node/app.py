from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

class KV(BaseModel):
    data: dict  # { "key": "...", "value": "..." }

app = FastAPI(title="Storage Node", version="0.1.0")
STORE: dict[str, str] = {}     # MVP: memória; depois troca-se por SQLite

@app.get("/health")
def health():
    return {"status": "ok"}

@app.put("/store", status_code=201)
def put_kv(item: KV):
    key = item.data["key"]
    STORE[key] = item.data["value"]
    return {"status": "stored"}

@app.get("/store")
def get_kv(key: str):
    if key not in STORE:
        raise HTTPException(404, "Key not found")
    return {"data": {"value": STORE[key]}}

@app.delete("/store", status_code=204)
def del_kv(key: str):
    STORE.pop(key, None)
    

@app.get("/store/all", summary="Listar todas as keys guardadas")
def list_all_keys():
    return {"keys": list(STORE.keys())}

