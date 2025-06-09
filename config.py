import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# Базовая папка проекта
basedir = Path(__file__).resolve().parent

def get_database_path():
    """Получить путь к базе данных из настроек"""
    db_url = os.environ.get('DATABASE_URL')
    if db_url and db_url.startswith('sqlite:///'):
        db_path = db_url.replace('sqlite:///', '')
        # Если путь относительный, делаем его абсолютным относительно basedir
        if not os.path.isabs(db_path):
            return basedir / db_path
        return Path(db_path)
    else:
        # Значение по умолчанию
        return basedir / "database" / "kadastr.db"

def get_folder_path(env_var, default_relative_path):
    """Получить путь к папке из настроек"""
    folder_path = os.environ.get(env_var, default_relative_path)
    # Если путь относительный, делаем его абсолютным относительно basedir
    if not os.path.isabs(folder_path):
        return basedir / folder_path
    return Path(folder_path)

class Config:
    """Базовая конфигурация"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # База данных - используем динамический путь
    _db_path = get_database_path()
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'sqlite:///{_db_path}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Загрузка файлов
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # Папки проекта - используем динамические пути
    UPLOAD_FOLDER = get_folder_path('UPLOAD_FOLDER', 'uploads')
    DOCS_FOLDER = get_folder_path('DOCS_FOLDER', 'docs')
    WORK_FOLDER = get_folder_path('WORK_FOLDER', 'work_files')
    
    # Настройки Flask
    FLASK_DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    @staticmethod
    def init_app(app):
        """Инициализация приложения с созданием необходимых папок"""
        # Создаем необходимые папки
        folders_to_create = [
            app.config['UPLOAD_FOLDER'],
            app.config['DOCS_FOLDER'], 
            app.config['WORK_FOLDER']
        ]
        
        for folder in folders_to_create:
            try:
                os.makedirs(folder, exist_ok=True)
                print(f"✅ Папка готова: {folder}")
            except Exception as e:
                print(f"⚠️ Ошибка создания папки {folder}: {e}")
        
        # Создаем папку для базы данных
        db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        if db_path and '/' in db_path or '\\' in db_path:
            db_dir = os.path.dirname(db_path)
            try:
                os.makedirs(db_dir, exist_ok=True)
                print(f"✅ Папка БД готова: {db_dir}")
            except Exception as e:
                print(f"⚠️ Ошибка создания папки БД {db_dir}: {e}")

class DevelopmentConfig(Config):
    """Конфигурация для разработки"""
    DEBUG = True

class ProductionConfig(Config):
    """Конфигурация для продакшена"""
    DEBUG = False
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'change-me-in-production'

class TestingConfig(Config):
    """Конфигурация для тестов"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

# Словарь конфигураций
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}