#!/usr/bin/env python3
"""
Прямая проверка базы данных без Flask кэша
"""
import sqlite3
import os

def direct_count_check():
    """Прямая проверка количества записей"""
    db_path = "kadastr.db"
    
    if not os.path.exists(db_path):
        print("❌ База данных не найдена")
        return
    
    print("🔍 Прямая проверка базы данных")
    print("=" * 40)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Простой подсчет всех клиентов
        cursor.execute("SELECT COUNT(*) FROM info_client")
        total_clients = cursor.fetchone()[0]
        print(f"📊 Всего клиентов в info_client: {total_clients}")
        
        # 2. Подсчет с проверкой created_at
        cursor.execute("SELECT COUNT(*) FROM info_client WHERE created_at IS NOT NULL")
        clients_with_date = cursor.fetchone()[0]
        print(f"📅 Клиентов с created_at: {clients_with_date}")
        
        cursor.execute("SELECT COUNT(*) FROM info_client WHERE created_at IS NULL")
        clients_without_date = cursor.fetchone()[0]
        print(f"❌ Клиентов без created_at: {clients_without_date}")
        
        # 3. Проверяем первые 10 записей
        cursor.execute("SELECT id, sur_name, name, created_at FROM info_client LIMIT 10")
        sample_clients = cursor.fetchall()
        print(f"\n📋 Первые 10 клиентов:")
        for client in sample_clients:
            print(f"   ID: {client[0]}, {client[1]} {client[2]}, дата: {client[3]}")
        
        # 4. Проверяем последние 10 записей
        cursor.execute("SELECT id, sur_name, name, created_at FROM info_client ORDER BY id DESC LIMIT 10")
        last_clients = cursor.fetchall()
        print(f"\n📋 Последние 10 клиентов:")
        for client in last_clients:
            print(f"   ID: {client[0]}, {client[1]} {client[2]}, дата: {client[3]}")
        
        # 5. Проверяем JOIN запросы как в приложении
        cursor.execute('''
            SELECT COUNT(*) FROM info_client c
            LEFT JOIN address_info_client a ON c.id = a.id_client
            LEFT JOIN city ci ON a.id_city = ci.id
        ''')
        join_count = cursor.fetchone()[0]
        print(f"\n🔗 С LEFT JOIN (address + city): {join_count}")
        
        cursor.execute('''
            SELECT COUNT(*) FROM info_client c
            INNER JOIN address_info_client a ON c.id = a.id_client
            INNER JOIN city ci ON a.id_city = ci.id
        ''')
        inner_join_count = cursor.fetchone()[0]
        print(f"🔗 С INNER JOIN (address + city): {inner_join_count}")
        
        # 6. Проверяем клиентов без адресов
        cursor.execute('''
            SELECT COUNT(*) FROM info_client c
            LEFT JOIN address_info_client a ON c.id = a.id_client
            WHERE a.id_client IS NULL
        ''')
        no_address = cursor.fetchone()[0]
        print(f"❌ Клиентов без адресов: {no_address}")
        
        # 7. Показываем клиентов без адресов
        if no_address > 0:
            cursor.execute('''
                SELECT c.id, c.sur_name, c.name FROM info_client c
                LEFT JOIN address_info_client a ON c.id = a.id_client
                WHERE a.id_client IS NULL
                LIMIT 5
            ''')
            no_addr_clients = cursor.fetchall()
            print(f"\n❌ Примеры клиентов без адресов:")
            for client in no_addr_clients:
                print(f"   ID: {client[0]}, {client[1]} {client[2]}")
        
        conn.close()
        
        print(f"\n💡 Выводы:")
        print(f"   - Всего клиентов: {total_clients}")
        print(f"   - С адресами и городами (INNER JOIN): {inner_join_count}")
        print(f"   - Разница: {total_clients - inner_join_count}")
        
        if total_clients != inner_join_count:
            print(f"   ⚠️ Flask показывает {inner_join_count} потому что использует INNER JOIN")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == '__main__':
    direct_count_check()