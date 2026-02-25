# Plan: Sync Job Resilience (Cache + Auto-Retry)

## 1. Objective
Improve the resilience of the Sync Job by implementing a local cache mechanism (Option C) and reinforcing the auto-retry logic (Option A). This ensures that if a sync job fails partially, subsequent runs will skip successful downloads and only attempt the failed ones, saving time and resources.

## 2. Technical Context
- **Downloads Directory**: Files downloaded by the browsers (`BaseBrowser`) are stored in `settings.DOWNLOADS_DIR`.
- **File Moving**: The `FileManager.move_downloads_to_data_dir()` method is called *only after* all downloads finish successfully. If a job fails midway, successfully downloaded files remain in `DOWNLOADS_DIR`.
- **Current Retry Logic**: `SyncService._execute_sync_logic` has a `run_download_task_with_retries` wrapper that retries a task up to 3 times before failing the whole job.

## 3. Proposed Changes

### 3.1. Implement Cache Validation Method (Option C)
Add a helper method `_is_download_cached(patterns, max_age_minutes)` in `app/services/sync_service.py` to check if valid files already exist in the `DOWNLOADS_DIR`.

- **Fiorilli Employees**: Requires a file with `trabalhador` in the name.
- **Fiorilli Leaves**: Requires *two* files, one with `pontoafastamentos` and another with `pontoferias`.
- **Ahgora Employees**: Requires a file with `funcionarios`.

If the required files exist and were modified within the `max_age_minutes` (e.g., 60 minutes), the download step is skipped.

### 3.2. Integrate Cache into Sync Logic
Modify `run_download_task_with_retries` in `app/services/sync_service.py` to receive the expected file `patterns`.
Before attempting the first browser download, it will call `_is_download_cached`.
- If `True`: Log a cache hit message and return `True` immediately.
- If `False`: Proceed with the normal browser automation and its existing auto-retry loop.

### 3.3. Enhance Auto-Retry (Option A)
The current `run_download_task_with_retries` already does 3 attempts. We will:
- Increase the delay between retries slightly to handle temporary portal instabilities better (e.g., from 2 seconds to 10 seconds).
- Ensure the logs explicitly state when a download is being skipped due to caching vs. when it is being retried.

## 4. Verification Plan
- **Manual Verification**:
  1. Trigger a sync job.
  2. While it's downloading the first file, forcefully kill the job or cause the second download to fail.
  3. Verify that the first downloaded file is in `downloads/`.
  4. Trigger a new sync job.
  5. Check the logs to ensure the first download was *skipped* (cache hit) and it only opened the browser for the remaining files.
- **Automated Checks**: Run `checklist.py .` or `ruff check .` to verify code quality.