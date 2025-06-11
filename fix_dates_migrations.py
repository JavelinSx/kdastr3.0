#!/usr/bin/env python3
"""
Исправление created_at - используем date_status как дату записи клиента
"""
import sqlite3
import os
from datetime import datetime

def fix_created_at_from_date_status():
    """Переносим date_status в created_at как основную дату записи"""
    db_path = "kadastr.db"
    
    if not os.path.exists(db_path):
        print("❌ База данных не найдена")
        return False
    
    print("🔧 Исправление created_at из date_status")
    print("=" * 50)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Проверяем текущее состояние
        cursor.execute("SELECT COUNT(*) FROM info_client")
        total_clients = cursor.fetchone()[0]
        print(f"📊 Всего клиентов: {total_clients}")
        
        # 2. Показываем текущие даты
        cursor.execute("""
            SELECT c.id, c.sur_name, c.created_at, w.date_status, w.date_work 
            FROM info_client c
            LEFT JOIN work_info_client w ON c.id = w.id_client
            ORDER BY c.id
            LIMIT 5
        """)
        examples = cursor.fetchall()
        print(f"\n📋 Примеры ТЕКУЩИХ дат:")
        for ex in examples:
            print(f"   ID {ex[0]} ({ex[1]}): created_at={ex[2]}, date_status={ex[3]}, date_work={ex[4]}")
        
        # 3. Основная логика: date_status = дата записи клиента
        print(f"\n🔄 Обновляю created_at из date_status (основная дата записи)...")
        
        # Переносим date_status в created_at
        cursor.execute("""
            UPDATE info_client 
            SET created_at = (
                SELECT CASE 
                    WHEN w.date_status IS NOT NULL AND w.date_status != '' AND w.date_status LIKE '__.__.__'
                    THEN datetime(
                        substr(w.date_status, 7, 4) || '-' || 
                        substr(w.date_status, 4, 2) || '-' || 
                        substr(w.date_status, 1, 2) || ' ' ||
                        CASE 
                            WHEN w.status = 1 THEN '14:00:00'  -- Готовые работы - дневное время
                            ELSE '09:00:00'                    -- В разработке - утреннее время  
                        END
                    )
                    ELSE datetime('now')  -- Если нет date_status, используем текущее время
                END
                FROM work_info_client w 
                WHERE w.id_client = info_client.id
            )
            WHERE EXISTS (
                SELECT 1 FROM work_info_client w 
                WHERE w.id_client = info_client.id
            )
        """)
        updated_count = cursor.rowcount
        print(f"✅ Обновлено записей: {updated_count}")
        
        # 4. Для клиентов без work_info_client (если такие есть)
        cursor.execute("""
            UPDATE info_client 
            SET created_at = datetime('now')
            WHERE id NOT IN (
                SELECT DISTINCT id_client FROM work_info_client WHERE id_client IS NOT NULL
            )
        """)
        orphaned_count = cursor.rowcount
        if orphaned_count > 0:
            print(f"⚠️ Клиентов без work_info (установлена текущая дата): {orphaned_count}")
        
        # 5. Проверяем результат
        cursor.execute("""
            SELECT c.id, c.sur_name, c.created_at, w.date_status, w.status
            FROM info_client c
            LEFT JOIN work_info_client w ON c.id = w.id_client
            ORDER BY c.created_at DESC
            LIMIT 10
        """)
        examples_after = cursor.fetchall()
        print(f"\n📋 Примеры ИСПРАВЛЕННЫХ дат (последние по created_at):")
        for ex in examples_after:
            status_text = "Готова" if ex[4] == 1 else "Разработка"
            print(f"   {ex[2]}: {ex[1]} (статус: {status_text})")
        
        # 6. Статистика по годам
        cursor.execute("""
            SELECT 
                strftime('%Y', created_at) as year,
                COUNT(*) as count
            FROM info_client 
            WHERE created_at IS NOT NULL
            GROUP BY strftime('%Y', created_at)
            ORDER BY year DESC
        """)
        yearly_stats = cursor.fetchall()
        print(f"\n📅 Статистика по годам:")
        for year_stat in yearly_stats:
            print(f"   {year_stat[0]}: {year_stat[1]} записей")
        
        # 7. Проверяем разнообразие дат
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT date(created_at)) as unique_dates,
                MIN(date(created_at)) as earliest_date,
                MAX(date(created_at)) as latest_date
            FROM info_client 
            WHERE created_at IS NOT NULL
        """)
        diversity = cursor.fetchone()
        print(f"\n📊 Разнообразие дат:")
        print(f"   Уникальных дат: {diversity[0]}")
        print(f"   Самая ранняя: {diversity[1]}")
        print(f"   Самая поздняя: {diversity[2]}")
        
        # 8. Топ дат по количеству
        cursor.execute("""
            SELECT 
                date(created_at) as date, 
                COUNT(*) as count
            FROM info_client 
            WHERE created_at IS NOT NULL
            GROUP BY date(created_at)
            ORDER BY count DESC
            LIMIT 5
        """)
        top_dates = cursor.fetchall()
        print(f"\n📅 Топ-5 дат по количеству записей:")
        for top_date in top_dates:
            print(f"   {top_date[0]}: {top_date[1]} записей")
        
        conn.commit()
        conn.close()
        
        print(f"\n✅ created_at успешно исправлен!")
        print(f"💡 Теперь created_at = date_status (дата записи клиента)")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def verify_flask_dates():
    """Проверяем как Flask видит даты после исправления"""
    print(f"\n🧪 Проверка Flask после исправления:")
    print("=" * 40)
    
    try:
        from app import create_app, db
        from app.models import Client
        
        app = create_app()
        with app.app_context():
            # Проверяем общее количество
            total = Client.query.count()
            print(f"📊 Всего клиентов в Flask: {total}")
            
            # Проверяем последние записи
            recent_clients = Client.query.order_by(Client.created_at.desc()).limit(10).all()
            print(f"📋 Последние 10 записей по дате:")
            for client in recent_clients:
                date_str = client.created_at.strftime('%d.%m.%Y') if client.created_at else 'Нет даты'
                print(f"   {date_str}: {client.full_name}")
            
            # Проверяем самые старые записи
            oldest_clients = Client.query.order_by(Client.created_at.asc()).limit(5).all()
            print(f"📋 Самые старые 5 записей:")
            for client in oldest_clients:
                date_str = client.created_at.strftime('%d.%m.%Y') if client.created_at else 'Нет даты'
                print(f"   {date_str}: {client.full_name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка Flask: {e}")
        return False

def main():
    print("🛠️ Исправление created_at из date_status")
    print("=" * 60)
    print("💡 date_status в исходном коде = дата записи клиента")
    print("💡 Это и есть правильная дата создания записи!")
    print()
    
    if fix_created_at_from_date_status():
        verify_flask_dates()
        print(f"\n▶️ Перезапустите приложение: python run.py")
        print(f"🎉 Теперь даты записи будут реальными!")
    else:
        print("❌ Не удалось исправить даты")

if __name__ == '__main__':
    main()