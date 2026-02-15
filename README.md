# FioGora (Integração Fiorilli-Ahgora)

Sistema de integração automatizada entre o sistema de gestão Fiorilli e a plataforma de controle de ponto Ahgora, agora modernizado com uma API FastAPI e suporte a Docker.

---

## Descrição

Fiogora é uma solução para automatizar a sincronização de dados entre o sistema de gestão Fiorilli e a plataforma Ahgora. Esta versão modernizeada utiliza uma arquitetura baseada em API (FastAPI) para gerenciar tarefas de sincronização em segundo plano, com persistência em banco de dados PostgreSQL.

## Requisitos do Sistema

- **Docker & Docker Compose** (Recomendado)
- **OU**
- **Python 3.13** (vinda do `uv`)
- **PostgreSQL**
- **Firefox** (para automação Selenium local)

## Como Executar

### 1. Via Docker (Recomendado)

O Docker Compose sobe tanto a API quanto o banco de dados PostgreSQL automaticamente.

1. Configure seu arquivo `.env` (veja seção abaixo).
2. Execute o comando:
   ```bash
   docker-compose up --build
   ```
3. A API estará disponível em `http://localhost:8000`.
4. Documentação interativa (Swagger): `http://localhost:8000/docs`.

### 2. Execução Local (Desenvolvimento)

1. **Instale as dependências**:
   ```bash
   uv sync
   ```
2. **Configure o Banco de Dados**:
   Certifique-se de ter um PostgreSQL rodando e ajuste o `DATABASE_URL` no `.env`.
3. **Execute as migrações**:
   ```bash
   uv run alembic upgrade head
   ```
4. **Inicie o servidor**:
   ```bash
   uv run uvicorn app.main:app --reload
   ```

## Configuração (.env)

Crie um arquivo `.env` na raiz do projeto:

```env
# Credenciais Fiorilli
FIORILLI_USER=seu_usuario
FIORILLI_PASSWORD=sua_senha

# Credenciais Ahgora
AHGORA_USER=seu_usuario
AHGORA_PASSWORD=sua_senha
AHGORA_COMPANY=codigo_empresa

# Configurações do Banco (Local)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/fiogora

# Automação
HEADLESS_MODE=True
```

## Estrutura de Diretórios (Novo)

```
fiogora/
├── app/
│   ├── api/            # Endpoints FastAPI
│   ├── core/           # Configurações e DB
│   ├── domain/         # Entidades e Enums
│   ├── infrastructure/ # Automação (Selenium) e Repositórios
│   ├── services/       # Lógica de negócio
│   └── main.py         # Ponto de entrada da API
├── tests/              # Testes unitários e de integração
├── Dockerfile          # Configuração Docker
└── docker-compose.yml  # Orquestração de serviços
```

## API Endpoints Principais

- `POST /api/sync/run`: Inicia uma nova sincronização em segundo plano.
- `GET /api/sync/jobs`: Lista todos os trabalhos de sincronização.
- `GET /api/sync/jobs/{id}`: Detalhes de um trabalho específico.
- `GET /api/sync/jobs/{id}/logs`: Logs detalhados de execução do trabalho.

## Licença

Este projeto é licenciado sob os termos da [licença MIT](LICENSE).
