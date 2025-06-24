# Makefile

# --- Configurações do Projeto ---
PROJECT_ROOT := $(CURDIR)
APP_NAME     := Integracao Fiorilli Ahgora
MAIN_SCRIPT  := main.py
ICON_FILE    := ifa2.ico

# --- Comandos ---
PYTHON_CMD   := uv run python

PYINSTALLER_FLAGS = --noconfirm --onedir --console \
	--icon "$(PROJECT_ROOT)/$(ICON_FILE)" \
	--name "$(APP_NAME)" \
	--add-data "$(PROJECT_ROOT)/src;src/" \

PYINSTALLER_CMD = uv run pyinstaller $(PYINSTALLER_FLAGS) "$(PROJECT_ROOT)/$(MAIN_SCRIPT)"

# --- Targets ---
.PHONY: all clean build shortcut update help

all: clean build shortcut

build:
	@echo "--------------------------------------------------"
	@echo "Iniciando o build do executavel..."
	@echo "--------------------------------------------------"
	$(PYINSTALLER_CMD)
	@echo "--------------------------------------------------"
	@xcopy /Y /I "$(PROJECT_ROOT)\data\leave_codes.csv" "$(PROJECT_ROOT)\dist\$(APP_NAME)\data\"
	@echo "Build concluido!"
	@echo "Executavel em: $(PROJECT_ROOT)/dist/$(APP_NAME)/"
	@echo "--------------------------------------------------"

update:
	@echo "--------------------------------------------------"
	@echo "Iniciando o build do executavel..."
	@echo "--------------------------------------------------"
	@xcopy /S /Y /I /E "$(PROJECT_ROOT)\dist\$(APP_NAME)\data" "$(PROJECT_ROOT)\data"
	@xcopy /S /Y /I /E "$(PROJECT_ROOT)\dist\$(APP_NAME)\downloads" "$(PROJECT_ROOT)\downloads"
	@xcopy /S /Y /I /E "$(PROJECT_ROOT)\dist\$(APP_NAME)\tasks" "$(PROJECT_ROOT)\tasks"
	$(PYINSTALLER_CMD)
	@echo "--------------------------------------------------"
	@xcopy /S /Y /I /E "$(PROJECT_ROOT)\data" "$(PROJECT_ROOT)\dist\$(APP_NAME)\data"
	@xcopy /S /Y /I /E "$(PROJECT_ROOT)\downloads" "$(PROJECT_ROOT)\dist\$(APP_NAME)\downloads"
	@xcopy /S /Y /I /E "$(PROJECT_ROOT)\tasks" "$(PROJECT_ROOT)\dist\$(APP_NAME)\tasks"
	@echo "Build concluido!"
	@echo "Executavel em: $(PROJECT_ROOT)/dist/$(APP_NAME)/"
	@echo "--------------------------------------------------"

shortcut:
	@echo "--------------------------------------------------"
	@echo "Criando atalho na area de trabalho publica..."
	@echo "--------------------------------------------------"
	@$(PYTHON_CMD) -c "import os, sys, win32com.client; \
		target_path = os.path.join('$(PROJECT_ROOT)', 'dist', '$(APP_NAME)', '$(APP_NAME).exe'); \
		shortcut_path = os.path.join('$(PUBLIC_DESKTOP)', '$(APP_NAME).lnk'); \
		shell = win32com.client.Dispatch('WScript.Shell'); \
		shortcut = shell.CreateShortCut(shortcut_path); \
		shortcut.Targetpath = target_path; \
		shortcut.WorkingDirectory = os.path.dirname(target_path); \
		shortcut.IconLocation = os.path.join('$(PROJECT_ROOT)', '$(ICON_FILE)'); \
		shortcut.save()"
	@echo "Atalho criado em: $(PUBLIC_DESKTOP)/$(APP_NAME).lnk"
	@echo "--------------------------------------------------"

clean:
	@echo "--------------------------------------------------"
	@echo "Limpando arquivos de build (build/, dist/, *.spec)..."
	@echo "--------------------------------------------------"
	@$(PYTHON_CMD) -c "import shutil, os, glob; \
		print('Removendo diretorio: build/'); shutil.rmtree('build', ignore_errors=True); \
		print('Removendo diretorio: dist/'); shutil.rmtree('dist', ignore_errors=True); \
		spec_files = glob.glob('*.spec'); \
		print(f'Removendo arquivos .spec: {spec_files}'); \
		[os.remove(f) for f in spec_files if os.path.isfile(f)]"
	@echo "--------------------------------------------------"
	@echo "Limpeza concluida."
	@echo "--------------------------------------------------"

help:
	@echo "--------------------------------------------------"
	@echo "Alvos disponiveis do Makefile:"
	@echo "--------------------------------------------------"
	@echo "  make all		- Constroi o projeto (default)."
	@echo "  make build		- Constroi o executavel."
	@echo "  make update		- Atualiza o executavel."
	@echo "  make shortcut	- Cria um atalho na area de trabalho publica."
	@echo "  make clean		- Remove os diretorios build/, dist/ e arquivos *.spec."
	@echo "  make help		- Mostra esta mensagem de ajuda."
	@echo "--------------------------------------------------"
