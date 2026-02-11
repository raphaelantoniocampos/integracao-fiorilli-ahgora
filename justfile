# --- Variables ---
set shell := ["powershell.exe", "-c"]

project_root := invocation_directory()
app_name     := "fiogora"
main_script  := "main.py"
icon_file    := "ifa3.ico"
dist_path    := project_root / "dist" / app_name

# Dynamically pull version from pyproject.toml
pkg_version   := `uv run python -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])"`
zip_full_name := app_name + "-" + pkg_version

python_cmd   := "uv run python"
pyinstaller  := "uv run pyinstaller"

# --- Recipes ---

# Default recipe: Clean and Build
all: clean build

# Build the executable and create ZIP
build:
    @echo "--------------------------------------------------"
    @echo "Iniciando o build do executavel v{{pkg_version}}..."
    @echo "--------------------------------------------------"
    {{ pyinstaller }} --noconfirm --onedir --console \
        --icon "{{ project_root }}/{{ icon_file }}" \
        --name "{{ app_name }}" \
        --add-data "{{ project_root }}/src;src/" \
        --add-data "{{ project_root }}/data/leave_codes.csv;data/leave_codes.csv" \
        "{{ project_root }}/{{ main_script }}"
    
    @echo "Copiando arquivos adicionais..."
    @{{ python_cmd }} -c "import shutil; shutil.copy2('pyproject.toml', r'{{ dist_path }}')"
    
    @echo "Criando arquivo comprimido dentro da pasta dist..."
    @{{ python_cmd }} -c "import shutil, os; \
        output_path = os.path.join('dist', '{{ zip_full_name }}'); \
        shutil.make_archive(output_path, 'zip', r'{{ dist_path }}')"
    
    @echo "--------------------------------------------------"
    @echo "Build concluido!"
    @echo "Diretorio: {{ dist_path }}"
    @echo "Arquivo:   dist/{{ zip_full_name }}.zip"
    @echo "--------------------------------------------------"

# Backup current data, rebuild, and restore
update:
    @echo "Iniciando atualizacao com backup de dados..."
    @{{ python_cmd }} -c "import shutil, os; [shutil.copytree(os.path.join(r'{{ dist_path }}', d), d, dirs_exist_ok=True) for d in ['data', 'downloads', 'tasks'] if os.path.exists(os.path.join(r'{{ dist_path }}', d))]"
    just build
    @{{ python_cmd }} -c "import shutil, os; [shutil.copytree(d, os.path.join(r'{{ dist_path }}', d), dirs_exist_ok=True) for d in ['data', 'downloads', 'tasks'] if os.path.exists(d)]"

# Clean build artifacts
clean:
    @echo "Limpando arquivos de build anteriores..."
    @{{ python_cmd }} -c "import shutil, os, glob; \
        shutil.rmtree('build', ignore_errors=True); \
        shutil.rmtree('dist', ignore_errors=True); \
        [os.remove(f) for f in glob.glob('*.spec') + glob.glob('*.zip')]"

# Show available commands
help:
    just --list
