"""
Первичная авторизация в Яндекс Вебмастер.

Использование:
  python authenticate.py --url         → печатает URL для авторизации
  python authenticate.py <code>        → обменивает код на токен
"""
import sys

from yandex_webmaster import authorize_url, exchange_code


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    arg = sys.argv[1]
    if arg == '--url':
        print('Откройте в браузере и авторизуйтесь:')
        print(authorize_url())
        print('\nПосле подтверждения Яндекс покажет confirmation code.')
        print('Запустите: python authenticate.py <code>')
        return
    data = exchange_code(arg)
    print('OK. Токен сохранён.')
    print(f'expires_in: {data.get("expires_in")} сек')
    print(f'refresh_token: {"есть" if data.get("refresh_token") else "нет"}')


if __name__ == '__main__':
    main()
