Diogo Paiva Almeida - 81477

# Sistemas Distribuídos SPD – Projeto “Key-Value Distribuído”

## 1. Visão Geral

Este repositório contém a implementação de um sistema de armazenamento distribuído de pares **key-value**, capaz de executar operações básicas (**PUT**, **GET**, **DELETE**) sobre múltiplos nós, garantindo disponibilidade, escalabilidade, tolerância a faltas e consistência.

## 2. Arquitetura do Sistema

O sistema segue um padrão de micro-serviços, organizado em clusters e com um reverse proxy na entrada.

![Diagrama de Arquitetura](docs/arquitetura.png)

> **Figura:** Ilustração dos componentes principais e dos fluxos de dados entre eles.

### Componentes

1. **Nginx**
   – Serviço de reverse proxy que recebe requisições HTTP, aplica health-check e encaminha o tráfego para o Envoy mantendo cabeçalhos essenciais.
2. **Envoy Proxy**
   – Docker container que executa o proxy Envoy v1.28 e um serviço FastAPI que funciona como API Gateway, enfileirando operações de escrita no RabbitMQ e encaminhando leituras para o nó de armazenamento.
3. **Cluster Redis**
   – Service que atua como Storage Node: gere operações sobre CockroachDB com cache Redis via Sentinel para aceleração de leituras.
4. **Cluster API**
   – Conjunto de instâncias que expõem a REST-API pública (`PUT`, `GET`, `DELETE`).
5. **Cluster Queue**
   – Camada de mensagens para orquestração de tarefas assíncronas (por ex., replicação, invalidation).
6. **Cluster Consumer**
   – Consumidores que processam eventos da fila.
7. **Cluster Base de Dados (BD)**
   – Repositório persistente para logs de operações e fallback de consistência.

## 3. ## Requisitos  
Para clonar e executar este repositório, só precisas de ter instalado no teu sistema:  
1. **Docker** (versão 20.10+).  
2. **Docker Compose** (versão 1.29+).  

Após isso, basta correr:
```bash
git clone <repo-url>
cd key-value-distribuido
./start.sh


## 4. Instalação e Setup

1. **Clone o repositório**

   ```bash
   git clone git@github.com:a66264/sistemas-distribuidos-spd.git
   cd sistemas-distribuidos-spd
   ```
2. **Configure variáveis de ambiente**
   Copie `.env.example` para `.env` e ajuste conforme necessário (portas, credenciais, endereços de cluster).
3. **Bootstrap e inicialização**

   ```bash
   chmod +x start.sh
   ./start.sh
   ```


   Este script:

   * Cria redes Docker
   * Inicia Nginx e Envoy
   * Levanta clusters de Redis, API, Queue, Consumer e BD
   * Executa health checks iniciais

## 5. Health Checks e Testes Unitários

* Cada serviço expõe um endpoint de health check em `/healthz`.
* Testes Unitários não suportados.

## 6. Considerações de Sistemas Distribuídos

* **Concorrência**: todos os clusters são balanceados pelo Nginx/Envoy e usam mecanismos de locking no Redis para evitar condições de corrida.
* **Escalabilidade**: containers são replicáveis horizontalmente; o sistema não suporta “auto-scale”.
* **Tolerância a faltas**: fallback automático para outra réplica em caso de falha de um nó; health checks e reinicialização automática.
* **Consistência**: modelo de consistência eventual com confirmação síncrona opcional via fila de eventos para réplicas críticas.
* **Coordenação**: Envoy gerencia descoberta de serviços e roteamento, enquanto Redis garante locks e filas suportam ordenação de eventos.

## 7. Uso em Cloud e Standalone

* **Standalone**: basta o `start.sh` em máquina GNU/Linux com Docker.
* **Cloud**: Cloud não suportada.

## 8. Relatórios e Testes de Carga

* Localizados em `docs/testes-carga.md`, incluindo ferramentas usadas (e.g. `locust`, `wrk`), parâmetros, resultados e conclusões sobre limites.

## 9. Bibliografia

* Artigos e livros de sistemas distribuídos (incluídos em `docs/bibliografia.bib`).
* Indicação de uso de IA para suporte à escrita: ChatGPT (OpenAI).

---

> **Demo:** Disponível em ambiente de staging via URL pública (ver arquivo `docs/demo.md`).
> **Repositório privado:** Acesso via GitHub a81477 (domínio ualg.pt).
