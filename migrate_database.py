#!/usr/bin/env python3
"""
Исправление SQLite базы данных - пересоздание таблицы
"""
import sqlite3
import os

def fix_sqlite_database():
    """Исправляем базу данных через пересоздание таблицы"""
    db_path = "database/kadastr.db"
    
    if not os.path.exists(db_path):
        print("❌ База данных не найдена")
        return False
    
    print("🔧 Исправляю SQLite базу данных...")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Создаем новую таблицу с правильной структурой
        print("   📋 Создаю новую таблицу...")
        cursor.execute('''
            CREATE TABLE info_client_new (
                id INTEGER PRIMARY KEY,
                sur_name TEXT NOT NULL,
                name TEXT NOT NULL,
                middle_name TEXT,
                telefone TEXT,
                path_folder TEXT,
                service INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 2. Копируем данные из старой таблицы
        print("   📊 Копирую данные...")
        cursor.execute('''
            INSERT INTO info_client_new 
            (id, sur_name, name, middle_name, telefone, path_folder, service, created_at)
            SELECT id, sur_name, name, middle_name, telefone, path_folder, service, 
                   datetime('now') as created_at
            FROM info_client
        ''')
        
        # 3. Удаляем старую таблицу
        print("   🗑️  Удаляю старую таблицу...")
        cursor.execute('DROP TABLE info_client')
        
        # 4. Переименовываем новую таблицу
        print("   🔄 Переименовываю таблицу...")
        cursor.execute('ALTER TABLE info_client_new RENAME TO info_client')
        
        conn.commit()
        conn.close()
        
        print("✅ База данных успешно исправлена!")
        print("▶️  Теперь можете запустить: python run.py")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def simple_add_column():
    """Простое добавление колонки без DEFAULT"""
    db_path = "database/kadastr.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Добавляем колонку без DEFAULT
        cursor.execute('ALTER TABLE info_client ADD COLUMN created_at DATETIME')
        
        # Устанавливаем значения для всех записей
        cursor.execute("UPDATE info_client SET created_at = datetime('now')")
        
        conn.commit()
        conn.close()
        
        print("✅ Колонка добавлена простым способом!")
        return True
        
    except Exception as e:
        if "duplicate column" in str(e):
            print("✅ Колонка уже существует")
            return True
        print(f"❌ Ошибка: {e}")
        return False

def main():
    print("🛠️  Исправление SQLite базы данных")
    print("=" * 40)
    
    print("Выберите способ исправления:")
    print("1. Простое добавление колонки")
    print("2. Пересоздание таблицы (безопасно)")
    print("3. Выход")
    
    choice = input("\nВаш выбор (1-3): ").strip()
    
    if choice == '1':
        simple_add_column()
    elif choice == '2':
        fix_sqlite_database()
    elif choice == '3':
        print("👋 До свидания!")
    else:
        print("❌ Неверный выбор")

if __name__ == '__main__':
    main()