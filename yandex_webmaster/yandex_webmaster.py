"""
Клиент Яндекс Вебмастер API v4.

Авторизация — OAuth OOB (RedirectURL=https://oauth.yandex.ru/verification_code):
  1. Откройте в браузере: python authenticate.py --url
  2. Авторизуйтесь, скопируйте код (confirmation code) со страницы Яндекса.
  3. Обменяйте: python authenticate.py <code>
     Токен сохранится в yandex_token.json (refresh при истечении — автоматически).

Использование в коде:
    from yandex_webmaster import get_token, get_user_id, list_hosts, api_get

    token = get_token()
    uid = get_user_id(token)
    hosts = list_hosts(token, uid)
"""
import json
import os
import time

import requests
from dotenv import load_dotenv


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
load_dotenv(os.path.join(ROOT_DIR, '.env'))

CLIENT_ID = os.getenv('ClientID')
CLIENT_SECRET = os.getenv('ClientSecret')
REDIRECT_URL = os.getenv('RedirectURL', 'https://oauth.yandex.ru/verification_code')

TOKEN_FILE = os.path.join(BASE_DIR, 'yandex_token.json')
API_BASE = 'https://api.webmaster.yandex.net/v4'
OAUTH_TOKEN_URL = 'https://oauth.yandex.ru/token'
OAUTH_AUTHORIZE_URL = 'https://oauth.yandex.ru/authorize'


def authorize_url():
    """URL для открытия в браузере — получить confirmation code."""
    return (
        f'{OAUTH_AUTHORIZE_URL}'
        f'?response_type=code'
        f'&client_id={CLIENT_ID}'
        f'&redirect_uri={REDIRECT_URL}'
    )


def exchange_code(code):
    """Меняет confirmation code на access_token + refresh_token, сохраняет."""
    resp = requests.post(OAUTH_TOKEN_URL, data={
        'grant_type': 'authorization_code',
        'code': code,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
    }, timeout=15)
    if not resp.ok:
        raise RuntimeError(f'OAuth {resp.status_code}: {resp.text}')
    data = resp.json()
    data['obtained_at'] = int(time.time())
    _save_token(data)
    return data


def refresh_token(refresh_t):
    """Обновляет access_token по refresh_token."""
    resp = requests.post(OAUTH_TOKEN_URL, data={
        'grant_type': 'refresh_token',
        'refresh_token': refresh_t,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
    }, timeout=15)
    if not resp.ok:
        raise RuntimeError(f'OAuth refresh {resp.status_code}: {resp.text}')
    data = resp.json()
    data['obtained_at'] = int(time.time())
    _save_token(data)
    return data


def _save_token(data):
    with open(TOKEN_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _load_token():
    if not os.path.exists(TOKEN_FILE):
        return None
    with open(TOKEN_FILE, encoding='utf-8') as f:
        return json.load(f)


def get_token():
    """
    Возвращает валидный access_token. Если истекает — автообновление через
    refresh_token. Если токена нет — FileNotFoundError с инструкцией.
    """
    data = _load_token()
    if not data:
        raise FileNotFoundError(
            f'Нет {TOKEN_FILE}. Запустите authenticate.py для авторизации.'
        )
    expires_at = data.get('obtained_at', 0) + data.get('expires_in', 0)
    # обновляем заранее, за 1 день до истечения
    if time.time() > expires_at - 86400 and data.get('refresh_token'):
        data = refresh_token(data['refresh_token'])
    return data['access_token']


def api_get(token, path, params=None):
    """GET запрос к Webmaster API v4."""
    url = API_BASE + path
    resp = requests.get(
        url,
        headers={'Authorization': f'OAuth {token}'},
        params=params,
        timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(f'API {resp.status_code} {path}: {resp.text}')
    return resp.json()


def api_post(token, path, params=None, json_body=None):
    """Webmaster API требует Content-Type: application/json — шлём {} по умолчанию."""
    url = API_BASE + path
    resp = requests.post(
        url,
        headers={'Authorization': f'OAuth {token}'},
        params=params,
        json=json_body if json_body is not None else {},
        timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(f'API {resp.status_code} {path}: {resp.text}')
    return resp.json() if resp.content else {}


def api_delete(token, path):
    url = API_BASE + path
    resp = requests.delete(
        url,
        headers={'Authorization': f'OAuth {token}'},
        timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(f'API {resp.status_code} {path}: {resp.text}')
    return resp.json() if resp.content else {}


def delete_host(token, user_id, host_id):
    return api_delete(token, f'/user/{user_id}/hosts/{host_id}')


def get_user_id(token):
    return api_get(token, '/user')['user_id']


def list_hosts(token, user_id):
    return api_get(token, f'/user/{user_id}/hosts').get('hosts', [])


def add_host(token, user_id, host_url):
    """Добавляет хост. Возвращает dict с host_id."""
    return api_post(
        token,
        f'/user/{user_id}/hosts/',
        json_body={'host_url': host_url},
    )


def request_verification(token, user_id, host_id, verification_type='META_TAG'):
    """Инициирует проверку прав выбранным методом."""
    return api_post(
        token,
        f'/user/{user_id}/hosts/{host_id}/verification/',
        params={'verification_type': verification_type},
    )


def get_verification(token, user_id, host_id):
    """Текущий статус + код для META_TAG (yandex-verification)."""
    return api_get(token, f'/user/{user_id}/hosts/{host_id}/verification/')


def list_user_sitemaps(token, user_id, host_id):
    """Sitemap-ы, добавленные пользователем (не обнаруженные Яндексом сами)."""
    data = api_get(token, f'/user/{user_id}/hosts/{host_id}/user-added-sitemaps/')
    return data.get('sitemaps', [])


def add_sitemap(token, user_id, host_id, sitemap_url):
    """Добавляет sitemap вручную. Возвращает dict с sitemap_id."""
    return api_post(
        token,
        f'/user/{user_id}/hosts/{host_id}/user-added-sitemaps/',
        json_body={'url': sitemap_url},
    )


def get_host_summary(token, user_id, host_id):
    """Сводка по хосту: indexing, sqi, проблемы, searchable."""
    return api_get(token, f'/user/{user_id}/hosts/{host_id}/summary')


def get_popular_queries(token, user_id, host_id, date_from, date_to, limit=500):
    """
    Популярные поисковые запросы за диапазон.
    date_from, date_to: YYYY-MM-DD. Максимум период 7 дней.
    Возвращает dict с ключом 'queries' — список [{query_text, indicators:{...}}].
    """
    params = [
        ('date_from', date_from),
        ('date_to', date_to),
        ('order_by', 'TOTAL_CLICKS'),
        ('query_indicator', 'TOTAL_CLICKS'),
        ('query_indicator', 'TOTAL_SHOWS'),
        ('query_indicator', 'AVG_SHOW_POSITION'),
        ('query_indicator', 'AVG_CLICK_POSITION'),
        ('limit', str(limit)),
    ]
    return api_get(
        token,
        f'/user/{user_id}/hosts/{host_id}/search-queries/popular/',
        params=params,
    )


if __name__ == '__main__':
    # Самопроверка: напечатать список доступных хостов.
    token = get_token()
    uid = get_user_id(token)
    print(f'user_id: {uid}')
    hosts = list_hosts(token, uid)
    print(f'Всего хостов: {len(hosts)}')
    for h in hosts:
        print(f"  {h.get('host_id', ''):40s}  verified={h.get('verified', '?')}")
