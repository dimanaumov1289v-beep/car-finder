from flask import Flask, render_template, request, session, redirect, url_for
import sqlite3
import os
if os.path.exists('cars.db'):
    os.remove('cars.db')

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_school_project'

def get_db():
    conn = sqlite3.connect('cars.db')
    conn.row_factory = sqlite3.Row
    return conn

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # ПРИНУДИТЕЛЬНО УДАЛЯЕМ СТАРУЮ ТАБЛИЦУ И СОЗДАЕМ НОВУЮ
    cursor.execute("DROP TABLE IF EXISTS Cars")
    cursor.execute('''CREATE TABLE Cars (
        id INTEGER PRIMARY KEY AUTOINCREMENT, brand TEXT, model TEXT, country TEXT, 
        body_type TEXT, engine_power INTEGER, engine_volume REAL, design_score INTEGER, price INTEGER, fuel_type TEXT)''')
    
    # ЗАЛИВАЕМ МАШИНЫ
    cars = [
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
    cursor.executemany('''INSERT INTO Cars (brand, model, country, body_type, engine_power, engine_volume, design_score, price, fuel_type) 
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', cars)
    conn.commit()
    conn.close()

# ВЫЗЫВАЕМ ИНИЦИАЛИЗАЦИЮ ПРИ СТАРТЕ
init_db()

# --- ЛОГИКА ПОИСКА ---
def search_cars(q, sort_by="default"):
    q = q.lower()
    brand_translations = {
        "лада": "lada", "ваз": "lada", "жигули": "lada", "тойота": "toyota", "хендай": "hyundai", 
        "хендэ": "hyundai", "киа": "kia", "бмв": "bmw", "мерседес": "mercedes", "мерс": "mercedes", 
        "ауди": "audi", "порше": "porsche", "фольксваген": "volkswagen", "фольц": "volkswagen", 
        "тесла": "tesla", "форд": "ford", "шевроле": "chevrolet", "ниссан": "nissan", "хонда": "honda", 
        "мазда": "mazda", "субару": "subaru", "лексус": "lexus", "феррари": "ferrari", 
        "ламборгини": "lamborghini", "ламбо": "lamborghini", "альфа": "alfa", "джили": "geely", 
        "чери": "chery", "хавал": "haval", "эксид": "exeed", "омода": "omoda", "танк": "tank", 
        "уаз": "uaz", "газ": "gaz", "москвич": "moskvich"
    }
    for rus, eng in brand_translations.items():
        if rus in q: q = q.replace(rus, eng)

    conn = get_db()
    cursor = conn.cursor()
    sql = "SELECT * FROM Cars WHERE 1=1"
    params = []
    
    if q: 
        sql += " AND (brand LIKE ? OR model LIKE ?)"
        params.append(f"%{q}%"); params.append(f"%{q}%")
    
    if any(x in q for x in ["русск", "советск", "российск"]): sql += " AND country = ?"; params.append("Россия")
    if any(x in q for x in ["япон", "тойот", "ниссан"]): sql += " AND country = ?"; params.append("Япония")
    if any(x in q for x in ["немец", "герман", "бмв", "мерсед", "ауди"]): sql += " AND country = ?"; params.append("Германия")
    if any(x in q for x in ["итальян", "феррари", "ламбо"]): sql += " AND country = ?"; params.append("Италия")
    if any(x in q for x in ["америк", "сша", "тесла", "форд"]): sql += " AND country = ?"; params.append("США")
    if any(x in q for x in ["коре", "киа", "хендай"]): sql += " AND country = ?"; params.append("Корея")
    if any(x in q for x in ["китай", "джили", "чери", "хавал"]): sql += " AND country = ?"; params.append("Китай")
    
    if any(x in q for x in ["электро", "электрич", "аккумулятор"]): sql += " AND fuel_type = ?"; params.append("Электро")
    if "бензин" in q: sql += " AND fuel_type = ?"; params.append("Бензин")
    
    if any(x in q for x in ["внедорожник", "джип"]): sql += " AND body_type = ?"; params.append("внедорожник")
    if "седан" in q: sql += " AND body_type = ?"; params.append("седан")
    if any(x in q for x in ["купе", "спорткар"]): sql += " AND body_type = ?"; params.append("купе")
    if any(x in q for x in ["хэтчбек", "хетч"]): sql += " AND body_type = ?"; params.append("хэтчбек")
    if any(x in q for x in ["кроссовер", "паркетник"]): sql += " AND body_type = ?"; params.append("кроссовер")

    if any(x in q for x in ["красив", "стильн", "модн"]): sql += " AND design_score >= ?"; params.append(4)
    if any(x in q for x in ["быстр", "мощн", "крут", "гонк"]): sql += " AND engine_power >= ?"; params.append(300)
    
    if any(x in q for x in ["дешев", "бюджетн", "недорог", "эконом", "доступн", "недоро"]): 
        sql += " AND price <= ?"; params.append(1500000)
    elif any(x in q for x in ["дорог", "люкс", "премиум"]) and "не" not in q: 
        sql += " AND price >= ?"; params.append(5000000)
    
    if any(x in q for x in ["семейн", "больш", "вместит"]): 
        sql += " AND body_type IN (?, ?, ?)"; params.extend(["внедорожник", "кроссовер", "универсал"])

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
    sort = request.args.get('sort', 'default')
    return render_template('index.html', results=search_cars("электрическая", sort), searched=False, title="Электромобили", query="электрическая", sort=sort, favorites=session.get('favorites', []))

@app.route('/cheap')
def cheap():
    sort = request.args.get('sort', 'default')
    return render_template('index.html', results=search_cars("недорогая", sort), searched=False, title="Бюджетные авто", query="недорогая", sort=sort, favorites=session.get('favorites', []))

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
    conn = get_db()
    placeholders = ','.join('?' for _ in session['favorites'])
    query = f"SELECT * FROM Cars WHERE id IN ({placeholders})"
    cursor = conn.cursor()
    cursor.execute(query, session['favorites'])
    results = cursor.fetchall()
    conn.close()
    return render_template('index.html', results=results, searched=True, title="Избранное", query="", sort="default", favorites=session['favorites'])

@app.route('/car/<int:car_id>')
def car_details(car_id):
    conn = get_db()
    car = conn.execute("SELECT * FROM Cars WHERE id = ?", (car_id,)).fetchone()
    conn.close()
    if car: return render_template('car.html', car=car)
    return "Машина не найдена", 404

@app.route('/buy/<int:car_id>')
def buy_car(car_id):
    conn = get_db()
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
