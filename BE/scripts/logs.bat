@echo off
echo Outvox System Logs
echo.
echo Select an option:
echo 1. All services
echo 2. Load balancer only
echo 3. Specific agent (1-10)
echo 4. Real-time logs (follow)
echo.
set /p choice="Enter your choice (1-4): "

if "%choice%"=="1" (
    docker-compose logs
) else if "%choice%"=="2" (
    docker-compose logs nginx-proxy
) else if "%choice%"=="3" (
    set /p agent="Enter agent number (1-10): "
    docker-compose logs outvox-agent%agent%
) else if "%choice%"=="4" (
    echo Press Ctrl+C to stop following logs
    docker-compose logs -f
) else (
    echo Invalid choice
)

echo.
pause
