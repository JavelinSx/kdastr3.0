#!/usr/bin/env python3
"""
Глубокая диагностика структуры базы данных
"""
import sqlite3
import os
import sys

def compare_schemas():
    """Сравнение реальной схемы БД с ожидаемой моделями Flask"""
    print("🔍 Сравнение схем базы данных")
    print("=" * 50)
    
    # Проверяем реальную структуру БД
    conn = sqlite3.connect('kadastr.db')
    cursor = conn.cursor()
    
    # Получаем все таблицы
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    real_tables = [row[0] for row in cursor.fetchall()]
    
    print("📋 Реальные таблицы в БД:")
    for table in real_tables:
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()
        
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        
        print(f"\n  🏷️ {table} ({count} записей):")
        for col in columns:
            col_id, name, type_, notnull, default, pk = col
            print(f"    • {name}: {type_} {'(PK)' if pk else ''} {'NOT NULL' if notnull else ''}")
    
    # Ожидаемые таблицы из моделей Flask
    expected_tables = {
        'city': ['id', 'city_name'],
        'info_client': ['id', 'sur_name', 'name', 'middle_name', 'telefone', 'path_folder', 'service', 'created_at'],
        'address_info_client': ['id', 'id_client', 'id_city', 'address'],
        'work_info_client': ['id', 'id_client', 'prepayment', 'remains', 'work', 'date_work', 'status', 'date_status', 'info'],
        'doc_info_client': ['id', 'id_client', 'series_pass', 'date_pass', 'info_pass', 'snils'],
        'doc_fill_info': ['id', 'id_client', 'date_birthday', 'place_residence', 'extend_work_info', 'approval', 'contract', 'contract_agreement', 'declaration', 'receipt']
    }
    
    print(f"\n🎯 Ожидаемые таблицы моделями Flask:")
    for table, expected_cols in expected_tables.items():
        print(f"\n  🏷️ {table}:")
        print(f"    Ожидаемые колонки: {', '.join(expected_cols)}")
        
        if table in real_tables:
            cursor.execute(f"PRAGMA table_info({table})")
            real_cols = [col[1] for col in cursor.fetchall()]
            
            missing_cols = set(expected_cols) - set(real_cols)
            extra_cols = set(real_cols) - set(expected_cols)
            
            if missing_cols:
                print(f"    ❌ Отсутствуют: {', '.join(missing_cols)}")
            if extra_cols:
                print(f"    ➕ Лишние: {', '.join(extra_cols)}")
            if not missing_cols and not extra_cols:
                print(f"    ✅ Структура совпадает")
        else:
            print(f"    ❌ Таблица отсутствует!")
    
    conn.close()

def check_data_integrity():
    """Проверка целостности данных"""
    print(f"\n🔗 Проверка целостности данных:")
    
    conn = sqlite3.connect('kadastr.db')
    cursor = conn.cursor()
    
    # Проверяем связи между таблицами
    checks = [
        ("Клиенты без адресов", 
         "SELECT COUNT(*) FROM info_client ic LEFT JOIN address_info_client aic ON ic.id = aic.id_client WHERE aic.id_client IS NULL"),
        
        ("Адреса без клиентов",
         "SELECT COUNT(*) FROM address_info_client aic LEFT JOIN info_client ic ON aic.id_client = ic.id WHERE ic.id IS NULL"),
        
        ("Клиенты без рабочей информации",
         "SELECT COUNT(*) FROM info_client ic LEFT JOIN work_info_client wic ON ic.id = wic.id_client WHERE wic.id_client IS NULL"),
        
        ("Адреса с несуществующими городами",
         "SELECT COUNT(*) FROM address_info_client aic LEFT JOIN city c ON aic.id_city = c.id WHERE c.id IS NULL"),
    ]
    
    for check_name, query in checks:
        cursor.execute(query)
        count = cursor.fetchone()[0]
        status = "⚠️" if count > 0 else "✅"
        print(f"  {status} {check_name}: {count}")
    
    # Проверяем примеры данных с связями
    print(f"\n📊 Примеры данных с связями:")
    
    try:
        cursor.execute("""
            SELECT 
                ic.id,
                ic.sur_name,
                ic.name,
                aic.address,
                c.city_name,
                wic.status
            FROM info_client ic
            LEFT JOIN address_info_client aic ON ic.id = aic.id_client
            LEFT JOIN city c ON aic.id_city = c.id
            LEFT JOIN work_info_client wic ON ic.id = wic.id_client
            LIMIT 5
        """)
        
        rows = cursor.fetchall()
        
        if rows:
            print("  Первые 5 клиентов с полной информацией:")
            for row in rows:
                print(f"    {row[0]}: {row[1]} {row[2]} - {row[3]} ({row[4]}) - статус: {row[5]}")
        else:
            print("  ❌ Нет данных в JOIN запросе!")
            
    except Exception as e:
        print(f"  ❌ Ошибка JOIN запроса: {e}")
    
    conn.close()

def test_sqlalchemy_mapping():
    """Тестирование маппинга SQLAlchemy"""
    print(f"\n🧪 Тестирование маппинга SQLAlchemy:")
    
    try:
        sys.path.insert(0, '.')
        os.environ['DATABASE_URL'] = 'sqlite:///kadastr.db'
        
        from app import create_app, db
        from app.models import Client, City, AddressInfo, WorkInfo, DocInfo, DocFillInfo
        
        app = create_app()
        
        with app.app_context():
            # Пробуем прямые SQL запросы через SQLAlchemy
            print("  🔍 Прямые SQL запросы через SQLAlchemy:")
            
            # Простой подсчет
            result = db.session.execute(db.text("SELECT COUNT(*) FROM info_client")).scalar()
            print(f"    info_client (SQL): {result} записей")
            
            # Проверяем маппинг модели Client
            print(f"  🔍 Проверка модели Client:")
            print(f"    Имя таблицы: {Client.__tablename__}")
            
            # Пробуем сырой запрос к таблице клиентов
            try:
                clients_raw = db.session.execute(
                    db.text("SELECT id, sur_name, name FROM info_client LIMIT 3")
                ).fetchall()
                
                print(f"    Сырой SQL результат: {len(clients_raw)} записей")
                for client in clients_raw:
                    print(f"      {client[0]}: {client[1]} {client[2]}")
                
            except Exception as e:
                print(f"    ❌ Ошибка сырого SQL: {e}")
            
            # Пробуем ORM запрос
            try:
                print(f"  🔍 ORM запросы:")
                
                # Самый простой запрос
                client_count = db.session.query(Client).count()
                print(f"    Client.query.count(): {client_count}")
                
                # Если count = 0, проверяем детали
                if client_count == 0:
                    print(f"    Проверяем детали маппинга...")
                    
                    # Проверяем есть ли проблемы с created_at
                    try:
                        first_client = db.session.execute(
                            db.text("SELECT * FROM info_client LIMIT 1")
                        ).fetchone()
                        
                        if first_client:
                            print(f"    Первая запись (сырая): {dict(first_client._mapping)}")
                            
                            # Пробуем создать объект Client вручную
                            client_data = dict(first_client._mapping)
                            manual_client = Client(
                                sur_name=client_data['sur_name'],
                                name=client_data['name'],
                                service=client_data['service'],
                                middle_name=client_data.get('middle_name'),
                                telefone=client_data.get('telefone'),
                                path_folder=client_data.get('path_folder')
                            )
                            print(f"    Создан объект Client: {manual_client.full_name}")
                            
                    except Exception as e:
                        print(f"    ❌ Ошибка детального анализа: {e}")
                
            except Exception as e:
                print(f"    ❌ Ошибка ORM: {e}")
        
    except Exception as e:
        print(f"  ❌ Ошибка тестирования SQLAlchemy: {e}")
        import traceback
        traceback.print_exc()

def main():
    print("🔬 Глубокая диагностика схемы базы данных")
    print("=" * 60)
    
    if not os.path.exists('kadastr.db'):
        print("❌ Файл kadastr.db не найден!")
        return
    
    compare_schemas()
    check_data_integrity()
    test_sqlalchemy_mapping()
    
    print(f"\n💡 Рекомендации:")
    print("1. Проверьте вывод выше на несоответствия схем")
    print("2. Особое внимание на ошибки в ORM запросах")
    print("3. Если проблема в created_at, возможно нужно обновить значения")

if __name__ == '__main__':
    main()