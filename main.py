"""АвтоПоиск: учебный каталог с локальным поиском и рейтингом дизайна."""
import json
import os
from pathlib import Path
import secrets
import sqlite3
from urllib.parse import urlsplit

from flask import Flask, abort, g, redirect, render_template, request, session, url_for
from search import SORTS, parse_query, select_cars
from marketplace import drom_url

ROOT = Path(__file__).resolve().parent


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        DATABASE=os.environ.get('DATABASE_PATH', str(Path(app.instance_path) / 'cars.sqlite3')),
        MAX_CONTENT_LENGTH=16 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=os.environ.get('COOKIE_SECURE') == '1',
    )
    if test_config:
        app.config.update(test_config)
    Path(app.config['DATABASE']).parent.mkdir(parents=True, exist_ok=True)
    # Ключ сохраняется между перезапусками и одинаков для всех gunicorn workers.
    if not app.config.get('SECRET_KEY'):
        app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
    if not app.config.get('SECRET_KEY'):
        key_path = Path(app.config['DATABASE']).with_suffix('.key')
        try:
            fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(fd, 'w') as stream:
                stream.write(secrets.token_hex(32))
        app.config['SECRET_KEY'] = key_path.read_text().strip()
        if not app.config['SECRET_KEY']:
            raise RuntimeError('Пустой файл ключа сессии. Укажите SECRET_KEY в окружении.')

    def db():
        if 'db' not in g:
            g.db = sqlite3.connect(app.config['DATABASE'], timeout=15)
            g.db.row_factory = sqlite3.Row
            g.db.execute('PRAGMA foreign_keys = ON')
        return g.db

    @app.teardown_appcontext
    def close_db(error=None):
        connection = g.pop('db', None)
        if connection is not None:
            connection.close()

    with app.app_context():
        db().executescript('''
            CREATE TABLE IF NOT EXISTS cars (
                id INTEGER PRIMARY KEY, brand TEXT NOT NULL, model TEXT NOT NULL,
                country TEXT NOT NULL, body_type TEXT NOT NULL, engine_power INTEGER NOT NULL,
                engine_volume REAL NOT NULL, demo_design_score REAL NOT NULL,
                price INTEGER NOT NULL, fuel_type TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS ratings (
                car_id INTEGER NOT NULL REFERENCES cars(id), voter TEXT NOT NULL,
                score INTEGER NOT NULL CHECK(score BETWEEN 1 AND 5),
                PRIMARY KEY(car_id, voter)
            );
        ''')
        seed = json.loads((ROOT / 'data/cars.json').read_text())
        db().executemany('''INSERT OR IGNORE INTO cars VALUES
            (:id,:brand,:model,:country,:body_type,:engine_power,:engine_volume,:demo_design_score,:price,:fuel_type)''', seed)
        db().commit()

    def catalogue():
        rows = db().execute('''SELECT c.*, COUNT(r.score) AS votes,
            COALESCE(AVG(r.score), c.demo_design_score) AS design_score
            FROM cars c LEFT JOIN ratings r ON c.id=r.car_id GROUP BY c.id''').fetchall()
        return [dict(row) for row in rows]

    def get_car(car_id):
        car = next((car for car in catalogue() if car['id'] == car_id), None)
        if car is None:
            abort(404)
        return car

    @app.context_processor
    def template_context():
        if 'csrf' not in session:
            session['csrf'] = secrets.token_hex(32)
        return dict(csrf_token=session['csrf'], favorites=session.get('favorites', []), sorts=SORTS)

    @app.template_filter('rubles')
    def rubles(value):
        return f'{value:,.0f}'.replace(',', ' ') + ' ₽'

    @app.template_filter('vote_count')
    def vote_count(value):
        ending = 'оценок' if 11 <= value % 100 <= 14 else 'оценка' if value % 10 == 1 else 'оценки' if value % 10 in (2, 3, 4) else 'оценок'
        return f'{value} {ending}'

    @app.before_request
    def protect_forms():
        if request.method == 'POST':
            token = request.form.get('csrf_token', '')
            if not token or not secrets.compare_digest(token, session.get('csrf', '')):
                abort(400, description='Форма устарела. Обновите страницу и повторите действие.')

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self'; img-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'self'"
        response.headers['Cache-Control'] = 'no-store'
        return response

    def listing(favorites_only=False):
        query = request.args.get('query', '').strip()
        if len(query) > 300:
            abort(400, description='Запрос должен быть не длиннее 300 символов.')
        sort = request.args.get('sort', 'default')
        if sort not in SORTS:
            sort = 'default'
        cars = catalogue()
        plan = parse_query(query, cars)
        if favorites_only:
            cars = [car for car in cars if car['id'] in session.get('favorites', [])]
        return render_template('index.html', results=select_cars(cars, plan, sort),
                               query=query, sort=sort, plan=plan, favorites_only=favorites_only,
                               title='Избранное' if favorites_only else 'Каталог автомобилей',
                               total=len(cars))

    @app.get('/')
    @app.get('/search')
    def home():
        return listing()

    @app.get('/electric')
    def electric():
        return redirect(url_for('home', query='электромобиль'))

    @app.get('/cheap')
    def cheap():
        return redirect(url_for('home', query='недорогая'))

    @app.get('/favorites')
    def show_favorites():
        return listing(favorites_only=True)

    def safe_next():
        target = request.form.get('next', '/')
        try:
            parts = urlsplit(target)
        except ValueError:
            return url_for('home')
        if parts.scheme or parts.netloc or not target.startswith('/') or target.startswith('//') or '\\' in target or any(ord(c) < 32 for c in target):
            return url_for('home')
        return target

    @app.post('/favorite/<int:car_id>')
    def toggle_favorite(car_id):
        get_car(car_id)
        favorites = session.get('favorites', [])
        if car_id in favorites:
            favorites.remove(car_id)
        else:
            favorites.append(car_id)
        session['favorites'] = favorites
        return redirect(safe_next(), code=303)

    @app.get('/car/<int:car_id>')
    def car_details(car_id):
        car = get_car(car_id)
        vote = db().execute('SELECT score FROM ratings WHERE car_id=? AND voter=?',
                            (car_id, session.get('voter', ''))).fetchone()
        return render_template('car.html', car=car, title=f"{car['brand']} {car['model']}", my_vote=vote['score'] if vote else None)

    @app.post('/rate/<int:car_id>')
    def rate_car(car_id):
        get_car(car_id)
        score = request.form.get('score', type=int)
        if score not in range(1, 6):
            abort(400, description='Выберите оценку от 1 до 5.')
        if 'voter' not in session:
            session['voter'] = secrets.token_hex(24)
        db().execute('''INSERT INTO ratings(car_id,voter,score) VALUES (?,?,?)
            ON CONFLICT(car_id,voter) DO UPDATE SET score=excluded.score''',
                     (car_id, session['voter'], score))
        db().commit()
        return redirect(url_for('car_details', car_id=car_id), code=303)

    @app.get('/buy/<int:car_id>')
    def buy_car(car_id):
        destination = drom_url(get_car(car_id))
        if destination is None:
            abort(404)
        return redirect(destination)

    @app.get('/about')
    def about():
        return render_template('about.html', title='Как работает подбор')

    @app.get('/health')
    def health():
        db().execute('SELECT 1 FROM cars LIMIT 1').fetchone()
        return {'status': 'ok'}

    @app.errorhandler(400)
    @app.errorhandler(404)
    @app.errorhandler(413)
    def error_page(error):
        return render_template('error.html', title='Не удалось открыть страницу', error=error), error.code

    return app


app = create_app()

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=int(os.environ.get('PORT', 5000)))
