
import os
import asyncio
import logging
import tempfile
from pathlib import Path

import yt_dlp
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("BOT_TOKEN topilmadi")

logging.basicConfig(level=logging.INFO)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎵 Salom! Musiqa Izla Botga xush kelibsiz!\n\n"
        "Qo‘shiq nomini yoki audio havolasini yuboring.\n"
        "Men MP3 tayyorlashga urinaman."
    )


def download_audio(query, folder):
    is_url = query.startswith(("http://", "https://"))

    target = query if is_url else "ytsearch1:" + query

    options = {
        "format": "bestaudio/best",
        "outtmpl": str(Path(folder) / "%(title).80s-%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 30,
        "retries": 2,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(target, download=True)

        if info.get("entries"):
            info = next(
                (item for item in info["entries"] if item),
                None
            )

        if not info:
            raise Exception("Audio topilmadi")

        title = info.get("title", "Musiqa")

    files = list(Path(folder).glob("*.mp3"))

    if not files:
        raise Exception("MP3 fayl tayyorlanmadi")

    return files[0], title


async def get_music(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()

    if not query:
        return

    status = await update.message.reply_text(
        "🔎 Musiqani qidiryapman, biroz kuting..."
    )

    try:
        with tempfile.TemporaryDirectory() as folder:
            audio_path, title = await asyncio.to_thread(
                download_audio, query, folder
            )

            await status.edit_text("🎧 MP3 tayyor! Yuboryapman...")

            with open(audio_path, "rb") as audio:
                await update.message.reply_audio(
                    audio=audio,
                    title=title[:64],
                    filename="musiqa.mp3",
                    read_timeout=120,
                    write_timeout=120,
                )

            await status.delete()

    except Exception as e:
    logging.exception("Musiqa yuklashda xatolik")

    await status.edit_text(
        f"❌ Xatolik sababi:\n{str(e)[:700]}"
        )
        

        
            
        
        )


def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, get_music)
    )

    print("Musiqa Izla Bot ishga tushdi!")

    app.run_polling()


if __name__ == "__main__":
    main()
