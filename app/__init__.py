from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os
from pathlib import Path
from config import config

db = SQLAlchemy()
migrate = Migrate()

def create_app(config_name=None):
    """Фабрика приложений Flask"""
    
    # ИСПРАВЛЕНИЕ: Указываем Flask где искать static папку
    # static_folder указывает относительно root_path приложения
    # Поскольку app находится в подпапке, нужно подняться на уровень выше
    app = Flask(__name__, 
                static_folder='../static',  # Поднимаемся из app/ в корень проекта
                static_url_path='/static')
    
    # Отладочная информация
    print("🔍 ОТЛАДКА СТАТИЧЕСКИХ ФАЙЛОВ:")
    print(f"   app.root_path: {app.root_path}")
    print(f"   app.static_folder: {app.static_folder}")
    print(f"   app.static_url_path: {app.static_url_path}")
    
    # Используем pathlib для безопасной работы с путями
    root_path = Path(app.root_path)
    static_folder = Path(app.static_folder) if app.static_folder else root_path / 'static'
    
    print(f"   Путь к static (pathlib): {static_folder.absolute()}")
    print(f"   Static папка существует: {static_folder.exists()}")
    
    if static_folder.exists():
        css_path = static_folder / 'css'
        print(f"   CSS папка существует: {css_path.exists()}")
        if css_path.exists():
            try:
                css_files = [f.name for f in css_path.iterdir() if f.is_file() and f.suffix == '.css']
                print(f"   CSS файлы найдены: {css_files}")
            except Exception as e:
                print(f"   Ошибка чтения CSS папки: {e}")
    else:
        print("   ❌ Static папка не найдена!")
    
    # Определяем конфигурацию
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'default')
    
    # Загружаем конфигурацию
    config_class = config[config_name]
    app.config.from_object(config_class)
    
    # Инициализируем приложение (создаем папки)
    config_class.init_app(app)
    
    # Инициализация расширений
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Регистрация маршрутов
    from app.routes import bp as main_bp
    app.register_blueprint(main_bp)
    
    # Регистрация CLI команд
    from commands import init_app
    init_app(app)
    
    return app