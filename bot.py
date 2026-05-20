import os

import httpx
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)


DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"
DEEPGRAM_PARAMS = {
    "model": "nova-3",
    "language": "ru",
    "smart_format": "true",
}
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_CALLBACK_PREFIX = "groq:"
TELEGRAM_MESSAGE_LIMIT = 4096


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет. Пришли голосовое сообщение, и я расшифрую его текстом."
    )


async def transcribe_audio(audio_bytes: bytes, mime_type: str | None, api_key: str) -> str:
    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": mime_type or "application/octet-stream",
    }

    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post(
            DEEPGRAM_URL,
            params=DEEPGRAM_PARAMS,
            headers=headers,
            content=audio_bytes,
        )
        response.raise_for_status()

    data = response.json()
    alternatives = data["results"]["channels"][0]["alternatives"]
    return alternatives[0].get("transcript", "").strip()


async def ask_groq(prompt: str, api_key: str, model: str) -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "Ты полезный ассистент. Отвечай на русском языке кратко и по делу.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
    }

    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post(GROQ_URL, headers=headers, json=payload)
        response.raise_for_status()

    data = response.json()
    return data["choices"][0]["message"].get("content", "").strip()


def transcript_key(chat_id: int, message_id: int) -> str:
    return f"{chat_id}:{message_id}"


def split_telegram_text(text: str) -> list[str]:
    return [
        text[index : index + TELEGRAM_MESSAGE_LIMIT]
        for index in range(0, len(text), TELEGRAM_MESSAGE_LIMIT)
    ]


async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    deepgram_api_key = context.bot_data["deepgram_api_key"]

    audio_source = message.voice or message.audio
    mime_type = audio_source.mime_type

    await message.chat.send_action(ChatAction.TYPING)
    status_message = await message.reply_text("Я работаю.")

    try:
        telegram_file = await audio_source.get_file()
        audio_bytes = bytes(await telegram_file.download_as_bytearray())
        transcript = await transcribe_audio(audio_bytes, mime_type, deepgram_api_key)
    except httpx.HTTPStatusError as exc:
        await status_message.edit_text(
            f"Deepgram вернул ошибку {exc.response.status_code}. Проверь ключ или попробуй позже."
        )
        return
    except Exception:
        await status_message.edit_text("Не получилось расшифровать аудио. Попробуй ещё раз.")
        return

    if not transcript:
        await status_message.edit_text("Я не разобрал речь в этом сообщении.")
        return

    key = transcript_key(status_message.chat_id, status_message.message_id)
    context.bot_data.setdefault("transcripts", {})[key] = transcript
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Отправить в Groq", callback_data=f"{GROQ_CALLBACK_PREFIX}{key}")]]
    )
    await status_message.edit_text(transcript, reply_markup=keyboard)


async def handle_groq_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    groq_api_key = context.bot_data.get("groq_api_key")
    if not groq_api_key:
        await query.message.reply_text("Groq API ключ не настроен на сервере.")
        return

    key = query.data.removeprefix(GROQ_CALLBACK_PREFIX)
    transcript = context.bot_data.get("transcripts", {}).get(key)
    if not transcript:
        await query.message.reply_text("Не нашёл текст для отправки. Пришли голосовое ещё раз.")
        return

    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.chat.send_action(ChatAction.TYPING)
    status_message = await query.message.reply_text("Отправляю в Groq...")

    try:
        answer = await ask_groq(transcript, groq_api_key, context.bot_data["groq_model"])
    except httpx.HTTPStatusError as exc:
        await status_message.edit_text(
            f"Groq вернул ошибку {exc.response.status_code}. Проверь ключ или попробуй позже."
        )
        return
    except Exception:
        await status_message.edit_text("Не получилось получить ответ от Groq. Попробуй ещё раз.")
        return

    if not answer:
        await status_message.edit_text("Groq вернул пустой ответ.")
        return

    chunks = split_telegram_text(answer)
    await status_message.edit_text(chunks[0])
    for chunk in chunks[1:]:
        await query.message.reply_text(chunk)


def main() -> None:
    load_dotenv()
    token = os.getenv("BOT_TOKEN")
    deepgram_api_key = os.getenv("DEEPGRAM_API_KEY")
    groq_api_key = os.getenv("GROQ_API_KEY")
    groq_model = os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL)

    if not token:
        raise RuntimeError("BOT_TOKEN не найден. Создай .env по примеру .env.example.")
    if not deepgram_api_key:
        raise RuntimeError("DEEPGRAM_API_KEY не найден. Добавь его в .env.")

    app = Application.builder().token(token).build()
    app.bot_data["deepgram_api_key"] = deepgram_api_key
    app.bot_data["groq_api_key"] = groq_api_key
    app.bot_data["groq_model"] = groq_model

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_groq_button, pattern=f"^{GROQ_CALLBACK_PREFIX}"))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_audio))
    app.run_polling()


if __name__ == "__main__":
    main()
