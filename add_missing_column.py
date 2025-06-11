#!/usr/bin/env python3
"""
Принудительное добавление колонки created_at
"""
import sqlite3
import os
from datetime import datetime

def force_add_created_at():
    """Принудительно добавляем колонку created_at"""
    db_path = "kadastr.db"
    
    if not os.path.exists(db_path):
        print("❌ База данных не найдена")
        return False
    
    print("🔧 Принудительное добавление колонки created_at")
    print("=" * 50)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Проверяем текущую структуру
        print("📋 Текущие колонки в info_client:")
        cursor.execute('PRAGMA table_info(info_client)')
        columns = cursor.fetchall()
        
        existing_columns = []
        for col in columns:
            print(f"   {col[1]} ({col[2]})")
            existing_columns.append(col[1])
        
        # 2. Проверяем есть ли created_at
        if 'created_at' in existing_columns:
            print("✅ Колонка created_at уже существует!")
            conn.close()
            return True
        
        # 3. Добавляем колонку
        print("\n🔨 Добавляю колонку created_at...")
        try:
            cursor.execute('ALTER TABLE info_client ADD COLUMN created_at DATETIME')
            print("✅ Колонка добавлена")
        except Exception as e:
            if "duplicate column" in str(e).lower():
                print("✅ Колонка уже существует (по ошибке)")
            else:
                raise e
        
        # 4. Заполняем значениями
        print("📅 Заполняю колонку датами...")
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("UPDATE info_client SET created_at = ? WHERE created_at IS NULL", (current_date,))
        updated_rows = cursor.rowcount
        print(f"✅ Обновлено записей: {updated_rows}")
        
        # 5. Проверяем результат
        cursor.execute('PRAGMA table_info(info_client)')
        columns_after = cursor.fetchall()
        print(f"\n📋 Колонки после добавления:")
        for col in columns_after:
            print(f"   {col[1]} ({col[2]})")
        
        # 6. Проверяем данные
        cursor.execute("SELECT COUNT(*) FROM info_client WHERE created_at IS NOT NULL")
        count_with_date = cursor.fetchone()[0]
        print(f"\n📊 Записей с датой: {count_with_date}")
        
        conn.commit()
        conn.close()
        
        print("✅ Колонка created_at успешно добавлена!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def test_flask_models():
    """Тестируем работу Flask моделей после добавления колонки"""
    print("\n🧪 Тестирование Flask моделей...")
    
    try:
        # Импортируем Flask модели
        import sys
        import os
        sys.path.append(os.getcwd())
        
        from app import create_app, db
        from app.models import Client
        
        # Создаем приложение
        app = create_app()
        
        with app.app_context():
            # Пробуем загрузить клиентов
            count = Client.query.count()
            print(f"✅ Flask видит клиентов: {count}")
            
            # Пробуем получить первых 5
            clients = Client.query.limit(5).all()
            print(f"✅ Загружено клиентов: {len(clients)}")
            
            for client in clients:
                print(f"   {client.id}: {client.full_name} (дата: {client.created_at})")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования Flask: {e}")
        return False

def main():
    print("🛠️ Исправление отсутствующей колонки created_at")
    print("=" * 60)
    
    if force_add_created_at():
        print("\n" + "=" * 60)
        test_flask_models()
        print("\n▶️ Теперь запустите: python run.py")
    else:
        print("❌ Не удалось добавить колонку")

if __name__ == '__main__':
    main()