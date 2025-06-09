from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from app import db
from app.models import Client, AddressInfo, WorkInfo, DocInfo, DocFillInfo, City
from datetime import datetime
import os
import shutil
import subprocess
import platform

bp = Blueprint('main', __name__)

def simple_fuzzy_match(text1, text2, threshold=80):
    """Простая реализация нечеткого поиска без rapidfuzz"""
    text1 = text1.lower().strip()
    text2 = text2.lower().strip()
    
    # Точное совпадение
    if text1 == text2:
        return 100
    
    # Проверяем вхождение
    if text1 in text2 or text2 in text1:
        return 90
    
    # Простое сравнение по символам
    matches = 0
    min_len = min(len(text1), len(text2))
    max_len = max(len(text1), len(text2))
    
    if max_len == 0:
        return 0
    
    for i in range(min_len):
        if text1[i] == text2[i]:
            matches += 1
    
    similarity = (matches * 100) // max_len
    return similarity

@bp.route('/')
def index():
    """Главная страница с таблицей клиентов"""
    try:
        clients = db.session.query(Client)\
            .join(AddressInfo, Client.id == AddressInfo.id_client, isouter=True)\
            .join(City, AddressInfo.id_city == City.id, isouter=True)\
            .join(WorkInfo, Client.id == WorkInfo.id_client, isouter=True)\
            .order_by(Client.created_at.desc())\
            .all()
    except Exception:
        # Если join не работает, используем простой запрос
        clients = Client.query.order_by(Client.created_at.desc()).all()
    
    return render_template('clients.html', clients=clients)

@bp.route('/api/clients')
def api_clients():
    """API для получения данных клиентов (для DataTables)"""
    # Получаем параметры фильтрации
    status_filter = request.args.get('status')
    work_filter = request.args.get('work')
    date_filter = request.args.get('date')
    search_query = request.args.get('search', '').strip()
    
    # Получаем всех клиентов
    all_clients = Client.query.all()
    filtered_clients = []
    
    for client in all_clients:
        # Применяем фильтры
        if status_filter:
            if status_filter == 'ready' and (not client.work_info or client.work_info.status != 1):
                continue
            elif status_filter == 'development' and (not client.work_info or client.work_info.status != 0):
                continue
        
        if work_filter:
            if work_filter == 'ready' and (not client.work_info or client.work_info.work != 1):
                continue
            elif work_filter == 'waiting' and (not client.work_info or client.work_info.work != 0):
                continue
        
        if date_filter and client.work_info and client.work_info.date_status != date_filter:
            continue
        
        # Применяем поиск
        if search_query:
            search_text = search_query.lower()
            
            # Собираем все поля для поиска
            search_fields = [
                client.sur_name or '',
                client.name or '',
                client.middle_name or '',
                client.telefone or '',
            ]
            
            if client.address:
                search_fields.append(client.address.address or '')
                if client.address.city_info:
                    search_fields.append(client.address.city_info.city_name or '')
            
            # Проверяем вхождение
            found = False
            for field in search_fields:
                if search_text in field.lower():
                    found = True
                    break
                # Проверяем нечеткое совпадение для городов
                if len(search_text) > 2 and len(field) > 2:
                    if simple_fuzzy_match(search_text, field) > 70:
                        found = True
                        break
            
            if not found:
                continue
        
        filtered_clients.append(client)
    
    # Формируем данные для ответа
    data = []
    for client in filtered_clients:
        data.append({
            'id': client.id,
            'status': client.work_info.status_name if client.work_info else 'Не указан',
            'work': client.work_info.work_status_name if client.work_info else 'Не указан',
            'city': client.address.city_info.city_name if client.address and client.address.city_info else 'Не указан',
            'address': client.address.address if client.address else 'Не указан',
            'sur_name': client.sur_name,
            'name': client.name,
            'middle_name': client.middle_name or '',
            'telefone': client.telefone or '',
            'service': client.service_name,
            'date_status': client.work_info.date_status if client.work_info else '',
            'created_at': client.created_at.strftime('%d.%m.%Y') if client.created_at else ''
        })
    
    return jsonify({'data': data})

@bp.route('/client/add')
def add_client():
    """Страница добавления клиента"""
    cities = City.query.order_by(City.city_name).all()
    return render_template('add_client.html', cities=cities)

@bp.route('/client/add', methods=['POST'])
def add_client_post():
    """Обработка добавления клиента"""
    try:
        # Проверяем обязательные поля
        required_fields = ['sur_name', 'name', 'service', 'city', 'address']
        for field in required_fields:
            if not request.form.get(field, '').strip():
                flash(f'Поле "{field}" обязательно для заполнения', 'error')
                return redirect(url_for('main.add_client'))

        # Создаем клиента
        client = Client(
            sur_name=request.form['sur_name'].strip(),
            name=request.form['name'].strip(),
            service=int(request.form['service']),
            middle_name=request.form.get('middle_name', '').strip() or None,
            telefone=request.form.get('telefone', '').strip() or None
        )
        db.session.add(client)
        db.session.flush()  # Получаем ID
        
        # Создаем адрес
        address = AddressInfo(
            id_client=client.id,
            id_city=int(request.form['city']),
            address=request.form['address'].strip()
        )
        db.session.add(address)
        
        # Создаем рабочую информацию
        current_date = datetime.now().strftime('%d.%m.%Y')
        work_info = WorkInfo(
            id_client=client.id,
            date_work=current_date,
            date_status=current_date,
            info=request.form.get('info', '').strip()
        )
        db.session.add(work_info)
        
        # Создаем документную информацию
        doc_info = DocInfo(id_client=client.id)
        db.session.add(doc_info)
        
        # Создаем информацию о заполнении документов
        doc_fill_info = DocFillInfo(id_client=client.id)
        db.session.add(doc_fill_info)
        
        # Создаем папку для клиента
        city = City.query.get(address.id_city)
        if city:
            folder_path = create_client_folder(client, city, address.address)
            client.path_folder = folder_path
        
        db.session.commit()
        flash('Клиент успешно добавлен!', 'success')
        return redirect(url_for('main.index'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при добавлении клиента: {str(e)}', 'error')
        return redirect(url_for('main.add_client'))

@bp.route('/client/<int:client_id>')
def edit_client(client_id):
    """Страница редактирования клиента"""
    client = Client.query.get_or_404(client_id)
    cities = City.query.order_by(City.city_name).all()
    return render_template('edit_client.html', client=client, cities=cities)

@bp.route('/client/<int:client_id>', methods=['POST'])
def edit_client_post(client_id):
    """Обработка редактирования клиента"""
    client = Client.query.get_or_404(client_id)
    
    try:
        # Сохраняем старые значения для проверки изменений
        old_path = client.path_folder
        old_service = client.service
        old_city_id = client.address.id_city if client.address else None
        old_address = client.address.address if client.address else None
        old_surname = client.sur_name
        
        # Получаем новый путь из формы
        new_path_from_form = request.form.get('path_folder', '').strip() or None
        move_files = 'move_files_on_change' in request.form
        
        # Обновляем основную информацию
        client.sur_name = request.form['sur_name'].strip()
        client.name = request.form['name'].strip()
        client.middle_name = request.form.get('middle_name', '').strip() or None
        client.telefone = request.form.get('telefone', '').strip() or None
        client.service = int(request.form['service'])
        
        # Обновляем адрес
        if client.address:
            client.address.id_city = int(request.form['city'])
            client.address.address = request.form['address'].strip()
        
        # Обновляем рабочую информацию
        if client.work_info:
            client.work_info.prepayment = 'prepayment' in request.form
            client.work_info.remains = 'remains' in request.form
            client.work_info.work = int(request.form.get('work', 0))
            client.work_info.status = int(request.form.get('status', 0))
            client.work_info.info = request.form.get('info', '').strip()
            
            # Обновляем даты если указаны
            date_work_value = request.form.get('date_work', '').strip()
            if date_work_value:
                client.work_info.date_work = date_work_value
                
            date_status_value = request.form.get('date_status', '').strip()
            if date_status_value:
                client.work_info.date_status = date_status_value
        
        # Обновляем документную информацию
        if client.doc_info:
            client.doc_info.series_pass = request.form.get('series_pass', '').strip() or None
            client.doc_info.date_pass = request.form.get('date_pass', '').strip() or None
            client.doc_info.info_pass = request.form.get('info_pass', '').strip() or None
            client.doc_info.snils = request.form.get('snils', '').strip() or None
        
        # Обновляем информацию о заполнении документов
        if client.doc_fill_info:
            client.doc_fill_info.date_birthday = request.form.get('date_birthday', '').strip() or None
            client.doc_fill_info.place_residence = request.form.get('place_residence', '').strip() or None
            client.doc_fill_info.extend_work_info = request.form.get('extend_work_info', '').strip() or None
            client.doc_fill_info.approval = 'approval' in request.form
            client.doc_fill_info.contract = 'contract' in request.form
            client.doc_fill_info.contract_agreement = 'contract_agreement' in request.form
            client.doc_fill_info.declaration = 'declaration' in request.form
            client.doc_fill_info.receipt = 'receipt' in request.form
        
        # Обработка изменения пути к папке
        path_changed = False
        
        # Проверяем изменения для автоматического создания папки
        new_city_id = int(request.form['city'])
        new_address = request.form['address'].strip()
        new_service = int(request.form['service'])
        new_surname = request.form['sur_name'].strip()
        
        auto_path_changed = (
            old_service != new_service or 
            old_city_id != new_city_id or 
            old_address != new_address or 
            old_surname != new_surname
        )
        
        # Если пользователь изменил путь вручную
        if new_path_from_form != old_path:
            path_changed = True
            
            if new_path_from_form:
                # Проверяем новый путь
                if not os.path.exists(new_path_from_form):
                    flash(f'Указанный путь не существует: {new_path_from_form}', 'error')
                    return redirect(url_for('main.edit_client', client_id=client_id))
                
                if not os.path.isdir(new_path_from_form):
                    flash(f'Указанный путь не является папкой: {new_path_from_form}', 'error')
                    return redirect(url_for('main.edit_client', client_id=client_id))
                
                # Если нужно переместить файлы и старая папка существует
                if move_files and old_path and os.path.exists(old_path):
                    try:
                        folder_name = os.path.basename(old_path)
                        new_full_path = os.path.join(new_path_from_form, folder_name)
                        
                        # Избегаем конфликтов имен
                        counter = 1
                        original_new_path = new_full_path
                        while os.path.exists(new_full_path):
                            new_full_path = f"{original_new_path}_{counter}"
                            counter += 1
                        
                        shutil.move(old_path, new_full_path)
                        client.path_folder = os.path.abspath(new_full_path)
                        flash(f'Папка перемещена в {new_full_path}', 'success')
                        
                    except Exception as e:
                        flash(f'Ошибка при перемещении папки: {str(e)}', 'error')
                        return redirect(url_for('main.edit_client', client_id=client_id))
                else:
                    # Просто обновляем путь
                    client.path_folder = os.path.abspath(new_path_from_form)
                    if move_files and old_path and not os.path.exists(old_path):
                        flash('Путь обновлен. Старая папка не найдена, перемещение невозможно.', 'warning')
                    else:
                        flash('Путь к папке обновлен', 'success')
            else:
                # Пользователь очистил путь
                client.path_folder = None
                flash('Путь к папке очищен', 'info')
        
        # Если путь не изменился вручную, но изменились данные для авто-пути
        elif auto_path_changed and old_path and os.path.exists(old_path):
            city = City.query.get(new_city_id)
            if city:
                new_folder_path = create_client_folder(client, city, new_address, move_from=old_path)
                client.path_folder = new_folder_path
                flash('Папка перемещена в соответствии с новыми данными', 'info')
        
        db.session.commit()
        flash('Клиент успешно обновлен!', 'success')
        return redirect(url_for('main.index'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при обновлении клиента: {str(e)}', 'error')
        return redirect(url_for('main.edit_client', client_id=client_id))
    
@bp.route('/client/<int:client_id>/delete', methods=['POST'])
def delete_client(client_id):
    """Удаление клиента"""
    client = Client.query.get_or_404(client_id)
    
    try:
        # Удаляем папку клиента
        if client.path_folder and os.path.exists(client.path_folder):
            shutil.rmtree(client.path_folder)
        
        db.session.delete(client)
        db.session.commit()
        flash('Клиент успешно удален!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении клиента: {str(e)}', 'error')
    
    return redirect(url_for('main.index'))

@bp.route('/client/<int:client_id>/work-ready', methods=['POST'])
def mark_work_ready(client_id):
    """Отметить съёмку как готовую"""
    client = Client.query.get_or_404(client_id)
    
    try:
        if client.work_info:
            client.work_info.work = 1
            client.work_info.date_work = datetime.now().strftime('%d.%m.%Y')
            db.session.commit()
            flash('Съёмка отмечена как готовая!', 'success')
        else:
            flash('Информация о работах не найдена', 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка: {str(e)}', 'error')
    
    return redirect(url_for('main.edit_client', client_id=client_id))

# МАРШРУТ ДЛЯ ЗАПОЛНЕНИЯ ДОКУМЕНТОВ
@bp.route('/client/<int:client_id>/fill-documents', methods=['POST'])
def fill_client_documents(client_id):
    """Заполнение документов клиента"""
    client = Client.query.get_or_404(client_id)
    
    try:
        # Импортируем сервис документов
        from app.document_service import document_service
        
        # Получаем список документов для заполнения
        selected_docs = []
        if request.is_json and request.json:
            selected_docs = request.json.get('documents', [])
        else:
            selected_docs = request.form.getlist('documents')
        
        if not selected_docs:
            return jsonify({
                'success': False,
                'errors': ['Не выбраны документы для заполнения'],
                'filled_documents': []
            })
        
        # Заполняем документы
        result = document_service.fill_client_documents(client_id, selected_docs)
        
        return jsonify({
            'success': result['success'],
            'filled_documents': result['filled_documents'],
            'errors': result['errors'],
            'client_folder': result.get('client_folder', '')
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'errors': [f'Ошибка при заполнении документов: {str(e)}'],
            'filled_documents': []
        })

# МАРШРУТЫ ДЛЯ РАБОТЫ С ПАПКАМИ
@bp.route('/client/<int:client_id>/open-folder')
def open_client_folder(client_id):
    """Открытие папки клиента в файловом менеджере"""
    client = Client.query.get_or_404(client_id)
    
    if not client.path_folder:
        flash('Путь к папке клиента не указан', 'error')
        return redirect(url_for('main.edit_client', client_id=client_id))
    
    if not os.path.exists(client.path_folder):
        flash('Папка клиента не найдена', 'error')
        return redirect(url_for('main.edit_client', client_id=client_id))
    
    try:
        # Определяем операционную систему и открываем папку
        system = platform.system()
        
        if system == "Windows":
            # Для Windows используем os.startfile - это откроет папку в Проводнике
            os.startfile(client.path_folder)
        elif system == "Darwin":  # macOS
            subprocess.run(["open", client.path_folder], check=True)
        else:  # Linux и другие Unix-подобные системы
            subprocess.run(["xdg-open", client.path_folder], check=True)
            
        flash('Папка клиента открыта в файловом менеджере', 'success')
        
    except Exception as e:
        flash(f'Ошибка при открытии папки: {str(e)}', 'error')
    
    return redirect(url_for('main.edit_client', client_id=client_id))

@bp.route('/client/<int:client_id>/change-path', methods=['GET', 'POST'])
def change_client_path(client_id):
    """Изменение пути к папке клиента"""
    client = Client.query.get_or_404(client_id)
    
    if request.method == 'GET':
        # Показываем форму для изменения пути
        try:
            return render_template('change_path.html', client=client)
        except Exception as e:
            flash(f'Ошибка загрузки страницы: {str(e)}', 'error')
            return redirect(url_for('main.edit_client', client_id=client_id))
    
    # POST метод
    try:
        new_path = request.form.get('new_path', '').strip()
        move_files = 'move_files' in request.form
        
        if not new_path:
            flash('Новый путь не может быть пустым', 'error')
            return render_template('change_path.html', client=client)
        
        # Нормализуем путь для разных ОС
        new_path = os.path.normpath(new_path)
        
        # Проверяем, существует ли новый путь
        if not os.path.exists(new_path):
            flash('Указанный путь не существует', 'error')
            return render_template('change_path.html', client=client)
        
        # Проверяем, является ли путь директорией
        if not os.path.isdir(new_path):
            flash('Указанный путь не является директорией', 'error')
            return render_template('change_path.html', client=client)
        
        # Проверяем права доступа
        if not os.access(new_path, os.R_OK | os.W_OK):
            flash('Недостаточно прав доступа к указанной папке', 'error')
            return render_template('change_path.html', client=client)
        
        old_path = client.path_folder
        old_path_exists = old_path and os.path.exists(old_path)
        
        # Проверяем, можно ли переместить файлы
        if move_files and old_path_exists:
            try:
                # Создаем имя папки в новом месте
                folder_name = os.path.basename(old_path)
                new_full_path = os.path.join(new_path, folder_name)
                
                # Если папка с таким именем уже существует, добавляем суффикс
                counter = 1
                original_new_path = new_full_path
                while os.path.exists(new_full_path):
                    new_full_path = f"{original_new_path}_{counter}"
                    counter += 1
                
                # Перемещаем папку
                shutil.move(old_path, new_full_path)
                client.path_folder = os.path.abspath(new_full_path)
                flash(f'Папка клиента перемещена в {new_full_path}', 'success')
                
            except PermissionError:
                flash('Недостаточно прав для перемещения папки', 'error')
                return render_template('change_path.html', client=client)
            except shutil.Error as e:
                flash(f'Ошибка при перемещении папки: {str(e)}', 'error')
                return render_template('change_path.html', client=client)
            except Exception as e:
                flash(f'Неожиданная ошибка при перемещении: {str(e)}', 'error')
                return render_template('change_path.html', client=client)
        else:
            # Просто обновляем путь в базе данных
            client.path_folder = os.path.abspath(new_path)
            
            # Информируем пользователя о том, что произошло
            if move_files and old_path and not old_path_exists:
                flash(f'Путь обновлен на {new_path}. Старая папка не найдена, поэтому перемещение файлов невозможно.', 'warning')
            elif move_files and not old_path:
                flash(f'Путь обновлен на {new_path}. Старый путь не был указан, поэтому перемещение файлов невозможно.', 'warning')
            else:
                flash('Путь к папке клиента обновлен', 'success')
        
        db.session.commit()
        return redirect(url_for('main.edit_client', client_id=client_id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при изменении пути: {str(e)}', 'error')
        return render_template('change_path.html', client=client)
    
@bp.route('/client/<int:client_id>/create-folder', methods=['POST'])
def create_client_folder_route(client_id):
    """Создание/пересоздание папки клиента"""
    client = Client.query.get_or_404(client_id)
    
    try:
        if not client.address:
            flash('У клиента не указан адрес', 'error')
            return redirect(url_for('main.edit_client', client_id=client_id))
        
        city = City.query.get(client.address.id_city)
        if not city:
            flash('Город клиента не найден', 'error')
            return redirect(url_for('main.edit_client', client_id=client_id))
        
        # Создаем папку
        folder_path = create_client_folder(client, city, client.address.address)
        client.path_folder = folder_path
        
        db.session.commit()
        flash('Папка клиента создана успешно!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при создании папки: {str(e)}', 'error')
    
    return redirect(url_for('main.edit_client', client_id=client_id))

@bp.route('/client/<int:client_id>/folder-info')
def get_folder_info(client_id):
    """Получение информации о папке клиента (AJAX)"""
    client = Client.query.get_or_404(client_id)
    
    if not client.path_folder:
        return jsonify({
            'exists': False,
            'path': None,
            'files_count': 0,
            'size': 0,
            'message': 'Путь к папке не указан'
        })
    
    if not os.path.exists(client.path_folder):
        return jsonify({
            'exists': False,
            'path': client.path_folder,
            'files_count': 0,
            'size': 0,
            'message': 'Папка не найдена'
        })
    
    try:
        # Подсчитываем файлы и размер
        files_count = 0
        total_size = 0
        
        for root, dirs, files in os.walk(client.path_folder):
            files_count += len(files)
            for file in files:
                file_path = os.path.join(root, file)
                if os.path.exists(file_path):
                    total_size += os.path.getsize(file_path)
        
        # Форматируем размер
        if total_size < 1024:
            size_str = f"{total_size} Б"
        elif total_size < 1024 * 1024:
            size_str = f"{total_size / 1024:.1f} КБ"
        else:
            size_str = f"{total_size / (1024 * 1024):.1f} МБ"
        
        return jsonify({
            'exists': True,
            'path': client.path_folder,
            'files_count': files_count,
            'size': total_size,
            'size_formatted': size_str,
            'message': f'Папка содержит {files_count} файлов ({size_str})'
        })
        
    except Exception as e:
        return jsonify({
            'exists': True,
            'path': client.path_folder,
            'files_count': 0,
            'size': 0,
            'message': f'Ошибка при получении информации: {str(e)}'
        })

@bp.route('/search')
def search():
    """Поиск клиентов"""
    query_text = request.args.get('q', '').strip()
    if not query_text:
        return redirect(url_for('main.index'))
    
    # Получаем всех клиентов и городов
    all_clients = Client.query.all()
    all_cities = City.query.all()
    
    # Используем простой нечеткий поиск для городов
    matching_city_ids = []
    for city in all_cities:
        if simple_fuzzy_match(query_text, city.city_name) > 70:
            matching_city_ids.append(city.id)
    
    filtered_clients = []
    search_text = query_text.lower()
    
    for client in all_clients:
        # Проверяем совпадения в различных полях
        matches = [
            search_text in (client.sur_name or '').lower(),
            search_text in (client.name or '').lower(),
            search_text in (client.middle_name or '').lower(),
            search_text in (client.telefone or ''),
        ]
        
        # Проверяем адрес
        if client.address:
            matches.append(search_text in (client.address.address or '').lower())
            matches.append(search_text in (client.address.city_info.city_name or '').lower() if client.address.city_info else False)
            matches.append(client.address.id_city in matching_city_ids)
        
        if any(matches):
            filtered_clients.append(client)
    
    return render_template('clients.html', clients=filtered_clients, search_query=query_text)

@bp.route('/city/add', methods=['POST'])
def add_city():
    """Добавление нового города через AJAX"""
    if not request.is_json:
        return jsonify({'success': False, 'message': 'Требуется JSON'})
    
    request_data = request.get_json()
    if not request_data:
        return jsonify({'success': False, 'message': 'Нет данных в запросе'})
    
    city_name = request_data.get('city_name', '').strip()
    
    if not city_name:
        return jsonify({'success': False, 'message': 'Название города обязательно'})
    
    # Проверяем, существует ли уже такой город
    existing_city = City.query.filter_by(city_name=city_name).first()
    if existing_city:
        return jsonify({'success': False, 'message': 'Такой город уже существует'})
    
    try:
        city = City(city_name=city_name)
        db.session.add(city)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Город успешно добавлен',
            'city': {'id': city.id, 'name': city.city_name}
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Ошибка: {str(e)}'})

def create_client_folder(client, city, address, move_from=None):
    """Создание папки для клиента"""
    from flask import current_app
    
    # Определяем базовую папку для работы
    work_folder = current_app.config.get('WORK_FOLDER', './work_files')
    
    # Формируем путь к папке
    folder_path = os.path.join(
        work_folder,
        client.service_name,
        city.city_name,
        f"{address} {client.sur_name}"
    )
    
    # Создаем папку если её нет
    if not os.path.exists(folder_path):
        os.makedirs(folder_path, exist_ok=True)
    
    # Если нужно переместить существующую папку
    if move_from and os.path.exists(move_from) and move_from != folder_path:
        if os.path.exists(folder_path):
            # Если целевая папка уже существует, удаляем её
            shutil.rmtree(folder_path)
        
        # Перемещаем папку
        shutil.move(move_from, folder_path)
    
    return os.path.abspath(folder_path)
@bp.route('/settings')
def settings():
    """Страница настроек"""
    from flask import current_app
    import os
    
    # Получаем текущие настройки
    current_settings = {
        'database_path': current_app.config.get('SQLALCHEMY_DATABASE_URI', '').replace('sqlite:///', ''),
        'work_folder': current_app.config.get('WORK_FOLDER', './work_files'),
        'docs_folder': current_app.config.get('DOCS_FOLDER', './docs'),
        'upload_folder': current_app.config.get('UPLOAD_FOLDER', './uploads')
    }
    
    # Проверяем существование путей
    path_status = {}
    for key, path in current_settings.items():
        if path and path != '':
            abs_path = os.path.abspath(path)
            path_status[key] = {
                'exists': os.path.exists(abs_path),
                'is_dir': os.path.isdir(abs_path) if os.path.exists(abs_path) else False,
                'abs_path': abs_path,
                'writable': os.access(abs_path, os.W_OK) if os.path.exists(abs_path) else False
            }
        else:
            path_status[key] = {
                'exists': False,
                'is_dir': False,
                'abs_path': '',
                'writable': False
            }
    
    return render_template('settings.html', 
                         settings=current_settings, 
                         path_status=path_status)

@bp.route('/settings', methods=['POST'])
def settings_post():
    """Обработка сохранения настроек"""
    try:
        # Получаем новые настройки из формы
        new_database_path = request.form.get('database_path', '').strip()
        new_work_folder = request.form.get('work_folder', '').strip()
        new_docs_folder = request.form.get('docs_folder', '').strip()
        new_upload_folder = request.form.get('upload_folder', '').strip()
        
        # Проверяем обязательные поля
        if not new_database_path:
            flash('Путь к базе данных обязателен', 'error')
            return redirect(url_for('main.settings'))
        
        if not new_work_folder:
            flash('Рабочая папка обязательна', 'error')
            return redirect(url_for('main.settings'))
        
        # Проверяем и создаем папки если нужно
        folders_to_check = [
            ('work_folder', new_work_folder, 'Рабочая папка'),
            ('docs_folder', new_docs_folder, 'Папка шаблонов'),
            ('upload_folder', new_upload_folder, 'Папка загрузок')
        ]
        
        for folder_key, folder_path, folder_name in folders_to_check:
            if folder_path:
                abs_path = os.path.abspath(folder_path)
                
                # Создаем папку если её нет
                if not os.path.exists(abs_path):
                    try:
                        os.makedirs(abs_path, exist_ok=True)
                        flash(f'{folder_name} создана: {abs_path}', 'success')
                    except Exception as e:
                        flash(f'Ошибка создания {folder_name.lower()}: {str(e)}', 'error')
                        return redirect(url_for('main.settings'))
                
                # Проверяем права доступа
                if not os.access(abs_path, os.W_OK):
                    flash(f'Нет прав записи в {folder_name.lower()}: {abs_path}', 'error')
                    return redirect(url_for('main.settings'))
        
        # Проверяем базу данных
        db_dir = os.path.dirname(os.path.abspath(new_database_path))
        if not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir, exist_ok=True)
                flash(f'Папка для базы данных создана: {db_dir}', 'success')
            except Exception as e:
                flash(f'Ошибка создания папки для БД: {str(e)}', 'error')
                return redirect(url_for('main.settings'))
        
        # Сохраняем настройки в .env файл
        env_path = os.path.join(os.getcwd(), '.env')
        env_lines = []
        
        # Читаем существующий .env файл
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                env_lines = f.readlines()
        
        # Обновляем настройки
        settings_to_update = {
            'DATABASE_URL': f'sqlite:///{new_database_path}',
            'WORK_FOLDER': new_work_folder,
            'DOCS_FOLDER': new_docs_folder,
            'UPLOAD_FOLDER': new_upload_folder if new_upload_folder else './uploads'
        }
        
        # Обновляем существующие строки или добавляем новые
        updated_keys = set()
        for i, line in enumerate(env_lines):
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                key = line.split('=')[0].strip()
                if key in settings_to_update:
                    env_lines[i] = f"{key}={settings_to_update[key]}\n"
                    updated_keys.add(key)
        
        # Добавляем новые ключи
        for key, value in settings_to_update.items():
            if key not in updated_keys:
                env_lines.append(f"{key}={value}\n")
        
        # Сохраняем обновленный .env файл
        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(env_lines)
        
        flash('Настройки сохранены! Перезапустите приложение для применения изменений.', 'success')
        return redirect(url_for('main.settings'))
        
    except Exception as e:
        flash(f'Ошибка при сохранении настроек: {str(e)}', 'error')
        return redirect(url_for('main.settings'))

@bp.route('/settings/test-database')
def test_database():
    """Тестирование подключения к базе данных"""
    try:
        from app import db
        from app.models import Client
        
        # Пробуем выполнить простой запрос
        count = Client.query.count()
        
        return jsonify({
            'success': True,
            'message': f'Подключение к базе данных успешно. Найдено {count} клиентов.',
            'clients_count': count
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Ошибка подключения к базе данных: {str(e)}',
            'error': str(e)
        })

@bp.route('/settings/create-folders', methods=['POST'])
def create_folders():
    """Создание всех необходимых папок"""
    try:
        if request.is_json and request.json is not None:
            folders = request.json.get('folders', [])
        else:
            folders = request.form.getlist('folders')
        
        created_folders = []
        errors = []
        
        for folder_path in folders:
            if folder_path and folder_path.strip():
                abs_path = os.path.abspath(folder_path.strip())
                try:
                    os.makedirs(abs_path, exist_ok=True)
                    created_folders.append(abs_path)
                except Exception as e:
                    errors.append(f'Ошибка создания {abs_path}: {str(e)}')
        
        return jsonify({
            'success': len(created_folders) > 0,
            'created_folders': created_folders,
            'errors': errors
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'errors': [f'Ошибка: {str(e)}'],
            'created_folders': []
        })
# Добавьте этот код в app/routes.py

@bp.route('/test-static')
def test_static():
    """Тестовая страница для проверки загрузки статических файлов"""
    import os
    from pathlib import Path
    from flask import current_app, url_for
    
    # Проверяем конфигурацию Flask
    static_folder = current_app.static_folder or ""
    static_url_path = current_app.static_url_path or ""
    root_path = current_app.root_path or ""
    
    # Проверяем существование файлов
    css_files = ['main.css', 'tables.css', 'forms.css', 'modals.css']
    file_status = {}
    
    for css_file in css_files:
        # Используем pathlib для безопасной работы с путями
        static_path = Path(static_folder)
        css_path = static_path / 'css' / css_file
        
        file_status[css_file] = {
            'exists': css_path.exists(),
            'path': str(css_path.absolute()),
            'size': css_path.stat().st_size if css_path.exists() else 0,
            'url': url_for('static', filename=f'css/{css_file}')
        }
    
    # Собираем HTML
    html_parts = [
        """<!DOCTYPE html>
<html>
<head>
    <title>Тест статических файлов</title>
    <link href=\"""" + url_for('static', filename='css/main.css') + """\" rel="stylesheet">
</head>
<body>
    <h1>Тест статических файлов</h1>
    
    <h2>Конфигурация Flask:</h2>
    <ul>
        <li><strong>static_folder:</strong> """ + static_folder + """</li>
        <li><strong>static_url_path:</strong> """ + static_url_path + """</li>
        <li><strong>app.root_path:</strong> """ + root_path + """</li>
    </ul>
    
    <h2>Статус CSS файлов:</h2>
    <ul>"""
    ]
    
    for file_name, status in file_status.items():
        exists_text = "✅ Существует" if status["exists"] else "❌ Не найден"
        html_parts.append(f"""
        <li>
            <strong>{file_name}:</strong> {exists_text} ({status["size"]} байт)<br>
            Путь: <code>{status["path"]}</code><br>
            URL: <a href="{status["url"]}" target="_blank">{status["url"]}</a>
        </li>""")
    
    html_parts.append("""
    </ul>
    
    <h2>Тест стилей:</h2>
    <p style="color: var(--primary-color, red); font-size: 18px; font-weight: bold;">
        Этот текст должен быть синим (#667eea) если CSS переменные загружаются
    </p>
    
    <div style="background: var(--primary-gradient, red); color: white; padding: 1rem; border-radius: var(--border-radius, 0); margin: 1rem 0;">
        Этот блок должен иметь градиентный фон если CSS загружается
    </div>
    
    <h2>Дополнительные проверки:</h2>
    <ul>""")
    
    # Дополнительные проверки
    static_path = Path(static_folder)
    checks = [
        ("Static папка существует", static_path.exists()),
        ("CSS папка существует", (static_path / 'css').exists()),
        ("Права на чтение static", static_path.exists() and os.access(str(static_path), os.R_OK)),
    ]
    
    for check_name, result in checks:
        status_icon = "✅" if result else "❌"
        html_parts.append(f"<li>{status_icon} {check_name}</li>")
    
    html_parts.append("""
    </ul>
    
    <h2>Список файлов в CSS папке:</h2>
    <ul>""")
    
    css_folder = static_path / 'css'
    if css_folder.exists():
        try:
            for css_file in css_folder.iterdir():
                if css_file.is_file():
                    html_parts.append(f"<li>{css_file.name} ({css_file.stat().st_size} байт)</li>")
        except Exception as e:
            html_parts.append(f"<li>Ошибка чтения папки: {e}</li>")
    else:
        html_parts.append("<li>CSS папка не найдена</li>")
    
    html_parts.append("""
    </ul>
</body>
</html>""")
    
    return ''.join(html_parts)