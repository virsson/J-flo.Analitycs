"""
Диагностика: показывает все чаты, которые видел ваш бот, чтобы найти
правильный TELEGRAM_CHAT_ID для группы.

Перед запуском:
  1. Добавьте бота в нужную группу.
  2. В этой группе напишите любое сообщение (например '/start' или 'тест').
  3. Запустите: python check_chat.py

Важно: в @BotFather -> /mybots -> <ваш бот> -> Bot Settings -> Group Privacy
выключите Privacy Mode, иначе бот не увидит обычные сообщения в группах
(либо сделайте его админом группы).
"""
import os

import requests
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

if not TOKEN:
    raise SystemExit('TELEGRAM_BOT_TOKEN не задан в .env')

resp = requests.get(
    f'https://api.telegram.org/bot{TOKEN}/getUpdates',
    timeout=15,
)
data = resp.json()

if not data.get('ok'):
    raise SystemExit(f'Telegram API error: {data}')

chats = {}
for upd in data.get('result', []):
    msg = upd.get('message') or upd.get('channel_post') or \
          upd.get('my_chat_member', {}).get('chat') and {'chat': upd['my_chat_member']['chat']}
    if not msg:
        continue
    chat = msg.get('chat')
    if not chat:
        continue
    chats[chat['id']] = chat

if not chats:
    print('Бот не видел ни одного чата.')
    print('Проверьте: (1) бот добавлен в группу, (2) в группе было сообщение')
    print('после добавления, (3) Privacy Mode выключен или бот — админ.')
else:
    print('Найденные чаты:')
    for cid, chat in chats.items():
        title = chat.get('title') or chat.get('username') or chat.get('first_name', '')
        ctype = chat.get('type', '?')
        print(f'  chat_id={cid}  type={ctype}  name={title!r}')
