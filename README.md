# J-flo.Analitycs

Система ежедневной аналитики для `j-flo.ru` и его субдоменов: позиции, клики,
показы, ошибки индексации и рекомендации по SEO. Источники — Google Search
Console и Яндекс Вебмастер. Результат — XLSX-отчёт и краткая сводка в Telegram.

---

## Структура

```
.
├── daily_report.py            — оркестратор (Google + Yandex + XLSX + Telegram)
├── search_console/            — модуль Google Search Console
│   ├── search_console.py      — API-клиент (OAuth Google)
│   ├── google_report.py       — ежедневный Google-отчёт (standalone)
│   ├── submit_sitemaps.py     — массовая отправка sitemap
│   └── subdomains.txt         — список субдоменов проекта
├── yandex_webmaster/          — модуль Яндекс Вебмастера
│   ├── yandex_webmaster.py    — API-клиент (OAuth Яндекс)
│   ├── yandex_data.py         — сбор данных для отчёта
│   ├── authenticate.py        — первичная авторизация OAuth
│   ├── setup_hosts.py         — добавление хостов + META-верификация
│   ├── verify_hosts.py        — перезапуск проверки прав
│   ├── submit_sitemaps.py     — массовая отправка sitemap
│   └── check_chat.py
├── telegram_bot/              — общий модуль отправки в Telegram
│   └── notifier.py
└── reports/                   — сгенерированные отчёты (gitignored)
```

## Установка

```bash
pip install -r search_console/requirements.txt
pip install -r yandex_webmaster/requirements.txt
pip install -r telegram_bot/requirements.txt
```

## Конфигурация

Секреты лежат в `.env`-файлах и JSON-файлах токенов, в git не попадают.

**Корень** — `.env`:
```
ClientID=<Yandex OAuth App Client ID>
ClientSecret=<Yandex OAuth App Client Secret>
RedirectURL=https://oauth.yandex.ru/verification_code
```

**Google Search Console** — `search_console/client_secret.json`
(скачать OAuth credentials из Google Cloud Console → Desktop app).
При первом запуске создаст `token.json`.

**Яндекс Вебмастер/Метрика** — один OAuth-токен:
```bash
cd yandex_webmaster
python authenticate.py --url       # получить URL
# авторизоваться в браузере, получить confirmation code
python authenticate.py <code>      # обмен кода на токен
```
Токен сохранится в `yandex_webmaster/yandex_token.json` (обновляется автоматически).

**Telegram** — `telegram_bot/.env`:
```
TELEGRAM_BOT_TOKEN=<бот от @BotFather>
TELEGRAM_CHAT_ID=<ID группы, см. check_chat.py>
```

## Использование

### Ежедневно (Google)

```bash
python search_console/google_report.py             # за T-3 (учёт лага GSC)
python search_console/google_report.py 2026-04-15  # за конкретную дату
```

Что делает:
- CSV на каждый субдомен в `search_console/reports/daily_report_YYYY-MM-DD_<host>.csv`
- Накапливающий `search_console/keywords.xlsx` (уникальные пары ключ+страница)
- `errors_YYYY-MM-DD.csv` — статус всех sitemap
- `recommendations_YYYY-MM-DD.csv` — рекомендации (low_ctr, page_2, position_drop)
- Telegram: сводка по всем хостам с трафиком, топ-20 запросов, динамика vs вчера

### Раз в 7 дней (Google + Yandex)

```bash
python daily_report.py
```

Что делает дополнительно к Google-отчёту:
- Выгрузка Яндекс Вебмастера за последние 7 дней (по всем подтверждённым хостам)
- Единый XLSX `reports/daily_report_YYYY-MM-DD.xlsx` с 5 листами:
  - **Главный** — сводка обеих систем по хостам
  - **Google** — детальные строки
  - **Yandex** — детальные строки
  - **Ошибки** — sitemap ошибки + Yandex FATAL/CRITICAL
  - **Рекомендации**
- Telegram: две секции (GOOGLE + YANDEX) отдельными сообщениями

## Административные утилиты

```bash
# Google: массовая отправка sitemap всех субдоменов
python search_console/submit_sitemaps.py --dry-run
python search_console/submit_sitemaps.py
python search_console/submit_sitemaps.py --list

# Яндекс: добавить хосты + запросить META-верификацию
python yandex_webmaster/setup_hosts.py --dry-run
python yandex_webmaster/setup_hosts.py
# → yandex_webmaster/reports/meta_tags.csv с кодами для вставки в <head>

# Яндекс: перезапустить проверку после размещения meta
python yandex_webmaster/verify_hosts.py

# Яндекс: массовая отправка sitemap
python yandex_webmaster/submit_sitemaps.py

# Telegram: найти chat_id группы
python telegram_bot/check_chat.py
```

## Лимиты и задержки

| Источник | Лимит / задержка |
|---|---|
| Google Search Console | обновление данных T-3 дня, 1200 req/min |
| Яндекс Вебмастер | `search-queries/popular` — до 7 дней за запрос |
| Яндекс Метрика | данные почти онлайн (~30 мин) |

## Добавление нового субдомена

1. Добавить URL в `search_console/subdomains.txt` (`https://<host>`).
2. `python search_console/submit_sitemaps.py` — зарегистрировать sitemap в Google.
3. `python yandex_webmaster/setup_hosts.py` — добавить в Яндекс + получить meta-код.
4. Разместить `<meta name="yandex-verification" content="..." />` в `<head>` сайта.
5. `python yandex_webmaster/verify_hosts.py` — подтвердить права.
6. `python yandex_webmaster/submit_sitemaps.py` — отправить sitemap в Яндекс.
7. В интерфейсе Яндекс Метрики добавить хост в «Дополнительные адреса» счётчика.
