# Integração Fiorilli-Ahgora (IFA)

Sistema de integração automatizada entre o sistema de gestão Fiorilli e a plataforma de controle de ponto Ahgora.

## Descrição

O projeto Integração Fiorilli-Ahgora (IFA) é uma solução desenvolvida para automatizar e facilitar a sincronização de dados entre o sistema de gestão Fiorilli e a plataforma de controle de ponto Ahgora. O sistema permite baixar dados de funcionários e afastamentos do Fiorilli, dados de funcionários do Ahgora, analisar essas informações e executar tarefas de sincronização entre os dois sistemas.

A aplicação utiliza automação de navegador para interagir com as interfaces web dos sistemas, extraindo e inserindo dados conforme necessário, sem depender de APIs específicas.

## Requisitos do Sistema

- Python 3.13 ou superior
- [uv](https://docs.astral.sh/uv/) para gerenciamento de pacotes
- Firefox (para automação de navegador)
- Acesso aos sistemas Fiorilli e Ahgora

## Dependências

O projeto utiliza as seguintes bibliotecas Python:
- chardet (>=5.2.0)
- inquirerpy (>=0.3.4)
- keyboard (>=0.13.5)
- pandas (>=2.2.3)
- pillow (>=11.1.0)
- pyautogui (>=0.9.54)
- pyperclip (>=1.9.0)
- pyproject-toml (>=0.1.0)
- pyscreeze (>=1.0.1)
- python-dotenv (>=1.0.1)
- rich (>=13.9.4)
- selenium (>=4.28.1)
- webdriver-manager (>=4.0.2)

## Instalação

1. Clone o repositório:
   ```bash
   git clone https://github.com/seu-usuario/integracao-fiorilli-ahgora.git
   cd integracao-fiorilli-ahgora
   ```

2. Inicie o main.py com uv:
   ```bash
   uv run main.py
   ```


## Configuração

1. Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:
   ```
   FIORILLI_USER=seu_usuario_fiorilli
   FIORILLI_PSW=sua_senha_fiorilli
   AHGORA_USER=seu_usuario_ahgora
   AHGORA_PSW=sua_senha_ahgora
   AHGORA_COMPANY=nome_da_sua_empresa_ahgora
   ```

2. Alternativamente, execute o programa e insira as credenciais quando solicitado.

3. Certifique-se de que os diretórios `data`, `tasks` e `downloads` existam na raiz do projeto. Eles serão criados automaticamente na primeira execução.

## Estrutura de Diretórios

```
integracao-fiorilli-ahgora/
├── data/                  # Diretório para armazenamento de dados processados
│   ├── ahgora/            # Dados relacionados ao Ahgora
│   └── fiorilli/          # Dados relacionados ao Fiorilli
├── downloads/             # Diretório para arquivos baixados
├── tasks/                 # Arquivos de tarefas pendentes
├── src/                   # Código-fonte do projeto
│   ├── browsers/          # Módulos de automação de navegador
│   ├── managers/          # Gerenciadores (tarefas, arquivos, dados, downloads)
│   ├── models/            # Modelos de dados
│   ├── tasks/             # Implementações de tarefas específicas
│   └── utils/             # Utilitários (configuração, constantes, credenciais, UI)
└── README.md              # Este arquivo
```

## Uso

Execute o programa principal:

```bash
uv run main.py
```

### Menu Principal

O sistema apresenta um menu interativo com as seguintes opções:

1. **Baixar Dados**: Permite baixar dados dos sistemas Fiorilli e Ahgora.
2. **Analisar Dados**: Processa os dados baixados e identifica diferenças entre os sistemas.
3. **Tarefas**: Lista e permite executar tarefas de sincronização.
4. **Configurações**: Permite ajustar configurações do sistema.
5. **Sair**: Encerra o programa.

### Fluxo de Trabalho Típico

1. **Baixar Dados**:
   - Selecione "Baixar Dados" no menu principal
   - Escolha quais dados deseja baixar (Afastamentos, Funcionários Ahgora, Funcionários Fiorilli)
   - Confirme a seleção

2. **Analisar Dados**:
   - Após o download, selecione "Analisar Dados" no menu principal
   - O sistema processará os dados e identificará diferenças entre os sistemas

3. **Executar Tarefas**:
   - Selecione "Tarefas" no menu principal
   - Escolha uma das tarefas disponíveis:
     - Adicionar funcionários
     - Remover funcionários
     - Atualizar funcionários
     - Adicionar afastamentos
   - O sistema automatizará a execução da tarefa no Ahgora

## Configurações

Acesse o menu de configurações para:

- Alternar o modo headless (execução sem interface gráfica do navegador)
- Configurar variáveis de ambiente (credenciais)
- Visualizar informações sobre a última análise e downloads

## Modo Headless

Por padrão, o sistema opera em modo headless, o que significa que a automação do navegador ocorre em segundo plano, sem exibir a interface gráfica. Isso é útil para execução em servidores ou para evitar interrupções no trabalho.

Para desativar o modo headless (útil para depuração):
1. Selecione "Configurações" no menu principal
2. Escolha "Alterar Headless Mode"

## Solução de Problemas

### Falhas na Automação do Navegador

Se a automação do navegador falhar:
- Verifique se o Firefox está instalado e atualizado
- Desative o modo headless para visualizar o processo
- Verifique se as credenciais estão corretas
- Verifique se houve alterações nas interfaces dos sistemas Fiorilli ou Ahgora

### Erros de Análise de Dados

Se a análise de dados falhar:
- Verifique se os arquivos foram baixados corretamente
- Verifique se os formatos dos arquivos exportados não foram alterados
- Execute novamente o download dos dados

## Desenvolvimento

Para contribuir com o desenvolvimento sinta-se livre para mandar um Pull Request ou abrir uma Issue.

## Licença

Este projeto é licenciado sob os termos da licença MIT.
