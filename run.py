#!/usr/bin/env python3
"""
Простой запуск приложения без debug режима
"""
import os
from pathlib import Path
from app import create_app, db

# Устанавливаем переменные окружения если они не заданы
if 'DATABASE_URL' not in os.environ:
    # Используем простой путь в корне проекта
    os.environ['DATABASE_URL'] = 'sqlite:///kadastr.db'

if 'WORK_FOLDER' not in os.environ:
    os.environ['WORK_FOLDER'] = './work_files'

if 'DOCS_FOLDER' not in os.environ:
    os.environ['DOCS_FOLDER'] = './docs'

# Отключаем debug режим
os.environ['FLASK_DEBUG'] = 'False'

def ensure_database_folder():
    """Убеждаемся что папка для базы данных существует"""
    # Получаем путь к базе данных из переменной окружения или используем по умолчанию
    db_url = os.environ.get('DATABASE_URL', 'sqlite:///database/kadastr.db')
    
    if db_url.startswith('sqlite:///'):
        db_path = db_url.replace('sqlite:///', '')
        
        # Если путь относительный, делаем его абсолютным
        if not os.path.isabs(db_path):
            db_path = os.path.abspath(db_path)
        
        # Создаем папку для базы данных
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir, exist_ok=True)
                print(f"📁 Создана папка для БД: {db_dir}")
            except Exception as e:
                print(f"❌ Ошибка создания папки БД {db_dir}: {e}")
                return False
        
        print(f"✅ Путь к БД: {db_path}")
        return True
    
    return True

def init_database(app):
    """Инициализация базы данных"""
    with app.app_context():
        from app.models import City
        
        try:
            # Создаем таблицы
            db.create_all()
            print("✅ Таблицы созданы")
            
            # Добавляем города если их нет
            if City.query.count() == 0:
                cities = ['Санкт-Петербург', 'Москва', 'Казань', 'Екатеринбург']
                for city_name in cities:
                    city = City(city_name)
                    db.session.add(city)
                db.session.commit()
                print(f"✅ Добавлено {len(cities)} городов")
            else:
                print("✅ Города уже существуют")
                
        except Exception as e:
            print(f"❌ Ошибка инициализации БД: {e}")
            print(f"🔍 Проверьте права доступа к папке базы данных")
            return False
            
        return True

if __name__ == '__main__':
    print("🚀 Запуск Кадастровой БД")
    print("=" * 30)
    
    # Создаем папку для базы данных ДО создания приложения
    if not ensure_database_folder():
        print("❌ Не удалось подготовить папку для базы данных")
        exit(1)
    
    # Создаем приложение
    app = create_app()
    
    # Инициализируем базу данных
    if init_database(app):
        print(f"🌐 Сервер запущен: http://127.0.0.1:5000")
        print("⏹️  Нажмите Ctrl+C для остановки")
        
        # Запускаем без debug
        app.run(
            debug=False,
            host='127.0.0.1',
            port=5000,
            use_reloader=False  # Отключаем перезагрузку
        )
    else:
        print("❌ Не удалось инициализировать базу данных")
        print("💡 Попробуйте:")
        print("   1. Проверить права доступа к папке")
        print("   2. Запустить от имени администратора")
        print("   3. Изменить путь к базе данных в настройках")