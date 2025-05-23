Sistemas Distribuídos SPD – Projeto “Key-Value Distribuído”
1. Visão Geral
Este repositório contém a implementação de um sistema de armazenamento distribuído de pares key-value, capaz de executar operações básicas (PUT, GET, DELETE) sobre múltiplos nós, garantindo escalabilidade, tolerância a falhas e consistência.

2. Arquitetura do Sistema
O sistema segue um padrão de micro-serviços, organizado em clusters e com um reverse proxy na entrada.


Figura: Ilustração dos componentes principais e dos fluxos de dados entre eles.

Componentes
Nginx
– Reverse proxy HTTP para distribuição inicial de tráfego.

Envoy Proxy
– Sidecar/gateway para roteamento interno, observabilidade e segurança entre serviços.

Cluster Redis
– Armazenamento persistente de pares key-value e suporte a locks/distribuição de carga.

Cluster API
– Conjunto de instâncias que expõem a REST-API pública (PUT, GET, DELETE).

Cluster Queue
– Camada de mensagens para orquestração de tarefas assíncronas (por ex., replicação, invalidation).

Cluster Consumer
– Consumidores que processam eventos da fila (por ex., consolidação de réplicas, limpeza).

Cluster Base de Dados (BD)
– Repositório persistente para logs de operações e fallback de consistência.

3. Requisitos
Docker / Docker Compose (GNU/Linux)

Bash (script de bootstrap: start.sh)

Python 3.10+ ou Node.js 18+ (dependendo da implementação dos micro-serviços)

Ferramentas de testes: curl, pytest ou equivalente

4. Instalação e Setup
Clone o repositório

bash
Copiar
Editar
git clone git@github.com:a66264/sistemas-distribuidos-spd.git
cd sistemas-distribuidos-spd
Configure variáveis de ambiente
Copie .env.example para .env e ajuste conforme necessário (portas, credenciais, endereços de cluster).

Bootstrap e inicialização

bash
Copiar
Editar
chmod +x start.sh
./start.sh
Este script:

Cria redes Docker

Inicia Nginx e Envoy

Levanta clusters de Redis, API, Queue, Consumer e BD

Executa health checks iniciais

5. Manual de API
Todas as chamadas usam JSON e seguem o padrão REST sobre HTTP:

Operação	Método	Endpoint	Request Body	Response
PUT	PUT	/kv	{ "data": { "key": "<chave>", "value": "<valor>" } }	HTTP 200 OK
GET	GET	/kv?key=<chave>	–	{ "data": { "value": "<valor>" } }
DELETE	DELETE	/kv?key=<chave>	–	HTTP 200 OK

Exemplo PUT

bash
Copiar
Editar
curl -X PUT http://localhost/kv \
     -H "Content-Type: application/json" \
     -d '{"data":{"key":"foo","value":"bar"}}'
6. Health Checks e Testes Unitários
Cada serviço expõe um endpoint de health check em /healthz.

Testes unitários localizados em tests/, executáveis via:

bash
Copiar
Editar
pytest tests/          # se em Python
npm test               # se em Node.js
7. Considerações de Sistemas Distribuídos
Concorrência: todos os clusters são balanceados pelo Nginx/Envoy e usam mecanismos de locking no Redis para evitar condições de corrida.

Escalabilidade: containers são replicáveis horizontalmente; o sistema pode “auto-scale” via orquestrador (ex.: Kubernetes).

Tolerância a faltas: fallback automático para outra réplica em caso de falha de um nó; health checks e reinicialização automática.

Consistência: modelo de consistência eventual com confirmação síncrona opcional via fila de eventos para réplicas críticas.

Coordenação: Envoy gerencia descoberta de serviços e roteamento, enquanto Redis garante locks e filas suportam ordenação de eventos.

8. Uso em Cloud e Standalone
Standalone: basta o start.sh em máquina GNU/Linux com Docker.

Cloud: use Terraform/Helm (não incluídos) para provisionar infraestrutura e replicar a configuração Docker em VMs ou cluster Kubernetes.

9. Relatórios e Testes de Carga
Localizados em docs/testes-carga.md, incluindo ferramentas usadas (e.g. locust, wrk), parâmetros, resultados e conclusões sobre limites.

10. Bibliografia
Artigos e livros de sistemas distribuídos (incluídos em docs/bibliografia.bib).

Indicação de uso de IA para suporte à escrita: ChatGPT (OpenAI).

Demo: Disponível em ambiente de staging via URL pública (ver arquivo docs/demo.md).
Repositório privado: Acesso via GitHub a66264 (domínio ualg.pt).