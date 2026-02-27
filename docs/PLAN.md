# Plan: Implement Automatic `add_leaves` in App

## 1. Objective
Automate the process of adding leaves (afastamentos) to Ahgora, replacing the legacy CLI interactive process (`src/tasks/add_leaves_task.py`) with a fully automated Selenium-based workflow within the new app architecture.

## 2. Technical Context
- **Legacy Code**: The legacy code (`src/tasks/add_leaves_task.py`) relies on manual user interaction. The user is prompted to manually import the file, copy the resulting validation errors from the Ahgora screen into a `filter.txt` file, which the script then parses to remove invalid records before generating a new file for a second manual import.
- **Current Architecture**: The system uses Selenium in `app/infrastructure/automation/web/ahgora_browser.py`. The `AhgoraBrowser` currently has a basic `add_leave(file_path: str)` method that only uploads the file and clicks "Obter Registros" but doesn't handle the validation step or clicking "Salvar".

## 3. Proposed Changes

### 3.1. Enhance `AhgoraBrowser` (Frontend/Web Automation)
Update the `AhgoraBrowser` to handle the validation and saving steps:
- **`upload_leaves_file(self, file_path)`**: Navigate to `/afastamentos/importa`, select layout `pw_afimport_01`, insert the file, and click "Obter Registros".
- **`extract_import_errors(self)`**: After obtaining records, use Selenium to scan the resulting validation table. It will extract the row index and the specific error messages (e.g., "Intersecção com afastamento existente", "Matrícula inexistente").
- **`confirm_import(self)`**: Click the "Salvar" button to commit the error-free records to Ahgora.

### 3.2. Implement `LeaveSyncService` (Backend/Service Logic)
Create a new service (or add to `SyncService`) to orchestrate the multi-step flow:
1. **Generate**: Read the incoming leaves data, format it according to `config.data.get("upload_leaves_columns")`, and generate a temporary `upload_leaves_initial.csv` (no header).
2. **First Import**: Use `AhgoraBrowser` to upload the initial file.
3. **Evaluate**: Call `extract_import_errors()` to get the list of failed rows.
4. **Filter**: Exclude the errored rows from the dataset. Leave only the successful ones.
5. **Generate Final**: Create a new file `upload_leaves_final.csv` with only the error-free records.
6. **Final Import & Save**: Use `AhgoraBrowser` to upload the final file, and then call `confirm_import()` to save.
7. **Logging/Database**: Generate a detailed report (e.g., a `.txt` or `.csv` log) showing exactly which leaves were imported and which failed. Update the local database to mark the imported leaves as synced, so they are excluded from future runs.

### 3.3. Task Integration
- Create an entry point for this task in the `TaskExecutionService` or `TaskRegistry` so it can be triggered like other jobs.

## 4. Verification Plan

### Automated Verification
- Write tests or use `checklist.py .` and `pytest` (if configured) to ensure the logic for filtering records by row index works precisely and that no off-by-one errors occur during the CSV regeneration.

### Manual / E2E Verification
1. Place a mock `leaves.csv` payload in the designated Fiorilli drop folder, intentionally including records that will trigger "Intersecção" errors on Ahgora alongside valid records.
2. Trigger the `add_leaves` job.
3. Observe the Selenium browser: it should upload the file, wait for validation, scrape the screen, automatically generate a new file, upload the new file, and finally click "Salvar".
4. Check the generated logs to ensure the errored records are detailed correctly.
5. Check the local DB to confirm that the successful records were marked as imported.