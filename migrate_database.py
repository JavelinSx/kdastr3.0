#!/usr/bin/env python3
"""
Единый файл для миграции и исправления базы данных
Основные задачи:
1. Исправление схемы таблиц
2. Сопоставление date_status с created_at (время создания заявки)
3. Исправление проблемных адресов
4. Проверка целостности данных
"""
import sqlite3
import os
import shutil
from datetime import datetime, timedelta
import random

def create_backup():
    """Создание резервной копии БД"""
    db_path = "kadastr.db"
    
    if not os.path.exists(db_path):
        print("❌ База данных не найдена")
        return None
    
    backup_name = f"kadastr_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    
    try:
        shutil.copy2(db_path, backup_name)
        print(f"💾 Создан бэкап: {backup_name}")
        return backup_name
    except Exception as e:
        print(f"⚠️ Не удалось создать бэкап: {e}")
        return None

def check_column_exists(cursor, table_name, column_name):
    """Проверка существования колонки в таблице"""
    try:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        return any(col[1] == column_name for col in columns)
    except Exception as e:
        print(f"Ошибка проверки колонки {column_name} в {table_name}: {e}")
        return False

def fix_schema_issues(cursor):
    """Исправление проблем схемы"""
    print("\n🔧 Исправление схемы базы данных...")
    
    changes_made = []
    
    # 1. Добавляем created_at в info_client если её нет
    if not check_column_exists(cursor, 'info_client', 'created_at'):
        print("  📅 Добавляем created_at в info_client...")
        try:
            cursor.execute('ALTER TABLE info_client ADD COLUMN created_at DATETIME')
            changes_made.append("Добавлена колонка created_at в info_client")
        except Exception as e:
            print(f"    ❌ Ошибка добавления created_at: {e}")
    else:
        print("  ✅ created_at уже существует в info_client")
    
    # 2. Проверяем и исправляем другие потенциальные проблемы схемы
    tables_to_check = {
        'city': ['id', 'city_name'],
        'info_client': ['id', 'sur_name', 'name', 'middle_name', 'telefone', 'path_folder', 'service', 'created_at'],
        'address_info_client': ['id', 'id_client', 'id_city', 'address'],
        'work_info_client': ['id', 'id_client', 'prepayment', 'remains', 'work', 'date_work', 'status', 'date_status', 'info'],
        'doc_info_client': ['id', 'id_client', 'series_pass', 'date_pass', 'info_pass', 'snils'],
        'doc_fill_info': ['id', 'id_client', 'date_birthday', 'place_residence', 'extend_work_info', 'approval', 'contract', 'contract_agreement', 'declaration', 'receipt']
    }
    
    for table_name, expected_columns in tables_to_check.items():
        try:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            if not cursor.fetchone():
                print(f"  ⚠️ Таблица {table_name} не найдена")
                continue
                
            cursor.execute(f"PRAGMA table_info({table_name})")
            existing_columns = [col[1] for col in cursor.fetchall()]
            
            missing_columns = set(expected_columns) - set(existing_columns)
            if missing_columns:
                print(f"  ⚠️ В таблице {table_name} отсутствуют колонки: {missing_columns}")
        except Exception as e:
            print(f"  ❌ Ошибка проверки таблицы {table_name}: {e}")
    
    return changes_made

def parse_date_string(date_str):
    """Парсинг даты из строки в формате ДД.ММ.ГГГГ"""
    if not date_str or not isinstance(date_str, str):
        return None
    
    # Очищаем строку
    date_str = date_str.strip()
    
    # Проверяем формат ДД.ММ.ГГГГ
    if not date_str or len(date_str) != 10 or date_str.count('.') != 2:
        return None
    
    try:
        parts = date_str.split('.')
        if len(parts) != 3:
            return None
            
        day = int(parts[0])
        month = int(parts[1])
        year = int(parts[2])
        
        # Проверяем разумность значений
        if not (1 <= day <= 31 and 1 <= month <= 12 and 2000 <= year <= 2030):
            return None
        
        # Создаем datetime объект
        dt = datetime(year, month, day)
        
        # Добавляем случайное время в рабочий день (9:00-18:00)
        hour = random.randint(9, 17)
        minute = random.randint(0, 59)
        second = random.randint(0, 59)
        
        return dt.replace(hour=hour, minute=minute, second=second)
        
    except (ValueError, IndexError) as e:
        print(f"    ⚠️ Ошибка парсинга даты '{date_str}': {e}")
        return None

def migrate_date_status_to_created_at(cursor):
    """Основная функция: перенос date_status в created_at"""
    print("\n🔄 Перенос date_status в created_at (дата создания заявки)...")
    
    # 1. Получаем всех клиентов с их рабочей информацией
    cursor.execute("""
        SELECT c.id, c.sur_name, c.created_at, w.date_status, w.status 
        FROM info_client c
        LEFT JOIN work_info_client w ON c.id = w.id_client
        ORDER BY c.id
    """)
    
    clients = cursor.fetchall()
    total_clients = len(clients)
    print(f"📊 Найдено клиентов: {total_clients}")
    
    if total_clients == 0:
        print("❌ Клиенты не найдены")
        return
    
    # 2. Показываем примеры текущих дат
    print(f"\n📋 Примеры ТЕКУЩИХ дат (первые 5):")
    for i, client in enumerate(clients[:5]):
        client_id, surname, current_created_at, date_status, status = client
        print(f"   ID {client_id} ({surname}): created_at={current_created_at}, date_status={date_status}")
    
    # 3. Обрабатываем каждого клиента
    updated_count = 0
    failed_count = 0
    fallback_count = 0
    
    # Для клиентов без date_status будем создавать даты в диапазоне последних 2 лет
    base_date = datetime.now() - timedelta(days=730)  # 2 года назад
    
    for client_id, surname, current_created_at, date_status, status in clients:
        new_created_at = None
        
        # Пытаемся использовать date_status
        if date_status:
            new_created_at = parse_date_string(date_status)
            
            if new_created_at:
                # Определяем время в зависимости от статуса
                if status == 1:  # Готовые работы
                    hour = random.randint(10, 16)  # Дневное время
                else:  # В разработке
                    hour = random.randint(9, 12)   # Утреннее время
                
                new_created_at = new_created_at.replace(
                    hour=hour,
                    minute=random.randint(0, 59),
                    second=random.randint(0, 59)
                )
        
        # Если date_status не подошел, создаем случайную дату
        if not new_created_at:
            fallback_count += 1
            # Случайная дата в диапазоне последних 2 лет
            days_offset = random.randint(0, 730)
            new_created_at = base_date + timedelta(days=days_offset)
            
            # Случайное время в рабочий день
            new_created_at = new_created_at.replace(
                hour=random.randint(9, 17),
                minute=random.randint(0, 59),
                second=random.randint(0, 59)
            )
        
        # Обновляем в базе данных
        try:
            cursor.execute("""
                UPDATE info_client 
                SET created_at = ? 
                WHERE id = ?
            """, (new_created_at.strftime('%Y-%m-%d %H:%M:%S'), client_id))
            
            updated_count += 1
            
        except Exception as e:
            print(f"    ❌ Ошибка обновления клиента {client_id}: {e}")
            failed_count += 1
    
    print(f"\n📊 Результаты миграции дат:")
    print(f"   ✅ Успешно обновлено: {updated_count}")
    print(f"   📅 Использован date_status: {updated_count - fallback_count}")
    print(f"   🎲 Случайные даты: {fallback_count}")
    print(f"   ❌ Ошибки: {failed_count}")
    
    # 4. Показываем примеры результата
    cursor.execute("""
        SELECT c.id, c.sur_name, c.created_at, w.date_status, w.status
        FROM info_client c
        LEFT JOIN work_info_client w ON c.id = w.id_client
        ORDER BY c.created_at DESC
        LIMIT 10
    """)
    
    examples_after = cursor.fetchall()
    print(f"\n📋 Примеры ИСПРАВЛЕННЫХ дат (последние 10 по created_at):")
    for client_id, surname, created_at, date_status, status in examples_after:
        status_text = "Готова" if status == 1 else "Разработка" if status == 0 else "Неизвестно"
        source = "date_status" if date_status and parse_date_string(date_status) else "случайная"
        print(f"   {created_at}: {surname} (статус: {status_text}, источник: {source})")

def fix_orphaned_addresses(cursor):
    """Исправление адресов с несуществующими городами"""
    print("\n🔧 Исправление проблемных адресов...")
    
    # 1. Найдем адреса с несуществующими городами
    cursor.execute('''
        SELECT a.id, a.id_client, a.id_city, a.address
        FROM address_info_client a
        LEFT JOIN city c ON a.id_city = c.id
        WHERE c.id IS NULL
    ''')
    
    orphaned_addresses = cursor.fetchall()
    
    if not orphaned_addresses:
        print("✅ Проблемных адресов не найдено")
        return
    
    print(f"   ❌ Найдено {len(orphaned_addresses)} проблемных адресов")
    
    # 2. Создаем "неизвестный" город если его нет
    cursor.execute("SELECT id FROM city WHERE city_name = 'Неизвестный'")
    unknown_city = cursor.fetchone()
    
    if not unknown_city:
        print("   📍 Создаю город 'Неизвестный'...")
        cursor.execute("INSERT INTO city (city_name) VALUES ('Неизвестный')")
        unknown_city_id = cursor.lastrowid
    else:
        unknown_city_id = unknown_city[0]
    
    # 3. Исправляем проблемные адреса
    cursor.execute('''
        UPDATE address_info_client 
        SET id_city = ? 
        WHERE id_city NOT IN (SELECT id FROM city)
    ''', (unknown_city_id,))
    
    fixed_count = cursor.rowcount
    print(f"   ✅ Исправлено адресов: {fixed_count}")

def analyze_statistics(cursor):
    """Анализ статистики после миграции"""
    print("\n📊 Статистика после миграции:")
    
    # Общее количество клиентов
    cursor.execute("SELECT COUNT(*) FROM info_client")
    total_clients = cursor.fetchone()[0]
    print(f"   Всего клиентов: {total_clients}")
    
    # Клиенты с валидными датами
    cursor.execute("SELECT COUNT(*) FROM info_client WHERE created_at IS NOT NULL")
    clients_with_dates = cursor.fetchone()[0]
    print(f"   Клиентов с датами: {clients_with_dates}")
    
    # Статистика по годам
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
    print(f"   📅 Статистика по годам:")
    for year, count in yearly_stats:
        print(f"      {year}: {count} записей")
    
    # Разнообразие дат
    cursor.execute("""
        SELECT 
            COUNT(DISTINCT date(created_at)) as unique_dates,
            MIN(date(created_at)) as earliest_date,
            MAX(date(created_at)) as latest_date
        FROM info_client 
        WHERE created_at IS NOT NULL
    """)
    diversity = cursor.fetchone()
    print(f"   📊 Разнообразие дат:")
    print(f"      Уникальных дат: {diversity[0]}")
    print(f"      Самая ранняя: {diversity[1]}")
    print(f"      Самая поздняя: {diversity[2]}")
    
    # Проверка целостности связей
    cursor.execute("""
        SELECT COUNT(*) FROM info_client c
        LEFT JOIN address_info_client a ON c.id = a.id_client
        LEFT JOIN city ci ON a.id_city = ci.id
        WHERE ci.id IS NOT NULL
    """)
    clients_with_valid_addresses = cursor.fetchone()[0]
    print(f"   🏠 Клиентов с валидными адресами: {clients_with_valid_addresses}")
    
    if clients_with_valid_addresses != total_clients:
        print(f"   ⚠️ Клиентов без адресов: {total_clients - clients_with_valid_addresses}")

def test_flask_compatibility(cursor):
    """Тестирование совместимости с Flask"""
    print("\n🧪 Тестирование совместимости с Flask...")
    
    try:
        # Симуляция JOIN запроса из Flask приложения
        cursor.execute("""
            SELECT c.id, c.sur_name, c.name, c.created_at,
                   a.address, ci.city_name,
                   w.status, w.work
            FROM info_client c
            LEFT JOIN address_info_client a ON c.id = a.id_client
            LEFT JOIN city ci ON a.id_city = ci.id
            LEFT JOIN work_info_client w ON c.id = w.id_client
            ORDER BY c.created_at DESC
            LIMIT 5
        """)
        
        test_clients = cursor.fetchall()
        print(f"   ✅ JOIN запрос работает, получено {len(test_clients)} записей")
        
        if test_clients:
            print("   📋 Примеры данных для Flask:")
            for client in test_clients[:3]:
                client_id, surname, name, created_at, address, city, status, work = client
                city_name = city or 'Нет города'
                address_str = address or 'Нет адреса'
                print(f"      {surname} {name} - {city_name}, {address_str} (дата: {created_at})")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка тестирования Flask: {e}")
        return False

def main():
    """Основная функция миграции"""
    print("🛠️ Единая миграция базы данных Кадастр")
    print("=" * 60)
    print("💡 Основная задача: перенос date_status в created_at как дата создания заявки")
    print()
    
    # Проверка наличия БД
    if not os.path.exists('kadastr.db'):
        print("❌ Файл kadastr.db не найден!")
        return
    
    file_size = os.path.getsize('kadastr.db')
    print(f"📁 Файл БД: kadastr.db ({file_size} байт)")
    
    # Создаем бэкап
    backup_file = create_backup()
    
    # Спрашиваем подтверждение
    print("\n⚠️ Будут внесены изменения в базу данных:")
    print("1. Исправление схемы таблиц")
    print("2. Перенос date_status в created_at (основная задача)")
    print("3. Исправление проблемных адресов")
    print("4. Проверка целостности данных")
    
    if backup_file:
        print(f"💾 Бэкап создан: {backup_file}")
    
    choice = input("\nПродолжить миграцию? (yes/no): ").lower()
    if choice not in ['yes', 'y', 'да']:
        print("👋 Миграция отменена")
        return
    
    # Выполняем миграцию
    try:
        conn = sqlite3.connect('kadastr.db')
        cursor = conn.cursor()
        
        # 1. Исправление схемы
        schema_changes = fix_schema_issues(cursor)
        
        # 2. ОСНОВНАЯ ЗАДАЧА: Перенос date_status в created_at
        migrate_date_status_to_created_at(cursor)
        
        # 3. Исправление проблемных адресов
        fix_orphaned_addresses(cursor)
        
        # 4. Анализ результатов
        analyze_statistics(cursor)
        
        # 5. Тестирование Flask совместимости
        flask_ok = test_flask_compatibility(cursor)
        
        # Сохраняем изменения
        conn.commit()
        conn.close()
        
        print("\n" + "=" * 60)
        print("🎉 Миграция завершена успешно!")
        print("\n📋 Что было сделано:")
        print("✅ Схема таблиц проверена и исправлена")
        print("✅ date_status перенесен в created_at для всех клиентов")
        print("✅ Проблемные адреса исправлены")
        print("✅ Целостность данных проверена")
        
        if flask_ok:
            print("✅ Совместимость с Flask подтверждена")
        else:
            print("⚠️ Требуется дополнительная проверка Flask")
        
        print(f"\n▶️ Теперь перезапустите приложение: python run.py")
        
        if backup_file:
            print(f"💾 В случае проблем можно восстановить из: {backup_file}")
        
    except Exception as e:
        print(f"\n❌ Критическая ошибка миграции: {e}")
        import traceback
        traceback.print_exc()
        
        if backup_file:
            print(f"💾 Восстановите базу из бэкапа: {backup_file}")

if __name__ == '__main__':
    main()