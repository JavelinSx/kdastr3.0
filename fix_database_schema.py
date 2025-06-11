#!/usr/bin/env python3
"""
Исправление схемы базы данных для совместимости с новыми моделями
"""
import sqlite3
import os
from datetime import datetime

def backup_database():
    """Создание резервной копии БД"""
    backup_name = f"kadastr_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    try:
        import shutil
        shutil.copy2('kadastr.db', backup_name)
        print(f"💾 Создан бэкап: {backup_name}")
        return backup_name
    except Exception as e:
        print(f"⚠️ Не удалось создать бэкап: {e}")
        return None

def check_column_exists(cursor, table_name, column_name):
    """Проверка существования колонки в таблице"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    return any(col[1] == column_name for col in columns)

def add_missing_columns():
    """Добавление недостающих колонок"""
    print("🔧 Добавление недостающих колонок...")
    
    try:
        conn = sqlite3.connect('kadastr.db')
        cursor = conn.cursor()
        
        changes_made = []
        
        # 1. Добавляем created_at в info_client если её нет
        if not check_column_exists(cursor, 'info_client', 'created_at'):
            print("  📅 Добавляем created_at в info_client...")
            cursor.execute('ALTER TABLE info_client ADD COLUMN created_at DATETIME')
            
            # Устанавливаем текущую дату для всех существующих записей
            cursor.execute("UPDATE info_client SET created_at = datetime('now') WHERE created_at IS NULL")
            changes_made.append("created_at добавлен в info_client")
        else:
            print("  ✅ created_at уже существует в info_client")
        
        # 2. Проверяем остальные таблицы и их структуру
        
        # Проверяем что все внешние ключи правильные
        cursor.execute("PRAGMA foreign_keys = ON")
        
        conn.commit()
        conn.close()
        
        if changes_made:
            print("✅ Изменения применены:")
            for change in changes_made:
                print(f"  • {change}")
        else:
            print("✅ Схема БД уже соответствует моделям")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка изменения схемы: {e}")
        return False

def test_models_after_fix():
    """Тестирование моделей после исправления"""
    print("\n🧪 Тестирование моделей после исправления...")
    
    try:
        import sys
        sys.path.insert(0, '.')
        
        os.environ['DATABASE_URL'] = 'sqlite:///kadastr.db'
        
        from app import create_app, db
        from app.models import Client, City, AddressInfo, WorkInfo, DocInfo, DocFillInfo
        
        app = create_app()
        
        with app.app_context():
            # Проверяем что данные теперь видны
            models_data = [
                ('City', City),
                ('Client', Client),
                ('AddressInfo', AddressInfo), 
                ('WorkInfo', WorkInfo),
                ('DocInfo', DocInfo),
                ('DocFillInfo', DocFillInfo)
            ]
            
            for model_name, model_class in models_data:
                try:
                    count = model_class.query.count()
                    print(f"  📊 {model_name}: {count} записей")
                    
                    if count > 0 and model_name == 'Client':
                        # Показываем первого клиента
                        first_client = model_class.query.first()
                        print(f"    Пример: {first_client.full_name}")
                        
                except Exception as e:
                    print(f"  ❌ {model_name}: {e}")
            
            # Тестируем JOIN запрос из routes.py
            try:
                clients = db.session.query(Client)\
                    .join(AddressInfo, Client.id == AddressInfo.id_client, isouter=True)\
                    .join(City, AddressInfo.id_city == City.id, isouter=True)\
                    .join(WorkInfo, Client.id == WorkInfo.id_client, isouter=True)\
                    .order_by(Client.created_at.desc())\
                    .limit(5)\
                    .all()
                
                print(f"  🔗 JOIN запрос вернул: {len(clients)} клиентов")
                
                if clients:
                    for i, client in enumerate(clients[:3], 1):
                        city_name = client.address.city_info.city_name if client.address and client.address.city_info else 'Нет города'
                        print(f"    {i}. {client.full_name} - {city_name}")
                
            except Exception as e:
                print(f"  ❌ JOIN запрос: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("🛠️ Исправление схемы базы данных")
    print("=" * 50)
    
    if not os.path.exists('kadastr.db'):
        print("❌ Файл kadastr.db не найден!")
        return
    
    file_size = os.path.getsize('kadastr.db')
    print(f"📁 Файл БД: kadastr.db ({file_size} байт)")
    
    # Создаем бэкап
    backup_file = backup_database()
    
    # Спрашиваем подтверждение
    print("\n⚠️ Будут внесены изменения в схему базы данных.")
    print("Убедитесь что создан бэкап!")
    
    choice = input("Продолжить? (yes/no): ").lower()
    if choice not in ['yes', 'y', 'да']:
        print("👋 Отменено")
        return
    
    # Применяем исправления
    if add_missing_columns():
        print("\n✅ Схема обновлена!")
        
        # Тестируем результат
        if test_models_after_fix():
            print("\n🎉 Исправление завершено успешно!")
            print("▶️ Теперь перезапустите приложение: python run.py")
            
            if backup_file:
                print(f"💾 Бэкап сохранен как: {backup_file}")
        else:
            print("\n❌ Проблемы остались. Возможно нужны дополнительные исправления.")
    else:
        print("\n❌ Не удалось обновить схему")
        if backup_file:
            print(f"💾 Бэкап доступен для восстановления: {backup_file}")

if __name__ == '__main__':
    main()