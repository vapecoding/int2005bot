# Session Notes: 2026-05-20

Date: May 20, 2026

## Context

This session updated the Telegram voice transcription bot so it can do more than
return a transcript. The user wanted a lightweight learning-project workflow:
send a voice message, receive the transcription, then optionally send that text
to Groq and get an assistant response back in Telegram.

The project is still intentionally small:

- main bot code: `bot.py`
- deployment guide: `docs/deployment.md`
- deploy script: `scripts/deploy.sh`
- server app directory: `/home/botdeploy/int2005bot`
- systemd service: `int2005bot`

## What Changed

### Voice processing status text

The temporary status message shown after receiving a voice/audio message was
changed from:

```text
Слушаю и расшифровываю...
```

to:

```text
Я работаю.
```

This keeps the UI simpler while Deepgram transcription is running.

### Groq button after transcription

After Deepgram returns a transcript, the bot now edits the status message to show
the transcript and attaches an inline button:

```text
Отправить в Groq
```

When the button is pressed:

1. the bot looks up the transcript stored for that message;
2. removes the inline keyboard from the transcript message;
3. sends the transcript to Groq;
4. replies with Groq's answer.

If Groq is not configured on the server, the bot responds with:

```text
Groq API ключ не настроен на сервере.
```

### Groq integration details

The integration uses Groq's OpenAI-compatible Chat Completions endpoint:

```text
https://api.groq.com/openai/v1/chat/completions
```

Authentication uses:

```text
Authorization: Bearer $GROQ_API_KEY
```

The default model is:

```text
llama-3.3-70b-versatile
```

The model can be overridden with:

```env
GROQ_MODEL=...
```

The system prompt currently tells Groq:

```text
Ты полезный ассистент. Отвечай на русском языке кратко и по делу.
```

Long Groq answers are split into Telegram-safe chunks because Telegram messages
have a 4096-character limit.

## Environment Variables

The application now expects these variables:

```env
BOT_TOKEN=...
DEEPGRAM_API_KEY=...
GROQ_API_KEY=...
GROQ_MODEL=llama-3.3-70b-versatile
```

`BOT_TOKEN` and `DEEPGRAM_API_KEY` are required at startup.

`GROQ_API_KEY` is optional at startup so the bot can still run without Groq, but
the Groq button will not work until the key exists in the server `.env`.

Secrets must stay out of Git. The real server `.env` lives at:

```text
/home/botdeploy/int2005bot/.env
```

During this session, `GROQ_API_KEY` and `GROQ_MODEL` were added to the server
`.env`, the service was restarted, and the Groq models endpoint returned HTTP
`200`, confirming that the key was accepted.

## Deployment Work Done

Two commits were created and deployed during the session:

```text
2bb871c Update voice processing status message
0fd3c66 Add Groq button for transcribed voice messages
```

Deployment followed the documented project flow:

```bash
git add ...
git commit -m "..."
git push origin main
./scripts/deploy.sh
```

The deploy script pulled from GitHub on the VPS, installed dependencies, checked
`bot.py` syntax, and restarted `int2005bot`.

After deployment, the service status was confirmed as:

```text
active (running)
```

## Current User Flow

1. User sends a Telegram voice message or audio file.
2. Bot replies: `Я работаю.`
3. Bot downloads the Telegram audio file.
4. Bot sends the audio bytes to Deepgram.
5. Bot replaces the status message with the transcript.
6. Bot shows `Отправить в Groq`.
7. User presses the button.
8. Bot sends the transcript to Groq.
9. Bot replies with Groq's answer.

## Implementation Notes For Future Agents

- Keep secrets in `.env` only. Do not commit real API keys.
- `context.bot_data["transcripts"]` stores transcripts by Telegram chat/message
  key while the bot process is alive.
- This storage is in memory. If the bot restarts after transcription but before
  the user presses the Groq button, the button may no longer find the transcript.
  In that case the bot asks the user to send the voice message again.
- Callback data uses the prefix `groq:`.
- The code intentionally uses `httpx` directly instead of adding a Groq SDK
  dependency, keeping the project small.
- The server `.env` was edited outside Git, as expected for secrets.
- If changing deploy behavior, update `docs/deployment.md`.

## Useful Checks

Local syntax check:

```bash
.venv/bin/python -m py_compile bot.py
```

Server service status:

```bash
ssh sprintbox-2005int
sudo systemctl status int2005bot
```

Server logs:

```bash
sudo journalctl -u int2005bot -f
```

