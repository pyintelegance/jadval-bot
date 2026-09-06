# JadvalBot

Telegram бот, который знает твоё точное расписание (6 кун, 1-6 soat) и время уроков:
1: 08:00-08:45
2: 08:50-09:35
3: 09:40-10:25
4: 10:40-11:25
5: 11:30-12:15
6: 12:20-13:05

Шлёт:
- в 07:55 — bugungi jadval
- в начале каждого урока — какой сейчас урок
- за 5 минут до конца — напоминание

Команды: /now /today /jadval /start /stop

Запуск:
```
pip install -r requirements.txt
set BOT_TOKEN=xxx  (или .env)
python bot.py
```
