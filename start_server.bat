@echo off
title AGNES PNP Server
cd /d C:\github\Nov-26-25\MIT_PROJECTS
call venv\Scripts\activate.bat
echo.
echo ========================================
echo   AGNES PNP Server Starting...
echo ========================================
echo.
python manage.py runserver
pause
