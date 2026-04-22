"""
Массовая отправка sitemap.xml в Яндекс Вебмастер для всех подтверждённых
j-flo.ru хостов.

Идемпотентно: если sitemap уже добавлен для хоста — пропускаем.

Использование:
    python submit_sitemaps.py --dry-run
    python submit_sitemaps.py
"""
import sys
import time

from yandex_webmaster import (
    get_token, get_user_id, list_hosts,
    list_user_sitemaps, add_sitemap,
)


def extract_host(host_id):
    parts = host_id.split(':')
    return parts[1] if len(parts) >= 2 else host_id


def sitemap_for(host):
    return f'https://{host}/sitemap.xml'


def main():
    dry_run = '--dry-run' in sys.argv
    token = get_token()
    uid = get_user_id(token)

    hosts = list_hosts(token, uid)
    verified = [h for h in hosts if h.get('verified') and 'j-flo.ru' in h['host_id']]
    print(f'Подтверждённых j-flo.ru хостов: {len(verified)}')

    plan = []  # [(host_id, host, sitemap_url, already)]
    for h in verified:
        hid = h['host_id']
        host = extract_host(hid)
        sm_url = sitemap_for(host)
        try:
            existing = list_user_sitemaps(token, uid, hid)
            urls = {s.get('sitemap_url') or s.get('url') for s in existing}
            already = sm_url in urls
        except Exception as e:
            print(f'  WARN list {host}: {str(e)[:120]}')
            already = False
        plan.append((hid, host, sm_url, already))
        time.sleep(0.05)

    need = [p for p in plan if not p[3]]
    print(f'Уже отправлено: {len(plan) - len(need)}')
    print(f'К отправке: {len(need)}')

    if dry_run:
        print('\n--- DRY RUN ---')
        for hid, host, sm, _ in need[:10]:
            print(f'  ADD  {sm}')
        if len(need) > 10:
            print(f'  ... ещё {len(need) - 10}')
        return

    ok, errors = 0, []
    total = len(need)
    for i, (hid, host, sm, _) in enumerate(need, 1):
        try:
            add_sitemap(token, uid, hid, sm)
            print(f'  [{i:3d}/{total}] OK   {sm}')
            ok += 1
        except Exception as e:
            msg = str(e).replace('\n', ' ')[:200]
            print(f'  [{i:3d}/{total}] ERR  {sm} - {msg}')
            errors.append((sm, msg))
        time.sleep(0.1)

    print(f'\nИтог: {ok}/{total} успешно')
    if errors:
        print(f'Ошибок: {len(errors)}')


if __name__ == '__main__':
    main()
