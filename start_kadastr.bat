@echo off
echo Запуск Кадастровой системы...
cd /d "D:\Kadastr\kdastr3.0-main"
call venv\Scripts\activate
python run.py
pause