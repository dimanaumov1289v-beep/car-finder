"""Регрессии поиска, рейтинга, избранного и HTTP-форм."""
import re
from contextlib import closing
import tempfile
import unittest
from pathlib import Path

from main import create_app
from search import parse_query, select_cars
import json

CARS = json.loads((Path(__file__).resolve().parents[1] / 'data/cars.json').read_text())
CARS = [dict(c, design_score=c['demo_design_score'], votes=0) for c in CARS]


class SearchTests(unittest.TestCase):
    def search(self, query, sort='default'):
        plan = parse_query(query, CARS)
        return select_cars(CARS, plan, sort)

    def test_affordable_is_not_expensive(self):
        cars = self.search('недорогая машина')
        self.assertTrue(cars)
        self.assertTrue(all(c['price'] <= 1_500_000 for c in cars))
        self.assertEqual([c['price'] for c in cars], sorted(c['price'] for c in cars))

    def test_brand_and_beauty_together(self):
        cars = self.search('красивая Toyota')
        self.assertTrue(cars)
        self.assertTrue(all(c['brand'] == 'Toyota' and c['design_score'] >= 4 for c in cars))

    def test_brand_is_word_not_substring(self):
        plan = parse_query('мне нужна недорогая машина', CARS)
        self.assertNotIn('brands', plan.filters)  # «газ» не извлекается из других слов
        self.assertTrue(select_cars(CARS, plan))

    def test_budget_not_ignored(self):
        cars = self.search('кроссовер до 3 млн')
        self.assertTrue(cars)
        self.assertTrue(all(c['body_type'] == 'кроссовер' and c['price'] <= 3_000_000 for c in cars))

    def test_money_formats_and_shared_unit(self):
        for query in ['от 1 до 2 млн', 'от 1 млн до 2 млн', 'от 1 000 000 до 2 000 000 рублей']:
            with self.subTest(query=query):
                p = parse_query(query, CARS)
                self.assertEqual(p.filters['min_price'], 1_000_000)
                self.assertEqual(p.filters['max_price'], 2_000_000)
                self.assertTrue(select_cars(CARS, p))
        self.assertEqual(parse_query('до 1,5 миллиона', CARS).filters['max_price'], 1_500_000)
        self.assertEqual(parse_query('до 800 тысяч', CARS).filters['max_price'], 800_000)

    def test_models_and_cyrillic_brand(self):
        self.assertEqual([c['model'] for c in self.search('Тойота Camry')], ['Camry'])
        self.assertEqual([c['model'] for c in self.search('красивый Nissan GT-R R35')], ['GT-R R35'])

    def test_multiple_countries_or_brands(self):
        cars = self.search('Toyota или Honda')
        self.assertEqual({c['brand'] for c in cars}, {'Toyota', 'Honda'})
        self.assertEqual({c['country'] for c in self.search('японская или немецкая')}, {'Япония', 'Германия'})

    def test_unknown_and_negation_do_not_return_random_catalogue(self):
        for query in ['абракадабра', 'не электрическая', 'красивая Mazda', 'экономичная', 'без бензина']:
            with self.subTest(query=query):
                self.assertEqual(self.search(query), [])

    def test_beauty_ranked_by_score(self):
        scores = [c['design_score'] for c in self.search('красивая')]
        self.assertTrue(scores)
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_contradictory_budget(self):
        self.assertEqual(self.search('от 5 млн до 2 млн'), [])

    def test_power_and_fuel(self):
        cars = self.search('мощная немецкая электрическая машина')
        self.assertTrue(cars)
        self.assertTrue(all(c['engine_power'] >= 300 and c['country'] == 'Германия' and c['fuel_type'] == 'Электро' for c in cars))


class AppTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.database = str(Path(self.tmp.name) / 'test.sqlite3')
        self.config = {'TESTING': True, 'DATABASE': self.database, 'SECRET_KEY': 'test-only-secret'}
        self.app = create_app(self.config)
        self.client = self.app.test_client()
        self.client.get('/')
        with self.client.session_transaction() as s:
            self.csrf = s['csrf']

    def tearDown(self):
        self.tmp.cleanup()

    def post(self, path, **fields):
        return self.client.post(path, data=dict(csrf_token=self.csrf, **fields))

    def test_pages_render_and_health(self):
        for path in ['/', '/search?query=красивая+Toyota', '/favorites', '/car/1', '/about', '/electric', '/cheap', '/health']:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path, follow_redirects=True).status_code, 200)
        self.assertEqual(self.client.get('/health').json, {'status': 'ok'})

    def test_sort_preserves_query_and_favorites_scope(self):
        html = self.client.get('/search?query=красивая&sort=price_asc').get_data(as_text=True)
        self.assertIn('name="query" value="красивая"', html)
        self.assertIn('value="price_asc" selected', html)
        self.post('/favorite/8')
        html = self.client.get('/favorites?sort=price_asc').get_data(as_text=True)
        self.assertIn('action="/favorites"', html)
        self.assertIn('Camry', html)
        self.assertNotIn('<h3>Roma</h3>', html)

    def test_favorites_toggle_and_csrf(self):
        self.assertEqual(self.client.get('/favorite/1').status_code, 405)
        self.assertEqual(self.client.post('/favorite/1').status_code, 400)
        self.assertEqual(self.post('/favorite/1').status_code, 303)
        with self.client.session_transaction() as s:
            self.assertEqual(s['favorites'], [1])
        self.post('/favorite/1')
        with self.client.session_transaction() as s:
            self.assertEqual(s['favorites'], [])
        self.assertEqual(self.post('/favorite/999').status_code, 404)

    def test_no_open_redirect(self):
        for target in ['//[', 'https://evil.example', '//evil.example', '/\\evil.example', '/\nevil.example']:
            with self.subTest(target=target):
                response = self.post('/favorite/1', next=target)
                self.assertNotIn('evil.example', response.location)
        self.assertEqual(self.post('/favorite/1', next='/favorites?sort=price_asc').location, '/favorites?sort=price_asc')

    def test_rating_replace_aggregate_and_persistence(self):
        self.assertEqual(self.post('/rate/1', score='5').status_code, 303)
        self.post('/rate/1', score='3')
        second = self.app.test_client()
        second.get('/')
        with second.session_transaction() as s:
            token = s['csrf']
        second.post('/rate/1', data={'csrf_token': token, 'score': '5'})
        import sqlite3
        with closing(sqlite3.connect(self.database)) as conn:
            count, average = conn.execute('SELECT COUNT(*),AVG(score) FROM ratings WHERE car_id=1').fetchone()
        self.assertEqual((count, average), (2, 4.0))
        restarted = create_app(self.config).test_client()
        html = restarted.get('/car/1').get_data(as_text=True)
        self.assertIn('4.0', html)
        self.assertIn('Количество оценок: 2', html)
        self.assertIn('Niva', restarted.get('/?query=красивая').get_data(as_text=True))

    def test_rating_validation(self):
        for value in ['', '0', '6', '1.5', 'abc']:
            self.assertEqual(self.post('/rate/1', score=value).status_code, 400)
        self.assertEqual(self.post('/rate/999', score='5').status_code, 404)

    def test_validation_and_escaping(self):
        self.assertEqual(self.client.get('/?query=' + 'a' * 301).status_code, 400)
        response = self.client.get('/?query=<script>alert(1)</script>')
        self.assertNotIn('<script>', response.get_data(as_text=True))
        self.assertIn("default-src 'self'", response.headers['Content-Security-Policy'])
        self.assertEqual(self.client.get('/car/999').status_code, 404)
        self.assertEqual(self.client.get('/?sort=invalid').status_code, 200)

    def test_buy_redirects_for_all_models(self):
        from urllib.parse import urlsplit
        from marketplace import DROM_PATHS
        self.assertEqual(set(DROM_PATHS), {(c['brand'], c['model']) for c in CARS})
        for car in CARS:
            response = self.client.get(f"/buy/{car['id']}")
            self.assertEqual(response.status_code, 302)
            parts = urlsplit(response.location)
            self.assertEqual((parts.scheme, parts.netloc), ('https', 'auto.drom.ru'))
            self.assertFalse(parts.query or parts.fragment)
        for car_id, expected in [(1, 'lada/2121_4x4_niva'), (7, 'moskvitch/3'),
                                 (8, 'toyota/camry'), (13, 'nissan/gt-r'),
                                 (16, 'mercedes-benz/s-class')]:
            self.assertEqual(self.client.get(f'/buy/{car_id}').location,
                             f'https://auto.drom.ru/{expected}/')
        self.assertEqual(self.client.get('/buy/999').status_code, 404)

    def test_buy_buttons_on_catalogue_details_and_favorites(self):
        from html.parser import HTMLParser
        class Links(HTMLParser):
            def __init__(self):
                super().__init__()
                self.links = []
            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag == 'a' and attrs.get('href', '').startswith('/buy/'):
                    self.links.append(attrs)
        self.post('/favorite/8')
        for page, count in [('/', 32), ('/car/8', 1), ('/favorites', 1)]:
            parser = Links()
            parser.feed(self.client.get(page).get_data(as_text=True))
            self.assertEqual(len(parser.links), count)
            for link in parser.links:
                self.assertEqual(link['target'], '_blank')
                self.assertIn('noopener', link['rel'])
                self.assertIn('Дроме', link['aria-label'])

    def test_forms_have_no_external_assets(self):
        html = self.client.get('/').get_data(as_text=True)
        self.assertFalse(re.search(r'(?:src|href)="https?://', html))


if __name__ == '__main__':
    unittest.main()
