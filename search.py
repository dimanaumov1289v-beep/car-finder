"""Прозрачный поиск по русским правилам без API и нейросетевых сервисов."""
import re
from dataclasses import dataclass, field

BRANDS = {
    'lada': r'лада\w*|ваз|жигули', 'toyota': r'тойот\w*',
    'hyundai': r'х[еёэ]нд[аэ]й?|хундай', 'kia': r'киа', 'bmw': r'бмв',
    'mercedes-benz': r'мерседес\w*|мерс|mercedes', 'audi': r'ауди',
    'porsche': r'порше', 'volkswagen': r'фольксваген\w*|фольц',
    'tesla': r'тесл\w*', 'ford': r'форд\w*', 'nissan': r'ниссан\w*',
    'honda': r'хонд\w*', 'ferrari': r'феррари', 'geely': r'джили',
    'haval': r'хав[аэ]йл?\w*|хавал\w*', 'uaz': r'уаз', 'gaz': r'газ',
    'moskvich': r'москвич\w*', 'byd': r'бид|биуайди', 'zeekr': r'зикр\w*',
}
COUNTRIES = {
    'Россия': r'русск\w*|росси\w*|отечественн\w*',
    'Япония': r'япон\w*', 'Германия': r'немец\w*|герман\w*',
    'Италия': r'итали\w*', 'США': r'америк\w*|сша',
    'Корея': r'коре\w*', 'Китай': r'китай\w*',
}
BODIES = {
    'седан': r'седан\w*', 'купе': r'купе|спорткар\w*',
    'хэтчбек': r'х[еэ]тч\w*', 'кроссовер': r'кроссовер\w*|паркетник\w*',
    'внедорожник': r'внедорожник\w*|джип\w*', 'универсал': r'универсал\w*',
}
SORTS = {'default': 'По соответствию', 'price_asc': 'Сначала дешевле',
         'power_desc': 'Сначала мощнее', 'design_desc': 'По дизайну'}


@dataclass
class SearchPlan:
    filters: dict = field(default_factory=dict)
    labels: list = field(default_factory=list)
    unknown: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    beauty: bool = False
    power: bool = False
    affordable: bool = False


def parse_query(query, cars):
    text = query.lower().replace('ё', 'е').strip()
    plan = SearchPlan()

    def take(pattern):
        nonlocal text
        found = bool(re.search(r'(?<!\w)(?:' + pattern + r')(?!\w)', text))
        text = re.sub(r'(?<!\w)(?:' + pattern + r')(?!\w)', ' ', text)
        return found

    # Не превращаем отрицание в противоположный запрос молча.
    if re.search(r'\b(?:не|кроме|без|исключая)\b', text):
        plan.warnings.append('Отрицания пока не поддерживаются. Укажите нужные свойства без «не», «кроме» и «без».')
        return plan

    # Цена: «до 2 млн», «от 800 тысяч», «от 1 до 2 млн».
    number = r'\d+(?:[.,]\d+)?(?:[ \u00a0]\d{3})*'
    unit = r'(?:млн\.?|миллион\w*|тыс\.?|тысяч\w*|к)'
    money_pattern = r'\b(до|от)\s*(' + number + r')\s*(' + unit + r')?\s*(?:руб\w*\.?|₽)?'
    matches = list(re.finditer(money_pattern, text))
    for idx, match in enumerate(matches):
        direction, value, suffix = match.groups()
        if not suffix and direction == 'от' and idx + 1 < len(matches):
            # В диапазоне единица справа относится к обеим границам.
            following = matches[idx + 1]
            if following.group(1) == 'до' and not text[match.end():following.start()].strip():
                suffix = following.group(3)
        multiplier = 1_000_000 if suffix and suffix.startswith(('млн', 'миллион')) else 1000 if suffix else 1
        amount = float(value.replace(' ', '').replace('\u00a0', '').replace(',', '.')) * multiplier
        key = 'min_price' if direction == 'от' else 'max_price'
        amount = int(amount)
        plan.filters[key] = max(plan.filters.get(key, 0), amount) if key == 'min_price' else min(plan.filters.get(key, amount), amount)
    text = re.sub(money_pattern, ' ', text)
    for key, label in [('min_price', 'Цена от'), ('max_price', 'Цена до')]:
        if key in plan.filters:
            plan.labels.append(f'{label} {plan.filters[key]:,} ₽'.replace(',', ' '))

    for category, mapping in [('brands', BRANDS), ('countries', COUNTRIES), ('bodies', BODIES)]:
        values = []
        for value, pattern in mapping.items():
            if take(pattern + (r'|' + re.escape(value) if category == 'brands' else '')):
                values.append(value)
        if values:
            plan.filters[category] = values
            plan.labels.append(' / '.join(values))

    # Названия моделей поддерживаются вместе с характеристиками и марками.
    models = []
    for model in sorted({car['model'] for car in cars}, key=len, reverse=True):
        if take(re.escape(model.lower())):
            models.append(model)
    if models:
        plan.filters['models'] = models
        plan.labels.append(' / '.join(models))

    if take(r'электро\w*|электрич\w*'):
        plan.filters['fuel'] = 'Электро'
        plan.labels.append('Электромобиль')
    if take(r'бензин\w*'):
        if 'fuel' in plan.filters:
            plan.warnings.append('Укажите один тип двигателя: электрический или бензиновый.')
        plan.filters['fuel'] = 'Бензин'
        plan.labels.append('Бензин')
    if take(r'красив\w*|стильн\w*|модн\w*'):
        plan.beauty = True
        plan.labels.append('Дизайн от 4 из 5')
    if take(r'быстр\w*|мощн\w*|спортив\w*|гонк\w*'):
        plan.power = True
        plan.labels.append('Мощность от 300 л.с.')
    if take(r'дешев\w*|недорог\w*|бюджетн\w*|доступн\w*'):
        plan.affordable = True
        if 'max_price' not in plan.filters:
            plan.filters['max_price'] = 1_500_000
            plan.labels.append('Цена до 1 500 000 ₽')
    if take(r'дорог\w*|люкс\w*|премиум\w*'):
        plan.filters['min_price'] = max(plan.filters.get('min_price', 0), 5_000_000)
        plan.labels.append('Цена от 5 000 000 ₽')
    if take(r'семейн\w*|вместит\w*|больш\w*'):
        plan.filters['family'] = True
        plan.labels.append('Семья: кроссовер / внедорожник / универсал')
    if take(r'город\w*'):
        plan.filters['city'] = True
        plan.labels.append('Город: седан / хэтчбек / кроссовер')
    if take(r'эконом\w*'):
        plan.warnings.append('В каталоге нет расхода топлива: экономичность пока оценить нельзя. Можно указать бюджет, например «до 2 млн».')
    take(r'хочу|нужн\w*|мне|машин\w*|авто\w*|найди|подбери|покажи|пожалуйста|и|или|с|для|по|на')
    plan.unknown = re.findall(r'[\w-]+', text)
    if plan.filters.get('min_price', 0) > plan.filters.get('max_price', float('inf')):
        plan.warnings.append('Нижняя граница цены больше верхней. Измените бюджет.')
    return plan


def select_cars(cars, plan, sort='default'):
    if plan.warnings or plan.unknown:
        return []
    f = plan.filters
    results = []
    for car in cars:
        if f.get('brands') and car['brand'].lower() not in f['brands']: continue
        if f.get('countries') and car['country'] not in f['countries']: continue
        if f.get('bodies') and car['body_type'] not in f['bodies']: continue
        if f.get('models') and car['model'] not in f['models']: continue
        if f.get('fuel') and car['fuel_type'] != f['fuel']: continue
        if car['price'] < f.get('min_price', 0) or car['price'] > f.get('max_price', float('inf')): continue
        if f.get('family') and car['body_type'] not in ('внедорожник', 'кроссовер', 'универсал'): continue
        if f.get('city') and car['body_type'] not in ('седан', 'хэтчбек', 'кроссовер'): continue
        if plan.beauty and car['design_score'] < 4: continue
        if plan.power and car['engine_power'] < 300: continue
        results.append(car)
    if sort == 'price_asc' or (sort == 'default' and plan.affordable):
        return sorted(results, key=lambda c: (c['price'], c['id']))
    if sort == 'power_desc' or (sort == 'default' and plan.power and not plan.beauty):
        return sorted(results, key=lambda c: (-c['engine_power'], c['price']))
    if sort == 'design_desc' or (sort == 'default' and plan.beauty):
        return sorted(results, key=lambda c: (-c['design_score'], -c['votes'], c['price']))
    return sorted(results, key=lambda c: c['id'])
