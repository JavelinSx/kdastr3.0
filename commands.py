"""
CLI команды для Flask приложения
"""
import click
from flask.cli import with_appcontext

@click.command()
@with_appcontext
def init_db():
    """Инициализация базы данных"""
    from app import db
    db.create_all()
    click.echo('✅ База данных инициализирована.')

@click.command()
@with_appcontext
def seed_db():
    """Заполнение базы данных тестовыми данными"""
    from app import db
    from app.models import City
    
    # Добавляем города
    if City.query.count() == 0:
        default_cities = [
            'Санкт-Петербург', 'Москва', 'Казань', 'Екатеринбург',
            'Новосибирск', 'Челябинск', 'Омск', 'Самара'
        ]
        for city_name in default_cities:
            city = City(city_name)  # Передаем как позиционный аргумент
            db.session.add(city)
        
        try:
            db.session.commit()
            click.echo(f'✅ Добавлено {len(default_cities)} городов.')
        except Exception as e:
            db.session.rollback()
            click.echo(f'❌ Ошибка: {e}')
    else:
        click.echo('ℹ️  Города уже существуют.')

@click.command()
@with_appcontext
def reset_db():
    """Полный сброс базы данных"""
    from app import db
    
    if click.confirm('Вы уверены что хотите удалить ВСЕ данные?'):
        db.drop_all()
        db.create_all()
        click.echo('✅ База данных сброшена.')
    else:
        click.echo('❌ Отменено.')

@click.command()
@with_appcontext  
def show_cities():
    """Показать все города"""
    from app.models import City
    
    cities = City.query.all()
    if cities:
        click.echo('📍 Города в базе данных:')
        for city in cities:
            click.echo(f'  - {city.city_name} (ID: {city.id})')
    else:
        click.echo('❌ Городов не найдено')

def init_app(app):
    """Регистрация команд в приложении Flask"""
    app.cli.add_command(init_db)
    app.cli.add_command(seed_db)
    app.cli.add_command(reset_db)
    app.cli.add_command(show_cities)