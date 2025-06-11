#!/usr/bin/env python3
"""
Отладка загрузки данных из БД
"""
import os
import sys
import sqlite3

# Добавляем путь к приложению
sys.path.insert(0, '.')

def test_direct_sqlite():
    """Прямая проверка через sqlite3"""
    print("🔍 Прямая проверка через sqlite3:")
    
    db_path = "kadastr.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Проверяем таблицы
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"📋 Найдено таблиц: {len(tables)}")
        
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"  • {table_name}: {count} записей")
            
            # Показываем примеры данных
            if count > 0:
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
                rows = cursor.fetchall()
                print(f"    Пример данных: {rows[0] if rows else 'нет данных'}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка sqlite3: {e}")
        return False

def test_flask_app():
    """Проверка через Flask приложение"""
    print("\n🔍 Проверка через Flask приложение:")
    
    try:
        # Устанавливаем правильный путь к БД
        os.environ['DATABASE_URL'] = 'sqlite:///kadastr.db'
        
        from app import create_app, db
        from app.models import Client, City, AddressInfo, WorkInfo, DocInfo, DocFillInfo
        
        app = create_app()
        
        with app.app_context():
            print(f"📊 Подключение к БД: {app.config['SQLALCHEMY_DATABASE_URI']}")
            
            # Проверяем модели
            models = [
                ('City', City),
                ('Client', Client), 
                ('AddressInfo', AddressInfo),
                ('WorkInfo', WorkInfo),
                ('DocInfo', DocInfo),
                ('DocFillInfo', DocFillInfo)
            ]
            
            for model_name, model_class in models:
                try:
                    count = model_class.query.count()
                    print(f"  • {model_name}: {count} записей")
                    
                    # Показываем пример записи
                    if count > 0:
                        first_record = model_class.query.first()
                        print(f"    Первая запись: {first_record}")
                        
                except Exception as e:
                    print(f"  ❌ {model_name}: Ошибка - {e}")
            
            # Специальная проверка клиентов для веб-интерфейса
            try:
                clients = db.session.query(Client)\
                    .join(AddressInfo, Client.id == AddressInfo.id_client, isouter=True)\
                    .join(City, AddressInfo.id_city == City.id, isouter=True)\
                    .join(WorkInfo, Client.id == WorkInfo.id_client, isouter=True)\
                    .order_by(Client.created_at.desc())\
                    .all()
                
                print(f"\n📊 Клиенты с JOIN запросом: {len(clients)}")
                
                if clients:
                    client = clients[0]
                    print(f"  Пример клиента: {client.full_name}")
                    print(f"  Адрес: {client.address.address if client.address else 'Нет'}")
                    print(f"  Город: {client.address.city_info.city_name if client.address and client.address.city_info else 'Нет'}")
                    print(f"  Статус: {client.work_info.status_name if client.work_info else 'Нет'}")
                
            except Exception as e:
                print(f"❌ Ошибка JOIN запроса: {e}")
                print(f"Это может быть причиной пустой таблицы в веб-интерфейсе!")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка Flask приложения: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_endpoint():
    """Проверка API эндпоинта"""
    print("\n🔍 Проверка API эндпоинта:")
    
    try:
        os.environ['DATABASE_URL'] = 'sqlite:///kadastr.db'
        
        from app import create_app
        
        app = create_app()
        
        with app.test_client() as client:
            # Тестируем API клиентов
            response = client.get('/api/clients')
            
            print(f"📡 Статус ответа: {response.status_code}")
            
            if response.status_code == 200:
                data = response.get_json()
                if data and 'data' in data:
                    clients_count = len(data['data'])
                    print(f"📊 API вернул клиентов: {clients_count}")
                    
                    if clients_count > 0:
                        client_example = data['data'][0]
                        print(f"  Пример клиента из API: {client_example.get('sur_name', 'N/A')} {client_example.get('name', 'N/A')}")
                else:
                    print("📊 API вернул пустой результат")
            else:
                print(f"❌ API ошибка: {response.data}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка API: {e}")
        return False

def main():
    print("🛠️ Диагностика загрузки данных")
    print("=" * 50)
    
    # Проверяем файл БД
    if not os.path.exists('kadastr.db'):
        print("❌ Файл kadastr.db не найден!")
        return
    
    file_size = os.path.getsize('kadastr.db')
    print(f"📁 Файл БД: kadastr.db ({file_size} байт)")
    
    # Последовательные проверки
    checks = [
        ("SQLite напрямую", test_direct_sqlite),
        ("Flask приложение", test_flask_app),
        ("API эндпоинт", test_api_endpoint)
    ]
    
    for check_name, check_func in checks:
        print(f"\n{'='*20} {check_name} {'='*20}")
        success = check_func()
        print(f"Результат: {'✅ Успешно' if success else '❌ Ошибка'}")

if __name__ == '__main__':
    main()