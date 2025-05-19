# Manual da API REST

Este manual explica como aceder e utilizar a API REST do sistema distribuído de armazenamento key-value, aproveitando o **Swagger UI** do **FastAPI** e exemplos de comandos em linha de comando.

---

## ÍNDICE

1. [Aceder ao Swagger UI](#1-aceder-ao-swagger-ui)
2. [Utilização via Swagger UI](#2-utilização-via-swagger-ui)

   * 2.1 [Inserir (PUT)](#21-inserir-put)
   * 2.2 [Consultar (GET)](#22-consultar-get)
   * 2.3 [Eliminar (DELETE)](#23-eliminar-delete)
   * 2.4 [Listar todas as chaves (GET /store/all)](#24-listar-todas-as-chaves-get-storeall)
3. [Exportar especificação OpenAPI](#3-exportar-especificação-openapi)
4. [Exemplos em linha de comando](#4-exemplos-em-linha-de-comando)

   * 4.1 [Usando curl (Git Bash / Linux)](#41-usando-curl-git-bash--linux)
   * 4.2 [Usando PowerShell (Windows)](#42-usando-powershell-windows)

---

## 1. Aceder ao Swagger UI

1. Assegura-te de que os serviços estão ativos:

   ```bash
   # Linux / WSL 2
   ./start.sh

   # Windows PowerShell
   .\start.ps1
   ```
2. Abre o browser e navega para:

   ```
   http://localhost:8000/docs
   ```
3. Vais encontrar a interface interactiva com todos os endpoints disponíveis:

   * **PUT /store**
   * **GET /store**
   * **DELETE /store**
   * **GET /store/all**
   * **GET /health**

> O Swagger UI mostra definições de rota, parâmetros, exemplos de payload e permite usar **Try it out** para testar diretamente no browser.

## 2. Utilização via Swagger UI

### 2.1 Inserir (PUT)

1. Expande o endpoint **PUT /store**.
2. Clica em **Try it out**.
3. No campo de request, substitui o exemplo por:

   ```json
   {
     "data": { "key": "foo", "value": "bar" }
   }
   ```
4. Clica em **Execute**.
5. Confirma que o **Status Code** é `201 Created` e o **Response Body** mostra:

   ```json
   { "status": "stored" }
   ```

### 2.2 Consultar (GET)

1. Expande o endpoint **GET /store**.
2. Clica em **Try it out**.
3. No campo `key`, insere `foo`.
4. Clica em **Execute**.
5. Verifica a resposta:

   ```json
   { "data": { "value": "bar" } }
   ```

### 2.3 Eliminar (DELETE)

1. Expande o endpoint **DELETE /store**.
2. Clica em **Try it out**.
3. No campo `key`, insere `foo`.
4. Clica em **Execute**.
5. O **Status Code** deve ser `204 No Content`.

### 2.4 Listar todas as chaves (GET /store/all)

1. Expande o endpoint **GET /store/all**.
2. Clica em **Try it out** e depois em **Execute**.
3. A resposta exibe todas as keys armazenadas:

   ```json
   { "keys": ["foo"] }
   ```

## 3. Exportar especificação OpenAPI

Para integrar com outras ferramentas ou gerar SDKs:

1. Acede a:

   ```
   http://localhost:8000/openapi.json
   ```
2. Guarda o conteúdo em `docs/openapi.json` no repositório.

## 4. Exemplos em linha de comando

Para complementar a interface Web, podes usar **curl** ou **Invoke-RestMethod**.

### 4.1 Usando curl (Git Bash / Linux)

```bash
# Inserir par key-value
echo "Inserir 'foo':'bar'"
curl -X PUT "http://localhost:8000/store" \
     -H "Content-Type: application/json" \
     -d '{"data":{"key":"foo","value":"bar"}}'

# Consultar valor
curl "http://localhost:8000/store?key=foo"

# Eliminar par
curl -X DELETE "http://localhost:8000/store?key=foo"

# Listar todas as chaves
curl "http://localhost:8000/store/all"
```

### 4.2 Usando PowerShell (Windows)

```powershell
# Inserir par key-value
Invoke-RestMethod -Method PUT -Uri "http://localhost:8000/store" \
  -Headers @{ "Content-Type" = "application/json" } \
  -Body '{"data":{"key":"foo","value":"bar"}}'

# Consultar valor
Invoke-RestMethod -Method GET -Uri "http://localhost:8000/store?key=foo"

# Eliminar par
Invoke-RestMethod -Method DELETE -Uri "http://localhost:8000/store?key=foo"

# Listar todas as chaves
Invoke-RestMethod -Method GET -Uri "http://localhost:8000/store/all"
```
