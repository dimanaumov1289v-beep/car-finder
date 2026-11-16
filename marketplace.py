"""Разделы объявлений Дрома для моделей учебного каталога.

Названия разделов не всегда совпадают с названием модели:
Moskvich → moskvitch, Niva → 2121_4x4_niva, GT-R R35 → gt-r.
Ссылки ведут на подборки, а не на отдельные объявления или оплату.
"""

DROM_PATHS = {
    ('Lada', 'Niva'): 'lada/2121_4x4_niva',
    ('Lada', 'Vesta'): 'lada/vesta',
    ('Lada', 'Granta'): 'lada/granta',
    ('Lada', 'Niva Legend'): 'lada/niva_legend',
    ('UAZ', 'Patriot'): 'uaz/patriot',
    ('GAZ', 'Volga Siber'): 'gaz/volga_siber',
    ('Moskvich', '3'): 'moskvitch/3',
    ('Toyota', 'Camry'): 'toyota/camry',
    ('Toyota', 'Supra'): 'toyota/supra',
    ('Toyota', 'Land Cruiser'): 'toyota/land_cruiser',
    ('Honda', 'Civic Type R'): 'honda/civic_type_r',
    ('Nissan', 'Leaf'): 'nissan/leaf',
    ('Nissan', 'GT-R R35'): 'nissan/gt-r',
    ('BMW', 'M3'): 'bmw/m3',
    ('BMW', 'i4'): 'bmw/i4',
    ('Mercedes-Benz', 'S-Class'): 'mercedes-benz/s-class',
    ('Audi', 'R8'): 'audi/r8',
    ('Porsche', 'Taycan'): 'porsche/taycan',
    ('Porsche', '911'): 'porsche/911',
    ('Volkswagen', 'Polo'): 'volkswagen/polo',
    ('Ferrari', 'Roma'): 'ferrari/roma',
    ('Ford', 'Mustang'): 'ford/mustang',
    ('Tesla', 'Model S'): 'tesla/model_s',
    ('Tesla', 'Model 3'): 'tesla/model_3',
    ('Tesla', 'Model Y'): 'tesla/model_y',
    ('Kia', 'Rio'): 'kia/rio',
    ('Hyundai', 'Solaris'): 'hyundai/solaris',
    ('Hyundai', 'Ioniq 5'): 'hyundai/ioniq_5',
    ('Geely', 'Monjaro'): 'geely/monjaro',
    ('Haval', 'Jolion'): 'haval/jolion',
    ('BYD', 'Han'): 'byd/han',
    ('Zeekr', '001'): 'zeekr/001',
}


def drom_url(car):
    """Вернуть URL подборки модели или None, если модель ещё не сопоставлена."""
    path = DROM_PATHS.get((car['brand'], car['model']))
    return f'https://auto.drom.ru/{path}/' if path else None
