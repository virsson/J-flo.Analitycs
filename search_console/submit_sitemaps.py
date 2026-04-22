"""
Массовая отправка sitemap-ов субдоменов j-flo.ru в Google Search Console.

Читает список базовых URL из subdomains.txt (по одному в строке, комментарии
начинаются с #). Для каждого отправляет <base>/sitemap.xml через Search
Console API в Domain property sc-domain:j-flo.ru.

Флаги:
    --dry-run    только показать что будет отправлено
    --list       показать текущие зарегистрированные sitemap-ы и выйти

Использование:
    python submit_sitemaps.py --dry-run
    python submit_sitemaps.py
    python submit_sitemaps.py --list
"""
import os
import sys
import time

from search_console import get_service, list_sitemaps, submit_sitemap


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SUBDOMAINS_FILE = os.path.join(BASE_DIR, 'subdomains.txt')
SITE_URL = 'sc-domain:j-flo.ru'
SITEMAP_PATH = '/sitemap.xml'
SLEEP_BETWEEN = 0.1


def read_subdomains(path):
    urls = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                urls.append(line.rstrip('/'))
    return urls


def cmd_list(service):
    items = list_sitemaps(service, SITE_URL)
    print(f'Зарегистрировано sitemap-ов: {len(items)}')
    for s in items:
        print(f'  {s.get("path")}  (last: {s.get("lastSubmitted", "?")})')


def cmd_submit(service, dry_run=False):
    subdomains = read_subdomains(SUBDOMAINS_FILE)
    total = len(subdomains)
    print(f'К отправке: {total} sitemap-ов (Domain property: {SITE_URL})')
    if dry_run:
        print('--- DRY RUN ---')
        for i, base in enumerate(subdomains, 1):
            print(f'  [{i:3d}/{total}] {base}{SITEMAP_PATH}')
        return

    ok = 0
    errors = []
    for i, base in enumerate(subdomains, 1):
        sitemap_url = base + SITEMAP_PATH
        try:
            submit_sitemap(service, SITE_URL, sitemap_url)
            print(f'  [{i:3d}/{total}] OK   {sitemap_url}')
            ok += 1
        except Exception as e:
            msg = str(e).replace('\n', ' ')[:200]
            print(f'  [{i:3d}/{total}] ERR  {sitemap_url} - {msg}')
            errors.append((sitemap_url, msg))
        time.sleep(SLEEP_BETWEEN)

    print(f'\nИтог: {ok}/{total} успешно')
    if errors:
        print(f'Ошибок: {len(errors)}')


def main():
    args = sys.argv[1:]
    service = get_service()
    if '--list' in args:
        cmd_list(service)
    else:
        cmd_submit(service, dry_run='--dry-run' in args)


if __name__ == '__main__':
    main()
