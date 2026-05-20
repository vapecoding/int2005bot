# Telegram Bot

Минимальный каркас для Telegram-бота на Python.

## Запуск

1. Создай бота через BotFather в Telegram и получи токен.
2. Создай файл `.env` рядом с `bot.py`:

```env
BOT_TOKEN=твой_токен_сюда
DEEPGRAM_API_KEY=твой_deepgram_ключ_сюда
GROQ_API_KEY=твой_groq_ключ_сюда
GROQ_MODEL=llama-3.3-70b-versatile
```

3. Запусти бота:

```bash
.venv/bin/python bot.py
```

Бот расшифровывает голосовые сообщения и показывает кнопку для отправки текста в Groq.
