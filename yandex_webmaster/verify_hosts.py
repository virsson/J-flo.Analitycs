"""
Перезапуск META_TAG верификации для всех неподтверждённых j-flo.ru хостов.

Использование (после размещения meta-тегов):
    python verify_hosts.py
"""
import time

from yandex_webmaster import (
    get_token, get_user_id, list_hosts,
    request_verification, get_verification,
)


def extract_host(host_id):
    parts = host_id.split(':')
    return parts[1] if len(parts) >= 2 else host_id


def main():
    token = get_token()
    uid = get_user_id(token)
    hosts = list_hosts(token, uid)

    pending = [
        h['host_id'] for h in hosts
        if not h.get('verified') and 'j-flo.ru' in h['host_id']
    ]
    if not pending:
        print('Нет неподтверждённых j-flo.ru хостов.')
        return

    print(f'К повторной проверке: {len(pending)} хостов')

    results = {'VERIFIED': 0, 'IN_PROGRESS': 0, 'FAILED': 0, 'OTHER': 0}
    for i, hid in enumerate(pending, 1):
        host = extract_host(hid)
        try:
            request_verification(token, uid, hid, 'META_TAG')
        except Exception:
            pass  # уже идёт — не критично
        time.sleep(0.2)
        try:
            v = get_verification(token, uid, hid)
            state = v.get('verification_state', 'OTHER')
            fail = v.get('fail_info') or {}
            reason = fail.get('reason', '')
            print(f'  [{i:2d}/{len(pending)}] {state:22s} {host}'
                  + (f'  ({reason})' if reason else ''))
            key = 'FAILED' if 'FAIL' in state else (
                'VERIFIED' if state == 'VERIFIED' else
                'IN_PROGRESS' if 'PROGRESS' in state else 'OTHER'
            )
            results[key] += 1
        except Exception as e:
            print(f'  [{i:2d}/{len(pending)}] ERR  {host} - {e}')
            results['OTHER'] += 1

    print()
    print(f'Итог: VERIFIED={results["VERIFIED"]}  IN_PROGRESS={results["IN_PROGRESS"]}  '
          f'FAILED={results["FAILED"]}  OTHER={results["OTHER"]}')


if __name__ == '__main__':
    main()
