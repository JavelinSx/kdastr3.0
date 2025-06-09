from app import db
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

class City(db.Model):
    __tablename__ = 'city'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    
    def __init__(self, city_name: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.city_name = city_name
    
    # Связь с адресами
    addresses: Mapped[List['AddressInfo']] = relationship('AddressInfo', back_populates='city_info', lazy='dynamic')
    
    def __repr__(self) -> str:
        return f'<City {self.city_name}>'

class Client(db.Model):
    __tablename__ = 'info_client'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sur_name: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    middle_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    telefone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    path_folder: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    service: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-8 типы услуг
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    def __init__(self, sur_name: str, name: str, service: int, 
                 middle_name: Optional[str] = None, telefone: Optional[str] = None, 
                 path_folder: Optional[str] = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.sur_name = sur_name
        self.name = name
        self.middle_name = middle_name
        self.telefone = telefone
        self.path_folder = path_folder
        self.service = service
    
    # Связи с другими таблицами
    address: Mapped[Optional['AddressInfo']] = relationship('AddressInfo', back_populates='client', uselist=False, cascade='all, delete-orphan')
    work_info: Mapped[Optional['WorkInfo']] = relationship('WorkInfo', back_populates='client', uselist=False, cascade='all, delete-orphan')
    doc_info: Mapped[Optional['DocInfo']] = relationship('DocInfo', back_populates='client', uselist=False, cascade='all, delete-orphan')
    doc_fill_info: Mapped[Optional['DocFillInfo']] = relationship('DocFillInfo', back_populates='client', uselist=False, cascade='all, delete-orphan')
    
    @property
    def full_name(self) -> str:
        return f"{self.sur_name} {self.name} {self.middle_name or ''}".strip()
    
    @property
    def service_name(self) -> str:
        services = [
            'Акт обследования', 'Выдел', 'Вынос', 'Образование',
            'Объединение', 'Перераспределение', 'Раздел', 
            'Технический план', 'Уточнение'
        ]
        return services[self.service] if 0 <= self.service < len(services) else 'Неизвестно'
    
    def __repr__(self) -> str:
        return f'<Client {self.full_name}>'

class AddressInfo(db.Model):
    __tablename__ = 'address_info_client'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_client: Mapped[int] = mapped_column(Integer, ForeignKey('info_client.id'), nullable=False)
    id_city: Mapped[int] = mapped_column(Integer, ForeignKey('city.id'), nullable=False)
    address: Mapped[str] = mapped_column(String(200), nullable=False)
    
    def __init__(self, id_client: int, id_city: int, address: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.id_client = id_client
        self.id_city = id_city
        self.address = address
    
    # Связи
    client: Mapped['Client'] = relationship('Client', back_populates='address')
    city_info: Mapped['City'] = relationship('City', back_populates='addresses')

class WorkInfo(db.Model):
    __tablename__ = 'work_info_client'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_client: Mapped[int] = mapped_column(Integer, ForeignKey('info_client.id'), nullable=False)
    prepayment: Mapped[bool] = mapped_column(Boolean, default=False)
    remains: Mapped[bool] = mapped_column(Boolean, default=False)
    work: Mapped[int] = mapped_column(Integer, default=0)  # 0-ожидает, 1-готова
    date_work: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    status: Mapped[int] = mapped_column(Integer, default=0)  # 0-разработка, 1-готова
    date_status: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    def __init__(self, id_client: int, date_work: Optional[str] = None, date_status: Optional[str] = None, 
                 info: Optional[str] = None, prepayment: bool = False, remains: bool = False, 
                 work: int = 0, status: int = 0, **kwargs) -> None:
        super().__init__(**kwargs)
        self.id_client = id_client
        self.prepayment = prepayment
        self.remains = remains
        self.work = work
        self.date_work = date_work
        self.status = status
        self.date_status = date_status
        self.info = info
    
    # Связи
    client: Mapped['Client'] = relationship('Client', back_populates='work_info')
    
    @property
    def work_status_name(self) -> str:
        return 'Готова' if self.work == 1 else 'Ожидает выезд'
    
    @property
    def status_name(self) -> str:
        return 'Готова' if self.status == 1 else 'Разработка'

class DocInfo(db.Model):
    __tablename__ = 'doc_info_client'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_client: Mapped[int] = mapped_column(Integer, ForeignKey('info_client.id'), nullable=False)
    series_pass: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    date_pass: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    info_pass: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    snils: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    def __init__(self, id_client: int, series_pass: Optional[str] = None, date_pass: Optional[str] = None, 
                 info_pass: Optional[str] = None, snils: Optional[str] = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.id_client = id_client
        self.series_pass = series_pass
        self.date_pass = date_pass
        self.info_pass = info_pass
        self.snils = snils
    
    # Связи
    client: Mapped['Client'] = relationship('Client', back_populates='doc_info')

class DocFillInfo(db.Model):
    __tablename__ = 'doc_fill_info'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_client: Mapped[int] = mapped_column(Integer, ForeignKey('info_client.id'), nullable=False)
    date_birthday: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    place_residence: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    extend_work_info: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    approval: Mapped[bool] = mapped_column(Boolean, default=False)
    contract: Mapped[bool] = mapped_column(Boolean, default=False)
    contract_agreement: Mapped[bool] = mapped_column(Boolean, default=False)
    declaration: Mapped[bool] = mapped_column(Boolean, default=False)
    receipt: Mapped[bool] = mapped_column(Boolean, default=False)
    
    def __init__(self, id_client: int, date_birthday: Optional[str] = None, place_residence: Optional[str] = None, 
                 extend_work_info: Optional[str] = None, approval: bool = False, contract: bool = False, 
                 contract_agreement: bool = False, declaration: bool = False, receipt: bool = False, **kwargs) -> None:
        super().__init__(**kwargs)
        self.id_client = id_client
        self.date_birthday = date_birthday
        self.place_residence = place_residence
        self.extend_work_info = extend_work_info
        self.approval = approval
        self.contract = contract
        self.contract_agreement = contract_agreement
        self.declaration = declaration
        self.receipt = receipt
    
    # Связи
    client: Mapped['Client'] = relationship('Client', back_populates='doc_fill_info')