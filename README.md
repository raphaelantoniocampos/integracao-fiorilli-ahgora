# 🤖 FioGora (Integração Fiorilli-Ahgora)

[![Python](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-05998b.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?logo=docker&logoColor=white)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**FioGora** é um serviço de integração RPA de alto desempenho que automatiza a sincronização de dados de funcionários entre o sistema de gestão **Fiorilli** e a plataforma de controle de ponto **Ahgora**. Ele utiliza **FastAPI** para gerenciamento, **PostgreSQL** para persistência e **Selenium** para automação.

---

## ✨ Recursos

- **Sincronização Automatizada**: Conexão contínua entre o Fiorilli e o Ahgora.
- **Arquitetura Assíncrona**: Gerenciamento de tarefas em segundo plano usando FastAPI Lifespan e agendadores.
- **Docker-First**: Ambiente totalmente em contêineres para implantação consistente.
- **Gerenciamento de Tarefas**: API REST para monitorar, listar e revisar logs detalhados de cada tarefa de sincronização.
- **Sistema de Repetição de Tarefas (Retry)**: Agendador integrado para lidar com falhas de automação transitórias.
- **Logs Detalhados**: Logs de execução granulares disponíveis via API REST.

---

## 🚀 Como Começar

### 1. Requisitos

- **Docker & Docker Compose** (Recomendado)
- **OR** Python 3.13 (`uv`), PostgreSQL e Firefox (para desenvolvimento local).

### 2. Configuração

**1. Variáveis de Ambiente:**

Crie um arquivo `.env` a partir do exemplo (`cp .env.example .env`) e preencha as variáveis:

| Variável            | Descrição                                          | Padrão |
| ------------------- | -------------------------------------------------- | ------ |
| `FIORILLI_USER`     | Usuário de acesso ao sistema Fiorilli              | -      |
| `FIORILLI_PASSWORD` | Senha de acesso ao sistema Fiorilli                | -      |
| `FIORILLI_URL`      | URL base do sistema Fiorilli                       | -      |
| `AHGORA_USER`       | Usuário de acesso à plataforma Ahgora              | -      |
| `AHGORA_PASSWORD`   | Senha de acesso à plataforma Ahgora                | -      |
| `AHGORA_COMPANY`    | Código da empresa na plataforma Ahgora             | -      |
| `AHGORA_URL`        | URL de login da plataforma Ahgora                  | -      |
| `HEADLESS_MODE`     | Executar navegador de forma invisível (True/False) | `True` |

**2. Configuração no Fiorilli:**

Configure as colunas da tabela no painel *Fiorilli 2.1 - Cadastro de Trabalhadores* e defina como padrão para seu usuário:

- Registro
- Nome
- CPF
- Sexo
- Dt. Nascimento
- PIS/PASEP/NIT
- Nome Cargo Atual
- Nome Local Trabalho
- Nome Unidade Orçamentária
- Nome Vinculo
- Dt. Admissão
- Dt. Desligamento

### 3. Executando

**1. Docker:**

```bash
docker-compose up -d --build
```

**2. Localmente:**

```bash
docker-compose up -d db
uv run uvicorn app.main:app --reload
```

- **API**: `http://localhost:8000`
- **Docs (Swagger)**: `http://localhost:8000/docs`

---

## 📑 Documentação da API

| Método | Endpoint                   | Descrição                                |
|:------ |:-------------------------- |:---------------------------------------- |
| `POST` | `/api/sync/run`            | Inicia uma nova tarefa de sincronização  |
| `GET`  | `/api/sync/jobs`           | Lista todas as tarefas de sincronização  |
| `GET`  | `/api/sync/jobs/{id}`      | Obtém detalhes específicos de uma tarefa |
| `GET`  | `/api/sync/jobs/{id}/logs` | Busca os logs detalhados de uma tarefa   |
| `POST` | `/api/sync/jobs/{id}/kill` | Interrompe uma tarefa em andamento       |
| `GET`  | `/health`                  | Status de integridade do serviço         |

Para detalhes completos dos payloads, parâmetros e respostas, acesse a documentação interativa Swagger via `http://localhost:8000/docs` após iniciar o projeto.

---

## 📂 Estrutura do Projeto

```text
fiogora/
├── app/
│   ├── api/            # REST API Layer
│   ├── core/           # Config, DB, and Scheduler logic
│   ├── domain/         # Business entities and schemas
│   ├── infrastructure/ # RPA (Selenium) and Repositories
│   ├── services/       # Core business logic
│   └── main.py         # Application Entrypoint
├── tests/              # Test suite
├── Dockerfile          # Container definition
└── docker-compose.yml  # Service orchestration
```

---

## 📜 Licença

Distribuído sob a licença **MIT**. Veja `LICENSE` para mais informações.
