"""
Отправка сообщений в Telegram-группу.

Используется общим модулем для всех источников аналитики (Google Search
Console, Яндекс.Метрика и т.д.). Каждый источник формирует текстовую
секцию, а `send_report` склеивает их разделителем и шлёт одним сообщением.

Конфиг в .env рядом с модулем:
    TELEGRAM_BOT_TOKEN=...
    TELEGRAM_CHAT_ID=...
"""
import os

import requests
from dotenv import load_dotenv


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

TG_MAX_LEN = 4096
SAFE_LEN = 3800  # запас под HTML-теги и хвост


def _send_raw(text):
    if not BOT_TOKEN or not CHAT_ID:
        raise RuntimeError(
            'Не заданы TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID в .env'
        )
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    resp = requests.post(url, data={
        'chat_id': CHAT_ID,
        'text': text,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True,
    }, timeout=15)
    if not resp.ok:
        raise RuntimeError(f'Telegram API {resp.status_code}: {resp.text}')
    return resp.json()


def _split_by_hosts(text, limit=SAFE_LEN):
    """
    Бьёт секцию по границам '📍 ' (начало блока хоста). Каждая часть
    гарантированно укладывается в limit.
    """
    if len(text) <= limit:
        return [text]
    blocks = text.split('\n📍 ')
    chunks, cur = [], blocks[0]
    for b in blocks[1:]:
        piece = '\n📍 ' + b
        if len(cur) + len(piece) > limit:
            chunks.append(cur)
            cur = '📍 ' + b
        else:
            cur += piece
    if cur:
        chunks.append(cur)
    return chunks


def send(text):
    """Шлёт текст, при необходимости разбивая по хостам."""
    for chunk in _split_by_hosts(text):
        _send_raw(chunk)


def send_report(sections):
    """Каждая секция — отдельное сообщение (с разбивкой по хостам если >SAFE_LEN)."""
    parts = [s for s in sections if s]
    if not parts:
        raise ValueError('Нет секций для отправки')
    for s in parts:
        send(s)
