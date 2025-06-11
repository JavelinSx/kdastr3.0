#!/usr/bin/env python3
"""
Диагностика системы перед запуском
"""
import os
import sys
from pathlib import Path
import sqlite3

def check_permissions():
    """Проверка прав доступа"""
    print("\n🔍 Проверка прав доступа:")
    
    current_dir = os.getcwd()
    print(f"📁 Текущая папка: {current_dir}")
    
    # Проверяем права на чтение и запись
    if os.access(current_dir, os.R_OK):
        print("✅ Права на чтение: есть")
    else:
        print("❌ Права на чтение: нет")
        return False
    
    if os.access(current_dir, os.W_OK):
        print("✅ Права на запись: есть")
    else:
        print("❌ Права на запись: нет")
        return False
    
    return True

def check_database():
    """Проверка базы данных"""
    print("\n🗄️ Проверка базы данных:")
    
    # Получаем путь к БД
    db_url = os.environ.get('DATABASE_URL', 'sqlite:///database/kadastr.db')
    if db_url.startswith('sqlite:///'):
        db_path = db_url.replace('sqlite:///', '')
        if not os.path.isabs(db_path):
            db_path = os.path.abspath(db_path)
        
        print(f"📍 Путь к БД: {db_path}")
        
        # Проверяем папку
        db_dir = os.path.dirname(db_path)
        if not os.path.exists(db_dir):
            print(f"📁 Создаем папку: {db_dir}")
            try:
                os.makedirs(db_dir, exist_ok=True)
                print("✅ Папка создана")
            except Exception as e:
                print(f"❌ Ошибка создания папки: {e}")
                return False
        
        # Пробуем создать/открыть БД
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            conn.close()
            
            if tables:
                print(f"✅ БД существует, таблиц: {len(tables)}")
            else:
                print("📝 БД пуста, будет инициализирована")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка работы с БД: {e}")
            return False
    
    return True

def check_folders():
    """Проверка рабочих папок"""
    print("\n📂 Проверка рабочих папок:")
    
    folders = {
        'work_files': './work_files',
        'docs': './docs', 
        'uploads': './uploads',
        'database': './database'
    }
    
    for name, path in folders.items():
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            print(f"✅ {name}: {abs_path}")
        else:
            print(f"📁 Создаем {name}: {abs_path}")
            try:
                os.makedirs(abs_path, exist_ok=True)
                print(f"✅ {name} создана")
            except Exception as e:
                print(f"❌ Ошибка создания {name}: {e}")
                return False
    
    return True

def check_dependencies():
    """Проверка зависимостей"""
    print("\n📦 Проверка зависимостей:")
    
    # Обязательные пакеты (имя_пакета: имя_модуля)
    required_packages = {
        'flask': 'flask',
        'flask-sqlalchemy': 'flask_sqlalchemy', 
        'flask-migrate': 'flask_migrate',
        'flask-wtf': 'flask_wtf',
        'wtforms': 'wtforms'
    }
    
    # Опциональные пакеты
    optional_packages = {
        'python-dotenv': 'dotenv',
        'docxtpl': 'docxtpl', 
        'openpyxl': 'openpyxl'
    }
    
    missing_required = []
    missing_optional = []
    
    # Проверяем обязательные
    for package_name, module_name in required_packages.items():
        try:
            __import__(module_name)
            print(f"✅ {package_name} (обязательный)")
        except ImportError:
            print(f"❌ {package_name} (обязательный)")
            missing_required.append(package_name)
    
    # Проверяем опциональные
    for package_name, module_name in optional_packages.items():
        try:
            __import__(module_name)
            print(f"✅ {package_name} (опциональный)")
        except ImportError:
            print(f"⚠️ {package_name} (опциональный) - не установлен")
            missing_optional.append(package_name)
    
    if missing_required:
        print(f"\n💡 Установите обязательные пакеты:")
        print(f"pip install {' '.join(missing_required)}")
        return False
    
    if missing_optional:
        print(f"\n💡 Рекомендуется установить опциональные пакеты:")
        print(f"pip install {' '.join(missing_optional)}")
        print("(Приложение будет работать, но с ограниченной функциональностью)")
    
    return True

def main():
    """Основная функция диагностики"""
    print("🔧 Диагностика системы Кадастровой БД")
    print("=" * 40)
    
    checks = [
        ("Права доступа", check_permissions),
        ("Зависимости", check_dependencies), 
        ("Рабочие папки", check_folders),
        ("База данных", check_database)
    ]
    
    all_passed = True
    
    for check_name, check_func in checks:
        try:
            if not check_func():
                all_passed = False
                print(f"❌ {check_name}: ОШИБКА")
            else:
                print(f"✅ {check_name}: ОК")
        except Exception as e:
            print(f"❌ {check_name}: ИСКЛЮЧЕНИЕ - {e}")
            all_passed = False
    
    print("\n" + "=" * 40)
    if all_passed:
        print("🎉 Все проверки пройдены! Можно запускать приложение:")
        print("python run.py")
    else:
        print("⚠️ Найдены проблемы. Исправьте их перед запуском.")
    
    return all_passed

if __name__ == '__main__':
    main()