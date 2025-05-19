# key-value-distribuido
Sistema distribuído de armazenamento key-value com API REST, tolerância a falhas, escalabilidade automática e execução em microserviços Docker.

## 🧱 Funcionalidades
- Armazenamento distribuído de dados key-value
- Acesso via REST API (PUT, GET, DELETE)
- Balanceamento de carga entre nós
- Tolerância a falhas e escalabilidade automática
- Armazenamento persistente
- Health checks e testes unitários
- Containerização com Docker

## 🚀 Requisitos
- Docker e Docker Compose
- Linux (ou WSL no Windows)
- Bash

## Comandos
- Open docker desktop
- docker compose build ## Build docker image, executa as instruções de cada dockerfile
- docker compose up -d  ## Arrancar os serviços
- docker compose ps ## Ver o estado dos serviços


## ⚙️ Instalação e Execução
```bash
chmod +x start.sh
./start.sh