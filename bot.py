import os

import httpx
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters


DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"
DEEPGRAM_PARAMS = {
    "model": "nova-3",
    "language": "ru",
    "smart_format": "true",
}


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

    await status_message.edit_text(transcript)


def main() -> None:
    load_dotenv()
    token = os.getenv("BOT_TOKEN")
    deepgram_api_key = os.getenv("DEEPGRAM_API_KEY")

    if not token:
        raise RuntimeError("BOT_TOKEN не найден. Создай .env по примеру .env.example.")
    if not deepgram_api_key:
        raise RuntimeError("DEEPGRAM_API_KEY не найден. Добавь его в .env.")

    app = Application.builder().token(token).build()
    app.bot_data["deepgram_api_key"] = deepgram_api_key

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_audio))
    app.run_polling()


if __name__ == "__main__":
    main()
