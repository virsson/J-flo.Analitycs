"""
Добавление недостающих субдоменов в Яндекс Вебмастер и инициация
META_TAG верификации.

Что делает:
  1. Сверяет ../search_console/subdomains.txt с текущим списком хостов
     в Вебмастере.
  2. Добавляет недостающие через API (POST /hosts/).
  3. Для добавленных + для уже существующих, но НЕ подтверждённых,
     инициирует META_TAG верификацию (получает verification_uin).
  4. Сохраняет reports/meta_tags.csv с маппингом host -> content.

Использование:
  python setup_hosts.py --dry-run   # показать план
  python setup_hosts.py             # применить
"""
import csv
import os
import sys
import time

from yandex_webmaster import (
    get_token, get_user_id, list_hosts,
    add_host, request_verification, get_verification,
)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
SUBDOMAINS_FILE = os.path.join(ROOT_DIR, 'search_console', 'subdomains.txt')
REPORTS_DIR = os.path.join(BASE_DIR, 'reports')
META_CSV = os.path.join(REPORTS_DIR, 'meta_tags.csv')


def extract_host(host_id):
    parts = host_id.split(':')
    return parts[1] if len(parts) >= 2 else host_id


def load_targets():
    targets = []
    with open(SUBDOMAINS_FILE, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                targets.append(line.rstrip('/'))
    return targets  # как URL https://...


def main():
    dry_run = '--dry-run' in sys.argv

    token = get_token()
    uid = get_user_id(token)
    existing = list_hosts(token, uid)

    by_host = {extract_host(h['host_id']): h for h in existing}
    targets = load_targets()

    to_add = []          # [url]
    to_verify = []       # [host_id]
    already_ok = 0

    for url in targets:
        host = url.replace('https://', '').replace('http://', '')
        if host in by_host:
            h = by_host[host]
            if h.get('verified'):
                already_ok += 1
            else:
                to_verify.append(h['host_id'])
        else:
            to_add.append(url)

    print(f'Целевых: {len(targets)}')
    print(f'Уже подтверждено: {already_ok}')
    print(f'К добавлению: {len(to_add)}')
    print(f'К запросу верификации (существующие неподтв.): {len(to_verify)}')

    if dry_run:
        print('\n--- DRY RUN ---')
        for u in to_add[:5]:
            print(f'  ADD  {u}')
        if len(to_add) > 5:
            print(f'  ... ещё {len(to_add) - 5}')
        for hid in to_verify:
            print(f'  VERIFY  {hid}')
        return

    os.makedirs(REPORTS_DIR, exist_ok=True)
    results = []

    # 1. Добавляем хосты
    added_host_ids = []
    for i, url in enumerate(to_add, 1):
        try:
            r = add_host(token, uid, url)
            hid = r.get('host_id')
            added_host_ids.append(hid)
            print(f'  ADD [{i:2d}/{len(to_add)}] OK   {url} -> {hid}')
        except Exception as e:
            msg = str(e).replace('\n', ' ')[:200]
            print(f'  ADD [{i:2d}/{len(to_add)}] ERR  {url} - {msg}')
        time.sleep(0.15)

    # 2. Запрашиваем META_TAG верификацию для всех подлежащих
    verify_list = added_host_ids + to_verify
    print(f'\nЗапрос META_TAG для {len(verify_list)} хостов:')
    for i, hid in enumerate(verify_list, 1):
        try:
            request_verification(token, uid, hid, 'META_TAG')
        except Exception as e:
            # 'already pending' — не страшно, просто получим uin ниже
            pass
        try:
            v = get_verification(token, uid, hid)
            uin = v.get('verification_uin', '')
            state = v.get('verification_state', '')
            host = extract_host(hid)
            results.append({'host': host, 'host_id': hid, 'uin': uin, 'state': state})
            print(f'  [{i:2d}/{len(verify_list)}] {state:25s} {host}  uin={uin}')
        except Exception as e:
            msg = str(e).replace('\n', ' ')[:200]
            print(f'  [{i:2d}/{len(verify_list)}] ERR  {hid} - {msg}')
        time.sleep(0.15)

    # 3. CSV с маппингом
    with open(META_CSV, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['host', 'meta_content', 'verification_state', 'meta_tag'])
        for r in results:
            meta = f'<meta name="yandex-verification" content="{r["uin"]}" />'
            w.writerow([r['host'], r['uin'], r['state'], meta])

    print(f'\nCSV: {META_CSV}')
    print(f'После размещения meta на страницах запустите:')
    print(f'  python verify_hosts.py')


if __name__ == '__main__':
    main()
