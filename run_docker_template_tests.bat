@echo off
setlocal

docker info >nul 2>&1
if errorlevel 1 (
  echo Docker Desktop is not running. Start Docker Desktop and run this file again.
  pause
  exit /b 1
)

set "PYTEST_ARGS=tests/test_template_catalog_filters.py tests/test_day_template_logic.py tests/test_empty_day_template_service.py tests/test_template_controller.py tests/test_template_cards.py"
docker compose --profile test up --build --abort-on-container-exit --exit-code-from tests tests
set "EXIT_CODE=%ERRORLEVEL%"

docker compose --profile test down >nul 2>&1

if not "%EXIT_CODE%"=="0" (
  echo Template test suite failed with exit code %EXIT_CODE%.
  pause
  exit /b %EXIT_CODE%
)

echo Template test suite passed.
pause
exit /b 0
