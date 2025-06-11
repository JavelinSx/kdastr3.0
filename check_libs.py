#!/usr/bin/env python3
"""
Скрипт для проверки установленных библиотек
"""
import sys
import subprocess

def check_library(lib_name):
    """Проверка наличия библиотеки"""
    try:
        __import__(lib_name)
        print(f"✅ {lib_name} - УСТАНОВЛЕНА")
        return True
    except ImportError as e:
        print(f"❌ {lib_name} - НЕ НАЙДЕНА: {e}")
        return False

def get_installed_packages():
    """Получить список установленных пакетов"""
    try:
        result = subprocess.run([sys.executable, '-m', 'pip', 'list'], 
                              capture_output=True, text=True)
        return result.stdout
    except Exception as e:
        print(f"Ошибка получения списка пакетов: {e}")
        return ""

def main():
    print("🔍 Проверка библиотек для работы с документами")
    print("=" * 50)
    
    print(f"Python executable: {sys.executable}")
    print(f"Python version: {sys.version}")
    print()
    
    # Проверяем основные библиотеки
    libraries = ['docxtpl', 'openpyxl', 'flask', 'sqlalchemy']
    
    all_ok = True
    for lib in libraries:
        if not check_library(lib):
            all_ok = False
    
    print()
    print("📦 Установленные пакеты (фильтр по docx и openpyxl):")
    packages = get_installed_packages()
    for line in packages.split('\n'):
        if any(word in line.lower() for word in ['docx', 'openpyxl', 'excel']):
            print(f"  {line}")
    
    print()
    if all_ok:
        print("✅ Все необходимые библиотеки установлены!")
    else:
        print("❌ Некоторые библиотеки отсутствуют")
        print("Выполните: pip install docxtpl openpyxl")
    
    # Проверяем конкретно функции
    print("\n🧪 Тестирование импортов:")
    try:
        from docxtpl import DocxTemplate
        print("✅ DocxTemplate импортирован успешно")
    except ImportError as e:
        print(f"❌ Ошибка импорта DocxTemplate: {e}")
    
    try:
        import openpyxl
        wb = openpyxl.Workbook()
        print("✅ openpyxl работает")
        wb.close()
    except ImportError as e:
        print(f"❌ Ошибка импорта openpyxl: {e}")
    except Exception as e:
        print(f"❌ Ошибка работы с openpyxl: {e}")

if __name__ == '__main__':
    main()