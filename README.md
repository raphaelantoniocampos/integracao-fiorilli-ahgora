# FioGora (Integração Fiorilli-Ahgora)

Sistema de integração automatizada entre o sistema de gestão Fiorilli e a plataforma de controle de ponto Ahgora.

## Descrição

O projeto Integração Fiorilli-Ahgora (IFA) é uma solução desenvolvida para automatizar e facilitar a sincronização de dados entre o sistema de gestão Fiorilli e a plataforma de controle de ponto Ahgora. O sistema permite baixar dados de funcionários e afastamentos do Fiorilli, dados de funcionários do Ahgora, analisar essas informações e executar tarefas de sincronização entre os dois sistemas.

A aplicação utiliza dois tipos de automação:
1. **Automação de Navegador (Selenium)**: Utilizada para extração (download) de dados dos sistemas Fiorilli e Ahgora de forma totalmente automatizada.
2. **Automação de Interface Gráfica (PyAutoGUI)**: Utilizada para execução de tarefas de sincronização (inserção de dados), operando em modo semi-automatizado onde o sistema interage com o navegador aberto pelo usuário.

## Requisitos do Sistema

- **Python 3.13** ou superior
- **[uv](https://docs.astral.sh/uv/)** para gerenciamento de pacotes
- **Firefox** (necessário para os downloads automatizados via Selenium)
- **Acesso aos sistemas** Fiorilli e Ahgora
- **Resolução de Tela**: Preferencialmente resoluções padrão (1920x1080) para melhor funcionamento da automação de interface.

## Dependências

O projeto utiliza as seguintes bibliotecas principais:
- **Selenium & Webdriver-Manager**: Para downloads automatizados.
- **PyAutoGUI, Keyboard & Pyperclip**: Para automação de tarefas e interação com a interface.
- **Pandas**: Para processamento e análise de dados.
- **InquirerPy & Rich**: Para interface de linha de comando (CLI) interativa.
- **Python-dotenv**: Para gerenciamento de credenciais.

## Instalação

1. Clone o repositório:
   ```bash
   git clone https://github.com/seu-usuario/fiogora.git
   cd fiogora
   ```

2. Inicie o sistema com uv:
   ```bash
   uv run main.py
   ```

## Build (Opcional)

Se desejar gerar um executável (.exe) para distribuição em outros computadores, o projeto utiliza o `PyInstaller` gerenciado via `Makefile`.

1. Certifique-se de ter o `make` instalado no Windows (ou utilize o `nmake`/`mingw32-make`).
2. Execute o comando:
   ```bash
   make build
   ```
3. O executável será gerado no diretório `dist/fiogora/`.

Comandos adicionais do `Makefile`:
- `make clean`: Remove arquivos temporários de build.
- `make update`: Reconstrói o executável preservando dados existentes nas pastas `data`, `downloads` e `tasks`.
- `make help`: Lista todos os comandos disponíveis.

## Configuração

1. Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:
   ```env
   FIORILLI_USER=seu_usuario_fiorilli
   FIORILLI_PSW=sua_senha_fiorilli
   AHGORA_USER=seu_usuario_ahgora
   AHGORA_PSW=sua_senha_ahgora
   AHGORA_COMPANY=nome_da_sua_empresa_ahgora
   ```

2. Alternativamente, execute o programa e insira as credenciais quando solicitado.

3. Os diretórios `data`, `tasks` e `downloads` são criados automaticamente na primeira execução.

## Estrutura de Diretórios

```
fiogora/
├── data/                  # Dados processados e configurações
│   ├── ahgora/            # CSVs de funcionários baixados do Ahgora
│   └── fiorilli/          # CSVs/TXTs de funcionários e afastamentos do Fiorilli
├── downloads/             # Temporário para arquivos baixados pelo navegador
├── tasks/                 # Listas de tarefas pendentes (CSVs gerados após análise)
├── src/                   # Código-fonte
│   ├── browsers/          # Classes de automação (Core, Ahgora, Fiorilli)
│   ├── managers/          # Orquestradores (Data, Download, File, Task)
│   ├── models/            # Modelos de dados e definições de teclas
│   ├── tasks/             # Lógica de execução das tarefas (Add, Update, Remove)
│   └── utils/             # Configurações, UI e constantes
└── README.md
```

## Uso

### 1. Baixar Dados
Selecione **"Downloads"** no menu principal. O sistema utilizará o Selenium para navegar nos sites, realizar login e baixar os relatórios de funcionários e afastamentos necessários.

### 2. Analisar Dados
Selecione **"Dados" -> "Analisar Dados"**. O sistema processará os arquivos baixados, normalizará os textos (removendo acentos, padronizando nomes) e identificará:
- Novos funcionários no Fiorilli ausentes no Ahgora.
- Funcionários desligados.
- Alterações em cargos ou departamentos.
- Novos afastamentos/férias.

As diferenças serão salvas como novos arquivos CSV no diretório `tasks/`.

### 3. Executar Tarefas
Selecione **"Tarefas"** e escolha a ação desejada. Para tarefas de inserção (como "Adicionar Funcionários"):
1. O sistema abrirá o navegador na página correta.
2. O sistema solicitará que você prepare a tela.
3. Use as teclas de atalho (configuradas em `src/models/key.py`) para confirmar a inserção de cada registro via PyAutoGUI.

## Configurações

Acesse o menu de configurações para:
- **Headless Mode**: Ativa/desativa a visualização do navegador durante os downloads automatizados.
- **Meses Retroativos**: Define quão longe no passado o sistema deve buscar por afastamentos.
- **Resetar Credenciais**: Editar o arquivo `.env` para atualização de dados.

## Solução de Problemas

### Falhas nos Downloads

- O modo **Headless** pode falhar se houver popups inesperados. Tente desativá-lo.
- Certifique-se de que o Firefox não tenha extensões que bloqueiem o download automático.

### Falhas nas Tarefas (PyAutoGUI)

- Não mova o mouse ou troque de janela enquanto o sistema estiver digitando dados.
- Verifique se o layout do teclado está correto (pode afetar caracteres especiais).
- O sistema depende da contagem de "tabs". Se a interface do Ahgora mudar, a sequência de preenchimento pode falhar.

## Licença

Este projeto é licenciado sob os termos da [licença MIT](LICENSE).
