# Google Search Console API

Клиент для доступа к Google Search Console: получение статистики (запросы, клики, показы, позиции), управление sitemap, проверка индексации URL.

---

## Развёртывание (с нуля)

### 1. Создать проект в Google Cloud

1. https://console.cloud.google.com/ → **Select project** → **New Project**
2. Название: любое (например `SC API`)

### 2. Включить Search Console API

1. **APIs & Services** → **Library**
2. Найти **"Google Search Console API"** → **Enable**

### 3. Настроить OAuth Consent Screen

1. **APIs & Services** → **OAuth consent screen** (или **Google Auth Platform** → **Branding**)
2. **App name**: любое (например `SC Client`)
3. **User support email**: ваш email
4. **Developer contact**: ваш email
5. **Save**

### 4. Добавить scopes

1. **Scopes** → **Add or Remove Scopes**
2. Выбрать:
   - `https://www.googleapis.com/auth/webmasters` (чтение + запись)
   - или `https://www.googleapis.com/auth/webmasters.readonly` (только чтение)
3. **Update** → **Save and Continue**

### 5. Добавить Test users

1. **Audience** → **Test users** → **+ Add users**
2. Указать Google-email под которым будете авторизоваться (и который имеет доступ к сайтам в Search Console)
3. **Save**

Пока приложение в статусе "Testing" — OAuth работает только для добавленных test users (до 100).

### 6. Создать OAuth Client ID

1. **Credentials** → **+ Create Credentials** → **OAuth client ID**
2. **Application type**: **Desktop app**
3. **Name**: любое (например `SC Desktop`)
4. **Create**

### 7. Скачать JSON

1. В списке **OAuth 2.0 Client IDs** кликнуть на созданный client
2. В разделе **Client secrets** справа от Client secret — иконка **⬇ Download**
3. Сохранить файл как **`client_secret.json`** рядом с `search_console.py`

### 8. Дать доступ к сайтам

Ваш Google-аккаунт должен иметь доступ к сайтам в Search Console (https://search.google.com/search-console).

Рекомендуется **Domain property** — `sc-domain:example.com` — покрывает все поддомены и протоколы одной записью.

---

## Первый запуск

```bash
pip install -r requirements.txt
python3 search_console.py
```

При первом запуске:
1. Откроется браузер с запросом авторизации
2. Войдите под Google-аккаунтом (тем, что добавили в Test users)
3. Нажмите **"Разрешить"**
4. Создастся `token.json` — дальше авторизация автоматически

---

## Использование в коде

```python
from search_console import get_service, list_sites, query_stats

service = get_service()

# Список сайтов
for s in list_sites(service):
    print(s['siteUrl'])

# Статистика по j-flo.ru за последний месяц
result = query_stats(
    service,
    site_url='sc-domain:j-flo.ru',
    start_date='2026-03-18',
    end_date='2026-04-18',
    dimensions=['query', 'page'],
    row_limit=1000,
)

for row in result.get('rows', []):
    print(row['keys'], row['clicks'], row['impressions'], row['position'])
```

### Фильтрация по поддомену

Когда используется Domain property (`sc-domain:`), для получения данных только по одному поддомену:

```python
result = query_stats(
    service,
    site_url='sc-domain:j-flo.ru',
    start_date='2026-04-01',
    end_date='2026-04-18',
    dimensions=['query'],
    filters=[{
        'dimension': 'page',
        'operator': 'contains',
        'expression': 'rostov.j-flo.ru',
    }],
)
```

### Sitemap

```python
from search_console import list_sitemaps, submit_sitemap

# Список
sitemaps = list_sitemaps(service, 'sc-domain:j-flo.ru')

# Отправка
submit_sitemap(service, 'sc-domain:j-flo.ru', 'https://j-flo.ru/sitemap.xml')
```

### Проверка индексации URL

```python
from search_console import inspect_url

result = inspect_url(service, 'sc-domain:j-flo.ru', 'https://rostov.j-flo.ru/tsvety/')
print(result['inspectionResult']['indexStatusResult'])
```

---

## Файлы

| Файл | Описание | В git? |
|------|----------|--------|
| `search_console.py` | Основной клиент | Да |
| `requirements.txt` | Python-зависимости | Да |
| `README.md` | Эта инструкция | Да |
| `client_secret.json` | **Секрет** OAuth | **НЕТ** |
| `token.json` | **Токен** авторизации | **НЕТ** |

Добавьте в `.gitignore`:
```
client_secret.json
token.json
```

---

## Типы объектов в Search Console

| Тип | Формат | Покрытие |
|-----|--------|----------|
| **Domain property** | `sc-domain:example.com` | Все поддомены + протоколы |
| **URL prefix** | `https://example.com/` | Только этот URL prefix |

Используйте Domain property если у вас много поддоменов — одна верификация покрывает все.

---

## Лимиты API

| Операция | Лимит |
|----------|-------|
| Запросы | 1 200 / мин на проект |
| Строк в одном запросе | 25 000 |
| Период статистики | до 16 месяцев назад |
| Обновление данных | задержка 2-3 дня |

---

## Troubleshooting

### "Error 403: access_denied"
Ваш аккаунт не в списке Test users. Добавьте его: **OAuth consent screen** → **Audience** → **Test users**.

### "User has not granted the app X permission"
Удалите `token.json` и запустите скрипт заново — авторизуетесь с нужными scopes.

### Token expired
Скрипт автоматически обновит через refresh_token. Если не работает — удалите `token.json` и повторите авторизацию.
