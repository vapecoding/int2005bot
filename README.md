# Telegram Bot

Минимальный каркас для Telegram-бота на Python.

## Запуск

1. Создай бота через BotFather в Telegram и получи токен.
2. Создай файл `.env` рядом с `bot.py`:

```env
BOT_TOKEN=твой_токен_сюда
```

3. Запусти бота:

```bash
.venv/bin/python bot.py
```

Пока бот отвечает только на `/start`. Основную логику добавим позже.

