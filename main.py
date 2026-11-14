from flask import Flask, render_template, request, session, redirect, url_for
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_school_project'

CARS_DATA = [
    ('Lada', 'Niva', 'Россия', 'внедорожник', 80, 1.7, 3, 800000, 'Бензин'),
    ('Lada', 'Vesta', 'Россия', 'седан', 106, 1.6, 4, 1200000, 'Бензин'),
    ('Lada', 'Granta', 'Россия', 'седан', 87, 1.6, 3, 700000, 'Бензин'),
    ('Lada', 'Niva Legend', 'Россия', 'внедорожник', 83, 1.7, 3, 950000, 'Бензин'),
    ('UAZ', 'Patriot', 'Россия', 'внедорожник', 150, 2.7, 3, 1500000, 'Бензин'),
    ('GAZ', 'Volga Siber', 'Россия', 'седан', 143, 2.4, 3, 600000, 'Бензин'),
    ('Moskvich', '3', 'Россия', 'кроссовер', 150, 1.5, 2, 1900000, 'Бензин'),
    ('Toyota', 'Camry', 'Япония', 'седан', 200, 2.5, 5, 3000000, 'Бензин'),
    ('Toyota', 'Supra', 'Япония', 'купе', 340, 3.0, 5, 5500000, 'Бензин'),
    ('Toyota', 'Land Cruiser', 'Япония', 'внедорожник', 249, 4.0, 4, 8000000, 'Бензин'),
    ('Honda', 'Civic Type R', 'Япония', 'хэтчбек', 320, 2.0, 4, 4500000, 'Бензин'),
    ('Nissan', 'Leaf', 'Япония', 'хэтчбек', 150, 0.0, 3, 2000000, 'Электро'),
    ('Nissan', 'GT-R R35', 'Япония', 'купе', 570, 3.8, 5, 8000000, 'Бензин'),
    ('BMW', 'M3', 'Германия', 'купе', 510, 3.0, 5, 7000000, 'Бензин'),
    ('BMW', 'i4', 'Германия', 'седан', 340, 0.0, 4, 5000000, 'Электро'),
    ('Mercedes-Benz', 'S-Class', 'Германия', 'седан', 435, 4.0, 5, 12000000, 'Бензин'),
    ('Audi', 'R8', 'Германия', 'купе', 570, 5.2, 5, 14000000, 'Бензин'),
    ('Porsche', 'Taycan', 'Германия', 'седан', 408, 0.0, 5, 8500000, 'Электро'),
    ('Porsche', '911', 'Германия', 'купе', 385, 3.0, 5, 10000000, 'Бензин'),
    ('Volkswagen', 'Polo', 'Германия', 'хэтчбек', 110, 1.6, 3, 1500000, 'Бензин'),
    ('Ferrari', 'Roma', 'Италия', 'купе', 620, 3.9, 5, 20000000, 'Бензин'),
    ('Ford', 'Mustang', 'США', 'купе', 450, 5.0, 4, 4500000, 'Бензин'),
    ('Tesla', 'Model S', 'США', 'седан', 670, 0.0, 4, 6000000, 'Электро'),
    ('Tesla', 'Model 3', 'США', 'седан', 283, 0.0, 4, 3500000, 'Электро'),
    ('Tesla', 'Model Y', 'США', 'кроссовер', 456, 0.0, 4, 4500000, 'Электро'),
    ('Kia', 'Rio', 'Корея', 'седан', 123, 1.6, 4, 1300000, 'Бензин'),
    ('Hyundai', 'Solaris', 'Корея', 'седан', 123, 1.6, 3, 1200000, 'Бензин'),
    ('Hyundai', 'Ioniq 5', 'Корея', 'кроссовер', 325, 0.0, 5, 4500000, 'Электро'),
    ('Geely', 'Monjaro', 'Китай', 'кроссовер', 238, 2.0, 4, 3500000, 'Бензин'),
    ('Haval', 'Jolion', 'Китай', 'кроссовер', 143, 1.5, 3, 2000000, 'Бензин'),
    ('BYD', 'Han', 'Китай', 'седан', 517, 0.0, 4, 4500000, 'Электро'),
    ('Zeekr', '001', 'Китай', 'седан', 544, 0.0, 5, 5000000, 'Электро')
]

def create_temp_db():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE Cars (
        id INTEGER PRIMARY KEY AUTOINCREMENT, brand TEXT, model TEXT, country TEXT, 
        body_type TEXT, engine_power INTEGER, engine_volume REAL, design_score INTEGER, price INTEGER, fuel_type TEXT)''')
    cars_with_ids = [(i+1,) + car for i, car in enumerate(CARS_DATA)]
    cursor.executemany('''INSERT INTO Cars (id, brand, model, country, body_type, engine_power, engine_volume, design_score, price, fuel_type) 
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', cars_with_ids)
    return conn

def search_cars(q, sort_by="default"):
    q = q.lower()
    
    # Словарь стран
    country_map = {
        "русск": "Россия", "росси": "Россия", "советск": "Россия",
        "япон": "Япония", "немец": "Германия", "герман": "Германия",
        "итальян": "Италия", "америк": "США", "сша": "США",
        "коре": "Корея", "китай": "Китай"
    }
    
    # Словарь брендов
    brand_map = {
        "лада": "lada", "ваз": "lada", "жигули": "lada", "тойота": "toyota", "хендай": "hyundai", 
        "хендэ": "hyundai", "киа": "kia", "бмв": "bmw", "мерседес": "mercedes", "мерс": "mercedes", 
        "ауди": "audi", "порше": "porsche", "фольксваген": "volkswagen", "фольц": "volkswagen", 
        "тесла": "tesla", "форд": "ford", "шевроле": "chevrolet", "ниссан": "nissan", "хонда": "honda", 
        "мазда": "mazda", "субару": "subaru", "лексус": "lexus", "феррари": "ferrari", 
        "ламборгини": "lamborghini", "ламбо": "lamborghini", "альфа": "alfa", "джили": "geely", 
        "чери": "chery", "хавал": "haval", "эксид": "exeed", "омода": "omoda", "танк": "tank", 
        "уаз": "uaz", "газ": "gaz", "москвич": "moskvich"
    }

    conn = create_temp_db()
    cursor = conn.cursor()
    sql = "SELECT * FROM Cars WHERE 1=1"
    params = []
    
    # Поиск по стране
    found_country = None
    for key, val in country_map.items():
        if key in q:
            found_country = val
            break
    if found_country:
        sql += " AND country = ?"; params.append(found_country)

    # Поиск по бренду/модели (если это не характеристика)
    features = ["росси", "япон", "немец", "итальян", "америк", "сша", "коре", "китай", 
                "электро", "внедорожник", "джип", "седан", "купе", "спорткар", "хэтчбек", "кроссовер", 
                "красив", "стильн", "быстр", "мощн", "дешев", "недорог", "бюджетн", "дорог", "люкс", "семейн", "город"]
    
    is_feature = any(f in q for f in features)
    
    if q and not is_feature and not found_country:
        for rus, eng in brand_map.items():
            if rus in q:
                q = q.replace(rus, eng)
        
        sql += " AND (brand LIKE ? OR model LIKE ?)"
        params.append(f"%{q}%")
        params.append(f"%{q}%")

    # --- ИСПРАВЛЕННЫЙ БЛОК ПРО ТОПЛИВО ---
    if "электро" in q or "электрич" in q:
        sql += " AND fuel_type = ?"; params.append("Электро")
    
    # Кузов
    if "внедорожник" in q or "джип" in q: sql += " AND body_type = ?"; params.append("внедорожник")
    if "седан" in q: sql += " AND body_type = ?"; params.append("седан")
    if "купе" in q or "спорткар" in q: sql += " AND body_type = ?"; params.append("купе")
    if "хэтчбек" in q or "хетч" in q: sql += " AND body_type = ?"; params.append("хэтчбек")
    if "кроссовер" in q: sql += " AND body_type = ?"; params.append("кроссовер")
    if "город" in q: sql += " AND body_type IN (?, ?, ?)"; params.extend(["седан", "хэтчбек", "кроссовер"])

    # Характеристики
    if "красив" in q or "стильн" in q: sql += " AND design_score >= ?"; params.append(4)
    if "быстр" in q or "мощн" in q: sql += " AND engine_power >= ?"; params.append(300)
    if "дешев" in q or "недорог" in q or "бюджетн" in q: sql += " AND price <= ?"; params.append(1500000)
    if "дорог" in q or "люкс" in q: sql += " AND price >= ?"; params.append(5000000)
    
    # Семейная
    if "семейн" in q: sql += " AND body_type IN (?, ?, ?)"; params.extend(["внедорожник", "кроссовер", "универсал"])

    # Сортировка
    if sort_by == "price_asc": sql += " ORDER BY price ASC"
    elif sort_by == "power_desc": sql += " ORDER BY engine_power DESC"
    else: sql += " ORDER BY id ASC"

    cursor.execute(sql, params)
    results = cursor.fetchall()
    conn.close()
    return results

@app.route('/')
def home():
    sort = request.args.get('sort', 'default')
    return render_template('index.html', results=search_cars("", sort), searched=False, title="Все автомобили", query="", sort=sort, favorites=session.get('favorites', []))

@app.route('/search', methods=['POST'])
def search_post():
    q = request.form['query'].lower()
    sort = request.form.get('sort', 'default')
    return render_template('index.html', results=search_cars(q, sort), searched=True, title=f"Результаты: {q}", query=q, sort=sort, favorites=session.get('favorites', []))

@app.route('/search', methods=['GET'])
def search_get():
    q = request.args.get('query', '').lower()
    sort = request.args.get('sort', 'default')
    title = f"Результаты: {q}" if q else "Все автомобили"
    return render_template('index.html', results=search_cars(q, sort), searched=bool(q), title=title, query=q, sort=sort, favorites=session.get('favorites', []))

@app.route('/electric')
def electric():
    return render_template('index.html', results=search_cars("электрическая"), searched=False, title="Электромобили", query="электрическая", sort="default", favorites=session.get('favorites', []))

@app.route('/cheap')
def cheap():
    return render_template('index.html', results=search_cars("недорогая"), searched=False, title="Бюджетные авто", query="недорогая", sort="default", favorites=session.get('favorites', []))

@app.route('/favorite/<int:car_id>')
def toggle_favorite(car_id):
    if 'favorites' not in session: session['favorites'] = []
    favorites = session['favorites']
    if car_id in favorites: favorites.remove(car_id)
    else: favorites.append(car_id)
    session['favorites'] = favorites
    return redirect(request.referrer or url_for('home'))

@app.route('/favorites')
def show_favorites():
    if 'favorites' not in session or not session['favorites']:
        return render_template('index.html', results=[], searched=True, title="Избранное", query="", sort="default", favorites=[], message="У вас пока нет избранных машин.")
    conn = create_temp_db()
    placeholders = ','.join('?' for _ in session['favorites'])
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM Cars WHERE id IN ({placeholders})", session['favorites'])
    results = cursor.fetchall()
    conn.close()
    return render_template('index.html', results=results, searched=True, title="Избранное", query="", sort="default", favorites=session['favorites'])

@app.route('/car/<int:car_id>')
def car_details(car_id):
    conn = create_temp_db()
    car = conn.execute("SELECT * FROM Cars WHERE id = ?", (car_id,)).fetchone()
    conn.close()
    if car: return render_template('car.html', car=car)
    return "Машина не найдена", 404

@app.route('/buy/<int:car_id>')
def buy_car(car_id):
    conn = create_temp_db()
    car = conn.execute("SELECT * FROM Cars WHERE id = ?", (car_id,)).fetchone()
    conn.close()
    if car:
        brand_slug = car['brand'].lower().replace(' ', '_')
        model_slug = car['model'].lower().replace(' ', '_')
        if brand_slug == 'mercedes-benz': brand_slug = 'mercedes'
        drom_url = f"https://auto.drom.ru/{brand_slug}/{model_slug}/"
        return render_template('buy.html', car=car, drom_url=drom_url)
    return "Машина не найдена", 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
