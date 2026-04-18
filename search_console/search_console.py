"""
Google Search Console API — базовый клиент.

Первый запуск: откроется браузер для OAuth-авторизации → сохранит token.json.
Последующие: авторизация автоматически из token.json (refresh при истечении).

Использование:
    python3 search_console.py

Требования:
    pip install -r requirements.txt
"""
import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(BASE_DIR, 'client_secret.json')
TOKEN_FILE = os.path.join(BASE_DIR, 'token.json')

# https://www.googleapis.com/auth/webmasters — чтение + запись
# https://www.googleapis.com/auth/webmasters.readonly — только чтение
SCOPES = ['https://www.googleapis.com/auth/webmasters']


def get_service():
    """Возвращает авторизованный Search Console API клиент."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(
                    f'Не найден {CREDENTIALS_FILE}. '
                    'Скачайте OAuth credentials из Google Cloud Console.'
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, 'w', encoding='utf-8') as f:
            f.write(creds.to_json())

    return build('searchconsole', 'v1', credentials=creds)


def list_sites(service):
    """Список всех сайтов в Search Console."""
    sites = service.sites().list().execute()
    return sites.get('siteEntry', [])


def query_stats(service, site_url, start_date, end_date, dimensions=None,
                filters=None, row_limit=1000):
    """
    Получить статистику по сайту.

    Параметры:
        site_url: 'sc-domain:j-flo.ru' или 'https://example.com/'
        start_date, end_date: 'YYYY-MM-DD'
        dimensions: список из 'query', 'page', 'country', 'device', 'date'
        filters: список фильтров в формате API
        row_limit: макс. строк (до 25000)
    """
    body = {
        'startDate': start_date,
        'endDate': end_date,
        'dimensions': dimensions or ['query'],
        'rowLimit': row_limit,
    }
    if filters:
        body['dimensionFilterGroups'] = [{'filters': filters}]

    return service.searchanalytics().query(siteUrl=site_url, body=body).execute()


def list_sitemaps(service, site_url):
    """Список sitemap-ов сайта."""
    return service.sitemaps().list(siteUrl=site_url).execute().get('sitemap', [])


def submit_sitemap(service, site_url, sitemap_url):
    """Отправить sitemap на индексацию."""
    return service.sitemaps().submit(siteUrl=site_url, feedpath=sitemap_url).execute()


def inspect_url(service, site_url, target_url):
    """Проверить статус индексации конкретного URL."""
    body = {
        'inspectionUrl': target_url,
        'siteUrl': site_url,
        'languageCode': 'ru',
    }
    return service.urlInspection().index().inspect(body=body).execute()


if __name__ == '__main__':
    service = get_service()

    print('=== Сайты в Search Console ===')
    for s in list_sites(service):
        print(f"  {s['permissionLevel']:20s}  {s['siteUrl']}")
