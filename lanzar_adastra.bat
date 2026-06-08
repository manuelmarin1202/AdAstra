@echo off
title AdAstra GS v2.0 — Lanzador
echo.
echo  =========================================
echo   ADASTRA GROUND STATION  v2.0.0 - PUCP
echo   Telemetria en Tiempo Real - ESP32
echo  =========================================
echo.
echo  [1/2] Iniciando servidor Streamlit...
start "" python -m streamlit run "%~dp0adastra_dashboard.py" --server.headless false
echo  [2/2] Esperando 4 segundos...
timeout /t 4 /nobreak > nul
echo  [3/3] Abriendo interfaz en modo app...
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --app=http://localhost:8501 --start-fullscreen
echo.
echo  Dashboard activo en http://localhost:8501
echo  Puerto serial: Auto-deteccion | 115200 baud
echo  Cierra esta ventana cuando termines.
pause
