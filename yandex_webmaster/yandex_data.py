"""
Библиотека выгрузки данных из Яндекс.Вебмастера для ежедневного отчёта.

Возвращает структуры, удобные для сборки XLSX и Telegram-сводки.
"""
import html
import time
from datetime import date, timedelta

from yandex_webmaster import (
    get_token, get_user_id, list_hosts,
    get_host_summary, get_popular_queries,
)


PRIORITY_HOSTS = ['j-flo.ru', 'sankt-peterburg.j-flo.ru']
DEFAULT_PERIOD_DAYS = 7
DEFAULT_LAG_DAYS = 3
SLEEP_BETWEEN_CALLS = 0.1


def extract_host(host_id):
    parts = host_id.split(':')
    return parts[1] if len(parts) >= 2 else host_id


def host_sort_key(host):
    if host in PRIORITY_HOSTS:
        return (0, PRIORITY_HOSTS.index(host))
    return (1, host)


def default_date_range():
    """7 дней, заканчивающиеся (сегодня - 3 дня)."""
    end = date.today() - timedelta(days=DEFAULT_LAG_DAYS)
    start = end - timedelta(days=DEFAULT_PERIOD_DAYS - 1)
    return start.isoformat(), end.isoformat()


def _flatten_query(item):
    ind = item.get('indicators', {}) or {}
    shows = int(ind.get('TOTAL_SHOWS') or 0)
    clicks = int(ind.get('TOTAL_CLICKS') or 0)
    show_pos = ind.get('AVG_SHOW_POSITION')
    click_pos = ind.get('AVG_CLICK_POSITION')
    ctr = (clicks / shows) if shows else 0
    return {
        'query': item.get('query_text', ''),
        'clicks': clicks,
        'shows': shows,
        'ctr': ctr,
        'show_position': show_pos,
        'click_position': click_pos,
    }


def fetch_data(date_from=None, date_to=None, verbose=True):
    """
    Возвращает dict:
      {
        'date_from': ..., 'date_to': ...,
        'hosts': [
          {
            'host', 'host_id',
            'summary': {sqi, excluded_pages_count, searchable_pages_count, site_problems},
            'queries': [{query, clicks, shows, ctr, show_position, click_position}]
          }
        ]
      }
    queries пусты если хост без трафика.
    """
    if not date_from or not date_to:
        date_from, date_to = default_date_range()

    token = get_token()
    uid = get_user_id(token)
    all_hosts = list_hosts(token, uid)
    verified = [
        h for h in all_hosts
        if h.get('verified') and 'j-flo.ru' in h['host_id']
    ]
    verified.sort(key=lambda h: host_sort_key(extract_host(h['host_id'])))

    if verbose:
        print(f'Яндекс: период {date_from} .. {date_to}, '
              f'verified j-flo.ru хостов: {len(verified)}')

    hosts_data = []
    for i, h in enumerate(verified, 1):
        hid = h['host_id']
        host = extract_host(hid)
        try:
            summary = get_host_summary(token, uid, hid)
        except Exception as e:
            summary = {'error': str(e)[:200]}
        time.sleep(SLEEP_BETWEEN_CALLS)

        try:
            pq = get_popular_queries(token, uid, hid, date_from, date_to, limit=500)
            queries = [_flatten_query(q) for q in pq.get('queries', [])]
        except Exception as e:
            queries = []
            summary['queries_error'] = str(e)[:200]
        time.sleep(SLEEP_BETWEEN_CALLS)

        if verbose and (queries or summary.get('searchable_pages_count')):
            clicks = sum(q['clicks'] for q in queries)
            shows = sum(q['shows'] for q in queries)
            print(f'  [{i:3d}/{len(verified)}] {host:35s} '
                  f'queries={len(queries):3d} clicks={clicks:4d} shows={shows:5d}')

        hosts_data.append({
            'host': host,
            'host_id': hid,
            'summary': summary,
            'queries': queries,
        })

    return {
        'date_from': date_from,
        'date_to': date_to,
        'hosts': hosts_data,
    }


def aggregate(queries):
    """Итоги по списку запросов."""
    n = len(queries)
    clicks = sum(q['clicks'] for q in queries)
    shows = sum(q['shows'] for q in queries)
    # средняя позиция взвешенная по показам
    weighted_pos = sum(
        (q['show_position'] or 0) * q['shows']
        for q in queries if q['show_position']
    )
    avg_pos = (weighted_pos / shows) if shows else 0
    ctr = (clicks / shows) if shows else 0
    return {
        'queries': n,
        'clicks': clicks,
        'shows': shows,
        'ctr': ctr,
        'position': avg_pos,
    }


def hosts_with_traffic(data):
    """Фильтр: только хосты где clicks>0 и shows>0. С приоритетной сортировкой."""
    out = []
    for h in data['hosts']:
        agg = aggregate(h['queries'])
        if agg['clicks'] > 0 and agg['shows'] > 0:
            out.append((h, agg))
    return out


def build_summary_text(data, top_n=20):
    """Текстовая секция для Telegram: YANDEX + только хосты с clicks>0."""
    df, dt = data['date_from'], data['date_to']
    lines = [
        f'<b>YANDEX Webmaster — {df} .. {dt} (7 дней)</b>',
        '',
    ]
    live = hosts_with_traffic(data)
    if not live:
        lines.append('<i>Нет хостов с кликами и показами за период.</i>')
        return '\n'.join(lines).rstrip()

    for h, agg in live:
        host = html.escape(h['host'])
        lines.append(
            f'📍 <b>{host}</b>\n'
            f'Запросов: <b>{agg["queries"]}</b> · Клики: <b>{agg["clicks"]}</b> · '
            f'Показы: <b>{agg["shows"]}</b> · Поз: <b>{agg["position"]:.2f}</b>'
        )
        top = sorted(h['queries'], key=lambda q: q['clicks'], reverse=True)[:top_n]
        if top:
            lines.append(f'<i>Топ-{len(top)} по кликам:</i>')
            for i, q in enumerate(top, 1):
                pos = q['show_position'] or 0
                q_esc = html.escape(q['query'])
                lines.append(
                    f'  {i}. {q_esc} — {q["clicks"]} кл. / '
                    f'{q["shows"]} пок. / поз. {pos:.1f}'
                )
        lines.append('')

    return '\n'.join(lines).rstrip()
