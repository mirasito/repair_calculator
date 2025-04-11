from flask import Flask, render_template, request, jsonify, g
import os
from dotenv import load_dotenv
import math
import json
import sqlite3
import logging

# Загружаем переменные окружения из файла .env
load_dotenv()

# Назначение файла базы данных
DATABASE = 'repair_calculator.db'

# Словарь с базовыми ценами за квадратный метр для разных качеств материалов (в тенге)
PRICES = {
    'standard': {
        'materials': 15000,  # 3000 руб -> 15000 тг
        'work': 10000,       # 2000 руб -> 10000 тг
        'bathroom': {'materials': 7500, 'work': 5000},
        'kitchen': {'materials': 10000, 'work': 7500},
        'window': {'materials': 2500, 'work': 1500},
        'replanning': {'materials': 5000, 'work': 10000}
    },
    'standard_plus': {
        'materials': 25000,  # 5000 руб -> 25000 тг
        'work': 15000,       # 3000 руб -> 15000 тг
        'bathroom': {'materials': 12500, 'work': 7500},
        'kitchen': {'materials': 17500, 'work': 12500},
        'window': {'materials': 4000, 'work': 2500},
        'replanning': {'materials': 7500, 'work': 15000}
    },
    'premium': {
        'materials': 40000,  # 8000 руб -> 40000 тг
        'work': 25000,       # 5000 руб -> 25000 тг
        'bathroom': {'materials': 20000, 'work': 12500},
        'kitchen': {'materials': 30000, 'work': 20000},
        'window': {'materials': 6000, 'work': 4000},
        'replanning': {'materials': 12500, 'work': 25000}
    }
}

# Словарь с деталями каждого этапа ремонта:
STEP_DETAILS = {
    'replanning': {
        'icon': '🏗️',
        'materials': [
            {
                'name_ru': 'Кирпич строительный',
                'name_en': 'Construction brick',
                'unit_ru': 'шт',
                'unit_en': 'pcs',
                'base_quantity': 100,  # на 10 кв.м.
                'base_price': 150
            },
            {
                'name_ru': 'Раствор цементный',
                'name_en': 'Cement mortar',
                'unit_ru': 'кг',
                'unit_en': 'kg',
                'base_quantity': 50,  # на 10 кв.м.
                'base_price': 100
            }
        ],
        'works': [
            {
                'name_ru': 'Демонтаж стен',
                'name_en': 'Wall demolition',
                'unit_ru': 'м²',
                'unit_en': 'm²',
                'base_quantity': 1,
                'base_price': 2000
            },
            {
                'name_ru': 'Возведение стен',
                'name_en': 'Wall construction',
                'unit_ru': 'м²',
                'unit_en': 'm²',
                'base_quantity': 1,
                'base_price': 3000
            }
        ]
    },
    'demolition': {
        'icon': '🔨',
        'materials': [
            {'name': 'Мешки для мусора', 'unit': 'шт', 'price': 100},
            {'name': 'Перчатки', 'unit': 'пар', 'price': 500},
            {'name': 'Защитные очки', 'unit': 'шт', 'price': 800}
        ],
        'works': [
            {'name': 'Демонтаж стен', 'unit': 'м²', 'price': 1500},
            {'name': 'Демонтаж пола', 'unit': 'м²', 'price': 800},
            {'name': 'Вывоз мусора', 'unit': 'м³', 'price': 2000}
        ]
    },
    'rough_work': {
        'icon': '🏗️',
        'materials': [
            {
                'name_ru': 'Штукатурка',
                'name_en': 'Plaster',
                'unit_ru': 'кг',
                'unit_en': 'kg',
                'base_quantity': 30,  # на 10 кв.м.
                'base_price': 200
            },
            {
                'name_ru': 'Грунтовка',
                'name_en': 'Primer',
                'unit_ru': 'л',
                'unit_en': 'l',
                'base_quantity': 5,  # на 10 кв.м.
                'base_price': 300
            }
        ],
        'works': [
            {
                'name_ru': 'Выравнивание стен',
                'name_en': 'Wall leveling',
                'unit_ru': 'м²',
                'unit_en': 'm²',
                'base_quantity': 1,
                'base_price': 1000
            },
            {
                'name_ru': 'Выравнивание пола',
                'name_en': 'Floor leveling',
                'unit_ru': 'м²',
                'unit_en': 'm²',
                'base_quantity': 1,
                'base_price': 800
            }
        ]
    },
    'plumbing': {
        'icon': '🚰',
        'materials': [
            {'name': 'Трубы', 'unit': 'м', 'price': 800},
            {'name': 'Фитинги', 'unit': 'шт', 'price': 500},
            {'name': 'Сантехника', 'unit': 'шт', 'price': 15000}
        ],
        'works': [
            {'name': 'Прокладка труб', 'unit': 'м', 'price': 1000},
            {'name': 'Установка фитингов', 'unit': 'шт', 'price': 300},
            {'name': 'Монтаж сантехники', 'unit': 'шт', 'price': 2000}
        ]
    },
    'electrical': {
        'icon': '⚡',
        'materials': [
            {'name': 'Кабель', 'unit': 'м', 'price': 200},
            {'name': 'Розетки', 'unit': 'шт', 'price': 500},
            {'name': 'Выключатели', 'unit': 'шт', 'price': 400}
        ],
        'works': [
            {'name': 'Прокладка кабеля', 'unit': 'м', 'price': 300},
            {'name': 'Установка розеток', 'unit': 'шт', 'price': 400},
            {'name': 'Установка выключателей', 'unit': 'шт', 'price': 400}
        ]
    },
    'finishing': {
        'icon': '🎨',
        'materials': [
            {
                'name_ru': 'Краска',
                'name_en': 'Paint',
                'unit_ru': 'л',
                'unit_en': 'l',
                'base_quantity': 5,  # на 10 кв.м.
                'base_price': 1000
            },
            {
                'name_ru': 'Обои',
                'name_en': 'Wallpaper',
                'unit_ru': 'рул',
                'unit_en': 'roll',
                'base_quantity': 2,  # на 10 кв.м.
                'base_price': 3000
            },
            {
                'name_ru': 'Ламинат',
                'name_en': 'Laminate',
                'unit_ru': 'м²',
                'unit_en': 'm²',
                'base_quantity': 10,
                'base_price': 2000
            }
        ],
        'works': [
            {
                'name_ru': 'Поклейка обоев',
                'name_en': 'Wallpaper installation',
                'unit_ru': 'м²',
                'unit_en': 'm²',
                'base_quantity': 1,
                'base_price': 800
            },
            {
                'name_ru': 'Укладка ламината',
                'name_en': 'Laminate installation',
                'unit_ru': 'м²',
                'unit_en': 'm²',
                'base_quantity': 1,
                'base_price': 600
            },
            {
                'name_ru': 'Покраска потолка',
                'name_en': 'Ceiling painting',
                'unit_ru': 'м²',
                'unit_en': 'm²',
                'base_quantity': 1,
                'base_price': 500
            }
        ]
    },
    'windows': {
        'icon': '🪟',
        'materials': [
            {'name': 'Окна', 'unit': 'шт', 'price': 50000},
            {'name': 'Подоконники', 'unit': 'шт', 'price': 5000},
            {'name': 'Отливы', 'unit': 'шт', 'price': 3000}
        ],
        'works': [
            {'name': 'Демонтаж старых окон', 'unit': 'шт', 'price': 2000},
            {'name': 'Установка новых окон', 'unit': 'шт', 'price': 5000},
            {'name': 'Установка подоконников', 'unit': 'шт', 'price': 2000}
        ]
    }
}

def create_app():
    """
    Фабрика приложения Flask. Здесь происходит настройка, регистрация маршрутов и соединения с базой данных.
    """
    app = Flask(__name__)
    logging.basicConfig(level=logging.INFO)

    def get_db():
        """
        Получает соединение с базой данных для текущего контекста.
        """
        db = getattr(g, '_database', None)
        if db is None:
            db = g._database = sqlite3.connect(DATABASE)
            db.row_factory = sqlite3.Row
        return db

    @app.teardown_appcontext
    def close_connection(exception):
        """
        Закрывает соединение с базой данных по окончании запроса.
        """
        db = getattr(g, '_database', None)
        if db is not None:
            db.close()

    def init_db():
        """
        Инициализирует базу данных, выполняя SQL-скрипт из файла schema.sql.
        """
        with app.app_context():
            db = get_db()
            with app.open_resource('schema.sql', mode='r') as f:
                db.cursor().executescript(f.read())
            db.commit()
            app.logger.info("База данных инициализирована.")

    def setup_directories():
        """
        Создает необходимые директории для шаблонов и статических файлов,
        если они не существуют.
        """
        if not os.path.exists('templates'):
            os.makedirs('templates')
            app.logger.info("Директория 'templates' создана.")
        if not os.path.exists('static'):
            os.makedirs('static')
            app.logger.info("Директория 'static' создана.")

    def calculate_step_details(step_key, area, quality, ceiling_coefficient=1.0):
        """
        Рассчитывает детали (материалы и работы) для конкретного этапа ремонта.

        :param step_key: Ключ этапа (например, 'replanning')
        :param area: Площадь квартиры в кв.м.
        :param quality: Качество материалов ('standard', 'standard_plus', 'premium')
        :param ceiling_coefficient: Коэффициент для высоты потолков (по умолчанию 1.0)
        :return: Словарь с информацией о материалах и работах для этапа
        """
        step = STEP_DETAILS[step_key]
        quality_multiplier = {
            'standard': 1.0,
            'standard_plus': 1.5,
            'premium': 2.0
        }[quality]
        area_coefficient = math.ceil(area / 10)  # Количество десятков кв.м.
        materials = []
        for material in step['materials']:
            if 'base_quantity' in material:
                quantity = material['base_quantity'] * area_coefficient
                price = material['base_price'] * quality_multiplier
                materials.append({
                    'name_ru': material['name_ru'],
                    'name_en': material['name_en'],
                    'unit_ru': material['unit_ru'],
                    'unit_en': material['unit_en'],
                    'quantity': quantity,
                    'price': price
                })
            else:
                # Для формата данных без базовой величины
                quantity = area_coefficient
                price = material['price'] * quality_multiplier
                materials.append({
                    'name_ru': material['name'],
                    'name_en': material['name'],
                    'unit_ru': material['unit'],
                    'unit_en': material['unit'],
                    'quantity': quantity,
                    'price': price
                })
        works = []
        for work in step['works']:
            if 'base_quantity' in work:
                if work['unit_ru'] == 'м²':
                    quantity = area
                else:
                    quantity = work['base_quantity'] * area_coefficient
                price = work['base_price'] * quality_multiplier
                works.append({
                    'name_ru': work['name_ru'],
                    'name_en': work['name_en'],
                    'unit_ru': work['unit_ru'],
                    'unit_en': work['unit_en'],
                    'quantity': quantity,
                    'price': price
                })
            else:
                if work['unit'] == 'м²':
                    quantity = area
                else:
                    quantity = area_coefficient
                price = work['price'] * quality_multiplier
                works.append({
                    'name_ru': work['name'],
                    'name_en': work['name'],
                    'unit_ru': work['unit'],
                    'unit_en': work['unit'],
                    'quantity': quantity,
                    'price': price
                })
        return {
            'materials': materials,
            'works': works
        }

    # Регистрация маршрутов (routes)

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/planning')
    def planning_overview():
        # Отображает общую страницу планирования (данные могут подтягиваться с localStorage через JS)
        return render_template('planning.html')

    @app.route('/planning/<int:estimate_id>')
    def planning(estimate_id):
        # Получает данные сметы по id из базы данных и отображает страницу планирования
        estimate = get_db().execute(
            'SELECT * FROM estimates WHERE id = ?',
            (estimate_id,)
        ).fetchone()
        if estimate is None:
            return render_template('error.html', message='Смета не найдена'), 404
        return render_template('planning.html', estimate=estimate)

    @app.route('/calculate', methods=['POST'])
    def calculate():
        data = request.json
        quality = data['materials_quality']
        # Коэффициент для высоты потолков (если выше 3м)
        ceiling_coefficient = max(1.0, data['ceiling_height'] / 3.0)
        steps = []
        base_duration = math.ceil(data['apartment_size'] / 10)  # 10 кв.м. в день – базовый показатель
        total_materials = 0
        total_work = 0

        # Этап перепланировки
        if data['replanning']:
            step_details = calculate_step_details('replanning', data['apartment_size'], quality, ceiling_coefficient)
            step_materials = sum(item['price'] * item['quantity'] for item in step_details['materials'])
            step_works = sum(item['price'] * item['quantity'] for item in step_details['works'])
            total_materials += step_materials
            total_work += step_works
            steps.append({
                'title': 'Перепланировка',
                'title_en': 'Replanning',
                'duration': math.ceil(base_duration * 0.5),
                'icon': STEP_DETAILS['replanning']['icon'],
                **step_details
            })

        # Остальные этапы ремонта
        other_steps = [
            {'key': 'demolition', 'title': 'Демонтаж', 'title_en': 'Demolition', 'duration_coef': 0.3},
            {'key': 'rough_work', 'title': 'Черновые работы', 'title_en': 'Rough Work', 'duration_coef': 1.0},
            {'key': 'plumbing', 'title': 'Сантехника', 'title_en': 'Plumbing', 'duration_coef': 0.2},
            {'key': 'electrical', 'title': 'Электрика', 'title_en': 'Electrical', 'duration_coef': 0.5},
            {'key': 'finishing', 'title': 'Отделочные работы', 'title_en': 'Finishing', 'duration_coef': 2.0}
        ]
        for step in other_steps:
            step_details = calculate_step_details(step['key'], data['apartment_size'], quality, ceiling_coefficient)
            # Если это сантехника, умножаем количество материалов и работ на число санузлов
            if step['key'] == 'plumbing':
                for material in step_details['materials']:
                    material['quantity'] *= data['bathrooms_count']
                for work in step_details['works']:
                    work['quantity'] *= data['bathrooms_count']
            step_materials = sum(item['price'] * item['quantity'] for item in step_details['materials'])
            step_works = sum(item['price'] * item['quantity'] for item in step_details['works'])
            total_materials += step_materials
            total_work += step_works
            steps.append({
                'title': step['title'],
                'title_en': step['title_en'],
                'duration': math.ceil(base_duration * step['duration_coef']),
                'icon': STEP_DETAILS[step['key']]['icon'],
                **step_details
            })

        # Этап установки окон
        window_details = {
            'materials': [{
                'name_ru': 'Окно с установкой',
                'name_en': 'Window with installation',
                'unit_ru': 'шт',
                'unit_en': 'pcs',
                'quantity': data['windows_count'],
                'price': PRICES[quality]['window']['materials']
            }],
            'works': [{
                'name_ru': 'Монтаж окна',
                'name_en': 'Window installation',
                'unit_ru': 'шт',
                'unit_en': 'pcs',
                'quantity': data['windows_count'],
                'price': PRICES[quality]['window']['work']
            }]
        }
        if data['windows_count'] > 0:
            steps.append({
                'title': 'Установка окон',
                'title_en': 'Window Installation',
                'duration': data['windows_count'],
                'icon': STEP_DETAILS['windows']['icon'],
                **window_details
            })
            total_materials += sum(item['price'] * item['quantity'] for item in window_details['materials'])
            total_work += sum(item['price'] * item['quantity'] for item in window_details['works'])

        return jsonify({
            'materials_cost': round(total_materials),
            'work_cost': round(total_work),
            'total_cost': round(total_materials + total_work),
            'steps': steps
        })

    @app.route('/add_step', methods=['POST'])
    def add_step():
        data = request.json
        step_key = data['key']
        step_title_ru = data['title_ru']
        step_title_en = data['title_en']
        step_icon = data.get('icon', '🔨')  # Если иконка не указана, используется стандартная
        # Добавляем новый этап в глобальный словарь STEP_DETAILS
        STEP_DETAILS[step_key] = {
            'icon': step_icon,
            'materials': [
                {'name': 'Материалы', 'unit': 'шт', 'price': 1000},
                {'name': 'Инструменты', 'unit': 'шт', 'price': 500}
            ],
            'works': [
                {'name': 'Работы', 'unit': 'м²', 'price': 1500},
                {'name': 'Дополнительные работы', 'unit': 'шт', 'price': 800}
            ]
        }
        return jsonify({'success': True, 'message': 'Этап успешно добавлен'})

    @app.route('/api/planning/<int:estimate_id>', methods=['GET'])
    def get_planning(estimate_id):
        try:
            planning_data = get_db().execute(
                'SELECT data FROM planning WHERE estimate_id = ?',
                (estimate_id,)
            ).fetchone()
            if planning_data is None:
                return jsonify({'weeks': []})
            return jsonify(json.loads(planning_data['data']))
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/planning/<int:estimate_id>', methods=['POST'])
    def save_planning(estimate_id):
        try:
            data = request.get_json()
            db = get_db()
            # Проверка: существует ли уже план для данной сметы
            existing = db.execute(
                'SELECT id FROM planning WHERE estimate_id = ?',
                (estimate_id,)
            ).fetchone()
            if existing:
                db.execute(
                    'UPDATE planning SET data = ?, updated_at = CURRENT_TIMESTAMP WHERE estimate_id = ?',
                    (json.dumps(data), estimate_id)
                )
            else:
                db.execute(
                    'INSERT INTO planning (estimate_id, data) VALUES (?, ?)',
                    (estimate_id, json.dumps(data))
                )
            db.commit()
            return jsonify({'status': 'success'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/marketplace')
    def marketplace():
        return render_template('marketplace.html')

    @app.route('/budget')
    def budget():
        return render_template('budget.html')

    # Обработчики ошибок

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('error.html', message='Страница не найдена'), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('error.html', message='Внутренняя ошибка сервера'), 500

    # Выполняем начальную настройку: создание необходимых директорий
    setup_directories()
    # Если необходимо инициализировать базу данных, раскомментируйте следующую строку:
    # init_db()

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5002)