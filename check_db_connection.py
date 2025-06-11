#!/usr/bin/env python3
"""
Проверка подключения к базе данных
"""
import os
import sys
import sqlite3

def check_database_paths():
    """Проверка всех возможных путей к БД"""
    print("🔍 Проверка путей к базе данных")
    print("=" * 50)
    
    # Текущая папка
    current_dir = os.getcwd()
    print(f"📁 Текущая папка: {current_dir}")
    
    # Переменные окружения
    print(f"🔧 DATABASE_URL: {os.environ.get('DATABASE_URL', 'НЕ УСТАНОВЛЕНА')}")
    
    # Возможные пути к БД
    possible_paths = [
        'kadastr.db',                           # В корне
        'database/kadastr.db',                  # В папке database
        os.path.join(current_dir, 'kadastr.db'), # Абсолютный путь к корню
        os.path.join(current_dir, 'database', 'kadastr.db'), # Абсолютный путь к database
    ]
    
    print(f"\n📂 Проверка файлов БД:")
    
    for path in possible_paths:
        abs_path = os.path.abspath(path)
        exists = os.path.exists(path)
        
        if exists:
            size = os.path.getsize(path)
            print(f"  ✅ {path} -> {abs_path} ({size} байт)")
            
            # Быстрая проверка содержимого
            try:
                conn = sqlite3.connect(path)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM info_client")
                count = cursor.fetchone()[0]
                conn.close()
                print(f"     📊 Клиентов в этом файле: {count}")
            except Exception as e:
                print(f"     ❌ Ошибка чтения: {e}")
        else:
            print(f"  ❌ {path} -> НЕ СУЩЕСТВУЕТ")

def check_flask_config():
    """Проверка конфигурации Flask"""
    print(f"\n🔧 Проверка конфигурации Flask:")
    
    try:
        sys.path.insert(0, '.')
        
        # Устанавливаем переменную окружения
        os.environ['DATABASE_URL'] = 'sqlite:///kadastr.db'
        
        from app import create_app
        
        app = create_app()
        
        print(f"📊 Конфигурация приложения:")
        print(f"  SQLALCHEMY_DATABASE_URI: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
        print(f"  SQLALCHEMY_TRACK_MODIFICATIONS: {app.config.get('SQLALCHEMY_TRACK_MODIFICATIONS')}")
        
        # Проверяем какой файл на самом деле используется
        db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        if db_uri.startswith('sqlite:///'):
            db_path_from_uri = db_uri.replace('sqlite:///', '')
            abs_db_path = os.path.abspath(db_path_from_uri)
            
            print(f"  📁 Путь к БД из конфига: {db_path_from_uri}")
            print(f"  📁 Абсолютный путь: {abs_db_path}")
            print(f"  📂 Файл существует: {os.path.exists(abs_db_path)}")
            
            if os.path.exists(abs_db_path):
                size = os.path.getsize(abs_db_path)
                print(f"  📏 Размер файла: {size} байт")
                
                # Проверяем содержимое файла, к которому подключается Flask
                try:
                    conn = sqlite3.connect(abs_db_path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM info_client")
                    count = cursor.fetchone()[0]
                    conn.close()
                    print(f"  📊 Клиентов в файле Flask: {count}")
                except Exception as e:
                    print(f"  ❌ Ошибка чтения файла Flask: {e}")
        
        return app
        
    except Exception as e:
        print(f"❌ Ошибка создания приложения: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_direct_flask_db():
    """Прямое тестирование Flask DB"""
    print(f"\n🧪 Прямое тестирование Flask DB:")
    
    app = check_flask_config()
    if not app:
        return
    
    try:
        from app import db
        from app.models import Client
        
        with app.app_context():
            # Принудительно подключаемся к БД
            print(f"  🔗 Создание подключения...")
            
            # Проверяем engine
            engine = db.engine
            print(f"  ⚙️ Engine URL: {engine.url}")
            
            # Пробуем прямое подключение
            with engine.connect() as connection:
                result = connection.execute(db.text("SELECT COUNT(*) FROM info_client"))
                count = result.scalar()
                print(f"  📊 Прямой запрос к engine: {count} клиентов")
                
                # Если count = 0, возможно таблица пустая или не существует
                if count == 0:
                    # Проверяем все таблицы
                    result = connection.execute(db.text("SELECT name FROM sqlite_master WHERE type='table'"))
                    tables = result.fetchall()
                    print(f"  📋 Таблицы в БД через engine: {[t[0] for t in tables]}")
                    
                    # Проверяем содержимое info_client
                    try:
                        result = connection.execute(db.text("SELECT * FROM info_client LIMIT 1"))
                        first_row = result.fetchone()
                        if first_row:
                            print(f"  📄 Первая запись info_client: {dict(first_row._mapping)}")
                        else:
                            print(f"  📄 Таблица info_client пуста")
                    except Exception as e:
                        print(f"  ❌ Ошибка чтения info_client: {e}")
        
    except Exception as e:
        print(f"❌ Ошибка тестирования Flask DB: {e}")
        import traceback
        traceback.print_exc()

def find_all_db_files():
    """Поиск всех .db файлов в проекте"""
    print(f"\n🔍 Поиск всех .db файлов:")
    
    db_files = []
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.db'):
                full_path = os.path.join(root, file)
                abs_path = os.path.abspath(full_path)
                size = os.path.getsize(full_path)
                
                db_files.append((full_path, abs_path, size))
    
    if db_files:
        print(f"  Найдено .db файлов: {len(db_files)}")
        for rel_path, abs_path, size in db_files:
            print(f"  📄 {rel_path} -> {abs_path} ({size} байт)")
            
            # Проверяем содержимое
            try:
                conn = sqlite3.connect(rel_path)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM info_client")
                count = cursor.fetchone()[0]
                conn.close()
                print(f"     📊 Клиентов: {count}")
            except Exception as e:
                print(f"     ❌ Ошибка: {e}")
    else:
        print(f"  ❌ .db файлы не найдены!")

def main():
    print("🔬 Диагностика подключения к базе данных")
    print("=" * 60)
    
    check_database_paths()
    find_all_db_files()
    test_direct_flask_db()
    
    print(f"\n💡 Следующие шаги:")
    print("1. Убедитесь что Flask подключается к правильному файлу")
    print("2. Проверьте что в этом файле есть данные")
    print("3. Если Flask подключается к пустому файлу - измените DATABASE_URL")

if __name__ == '__main__':
    main()