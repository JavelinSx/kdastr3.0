#!/usr/bin/env python3
"""
Исправление адресов с несуществующими городами
"""
import sqlite3
import os

def fix_orphaned_addresses():
    """Исправляем адреса с несуществующими городами"""
    db_path = "kadastr.db"
    
    if not os.path.exists(db_path):
        print("❌ База данных не найдена")
        return False
    
    print("🔧 Исправляю адреса с несуществующими городами...")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Найдем адреса с несуществующими городами
        print("   🔍 Ищу проблемные адреса...")
        cursor.execute('''
            SELECT a.id, a.id_client, a.id_city, a.address
            FROM address_info_client a
            LEFT JOIN city c ON a.id_city = c.id
            WHERE c.id IS NULL
        ''')
        
        orphaned_addresses = cursor.fetchall()
        
        if not orphaned_addresses:
            print("✅ Проблемных адресов не найдено")
            conn.close()
            return True
        
        print(f"   ❌ Найдено {len(orphaned_addresses)} проблемных адресов:")
        for addr in orphaned_addresses:
            print(f"      ID: {addr[0]}, Клиент: {addr[1]}, Несуществующий город: {addr[2]}, Адрес: {addr[3]}")
        
        # 2. Создаем "неизвестный" город если его нет
        cursor.execute("SELECT id FROM city WHERE city_name = 'Неизвестный'")
        unknown_city = cursor.fetchone()
        
        if not unknown_city:
            print("   📍 Создаю город 'Неизвестный'...")
            cursor.execute("INSERT INTO city (city_name) VALUES ('Неизвестный')")
            unknown_city_id = cursor.lastrowid
        else:
            unknown_city_id = unknown_city[0]
        
        print(f"   📍 ID города 'Неизвестный': {unknown_city_id}")
        
        # 3. Исправляем проблемные адреса
        print("   🔧 Исправляю проблемные адреса...")
        cursor.execute('''
            UPDATE address_info_client 
            SET id_city = ? 
            WHERE id_city NOT IN (SELECT id FROM city)
        ''', (unknown_city_id,))
        
        fixed_count = cursor.rowcount
        print(f"   ✅ Исправлено адресов: {fixed_count}")
        
        # 4. Проверяем результат
        cursor.execute('''
            SELECT COUNT(*) FROM address_info_client a
            LEFT JOIN city c ON a.id_city = c.id
            WHERE c.id IS NULL
        ''')
        
        remaining_orphans = cursor.fetchone()[0]
        
        if remaining_orphans == 0:
            print("✅ Все адреса исправлены!")
        else:
            print(f"⚠️ Остались проблемные адреса: {remaining_orphans}")
        
        conn.commit()
        conn.close()
        
        print("✅ Исправление завершено!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def check_client_count():
    """Проверяем количество клиентов после исправления"""
    db_path = "kadastr.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Подсчитываем клиентов разными способами
        cursor.execute("SELECT COUNT(*) FROM info_client")
        total_clients = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(*) FROM info_client c
            LEFT JOIN address_info_client a ON c.id = a.id_client
            LEFT JOIN city ci ON a.id_city = ci.id
            WHERE ci.id IS NOT NULL
        ''')
        clients_with_valid_addresses = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(*) FROM info_client c
            LEFT JOIN address_info_client a ON c.id = a.id_client
        ''')
        clients_with_addresses = cursor.fetchone()[0]
        
        print(f"\n📊 Статистика клиентов:")
        print(f"   Всего клиентов: {total_clients}")
        print(f"   Клиентов с адресами: {clients_with_addresses}")
        print(f"   Клиентов с валидными адресами: {clients_with_valid_addresses}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка подсчета: {e}")

def main():
    print("🛠️ Исправление проблемных адресов")
    print("=" * 40)
    
    if fix_orphaned_addresses():
        check_client_count()
        print("\n▶️ Теперь запустите приложение: python run.py")
    else:
        print("❌ Исправление не удалось")

if __name__ == '__main__':
    main()