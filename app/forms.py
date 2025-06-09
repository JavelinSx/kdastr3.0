from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, BooleanField, IntegerField
from wtforms.validators import DataRequired, Optional, Length, Regexp
from app.models import City

class ClientForm(FlaskForm):
    """Форма для добавления/редактирования клиента"""
    
    # Основная информация
    sur_name = StringField('Фамилия', validators=[
        DataRequired(message='Фамилия обязательна'),
        Length(max=100, message='Фамилия не должна превышать 100 символов')
    ])
    
    name = StringField('Имя', validators=[
        DataRequired(message='Имя обязательно'),
        Length(max=100, message='Имя не должно превышать 100 символов')
    ])
    
    middle_name = StringField('Отчество', validators=[
        Optional(),
        Length(max=100, message='Отчество не должно превышать 100 символов')
    ])
    
    telefone = StringField('Телефон', validators=[
        Optional(),
        Regexp(r'^\d{11}$', message='Телефон должен содержать 11 цифр')
    ])
    
    # Услуга
    service = SelectField('Услуга', 
        choices=[
            (0, 'Акт обследования'),
            (1, 'Выдел'),
            (2, 'Вынос'),
            (3, 'Образование'),
            (4, 'Объединение'),
            (5, 'Перераспределение'),
            (6, 'Раздел'),
            (7, 'Технический план'),
            (8, 'Уточнение')
        ],
        coerce=int,
        validators=[DataRequired(message='Выберите услугу')]
    )
    
    # Адрес
    city = SelectField('Город', coerce=int, validators=[DataRequired(message='Выберите город')])
    address = StringField('Адрес', validators=[
        DataRequired(message='Адрес обязателен'),
        Length(max=200, message='Адрес не должен превышать 200 символов')
    ])
    
    # Паспортные данные
    series_pass = StringField('Серия и номер паспорта', validators=[
        Optional(),
        Length(max=20, message='Серия и номер не должны превышать 20 символов')
    ])
    
    date_pass = StringField('Дата выдачи паспорта', validators=[
        Optional(),
        Regexp(r'^\d{2}\.\d{2}\.\d{4}$', message='Дата должна быть в формате ДД.ММ.ГГГГ')
    ])
    
    info_pass = StringField('Кем выдан паспорт', validators=[
        Optional(),
        Length(max=200, message='Информация о выдаче не должна превышать 200 символов')
    ])
    
    snils = StringField('СНИЛС', validators=[
        Optional(),
        Length(max=20, message='СНИЛС не должен превышать 20 символов')
    ])
    
    # Дополнительные данные для документов
    date_birthday = StringField('Дата рождения', validators=[
        Optional(),
        Regexp(r'^\d{2}\.\d{2}\.\d{4}$', message='Дата должна быть в формате ДД.ММ.ГГГГ')
    ])
    
    place_residence = StringField('Место проживания', validators=[
        Optional(),
        Length(max=200, message='Место проживания не должно превышать 200 символов')
    ])
    
    extend_work_info = StringField('Подробное наименование работ', validators=[
        Optional(),
        Length(max=500, message='Наименование работ не должно превышать 500 символов')
    ])
    
    # Документы для заполнения
    approval = BooleanField('Согласие')
    contract = BooleanField('Договор подряда')
    contract_agreement = BooleanField('Акт к договору подряда')
    declaration = BooleanField('Декларация')
    receipt = BooleanField('Квитанция')
    
    # Рабочая информация
    prepayment = BooleanField('Предоплата')
    remains = BooleanField('Остаток')
    
    work = SelectField('Статус съёмки', 
        choices=[(0, 'Ожидает выезд'), (1, 'Готова')],
        coerce=int,
        default=0
    )
    
    status = SelectField('Общий статус работ', 
        choices=[(0, 'Разработка'), (1, 'Готова')],
        coerce=int,
        default=0
    )
    
    info = TextAreaField('Дополнительная информация', validators=[Optional()])
    
    def __init__(self, *args, **kwargs):
        super(ClientForm, self).__init__(*args, **kwargs)
        # Динамически загружаем города
        self.city.choices = [(city.id, city.city_name) for city in City.query.all()]

class CityForm(FlaskForm):
    """Форма для добавления города"""
    city_name = StringField('Название города', validators=[
        DataRequired(message='Название города обязательно'),
        Length(max=100, message='Название не должно превышать 100 символов')
    ])

class SearchForm(FlaskForm):
    """Форма поиска"""
    query = StringField('Поиск', validators=[
        DataRequired(message='Введите поисковый запрос'),
        Length(min=2, max=100, message='Запрос должен содержать от 2 до 100 символов')
    ])