
import os
import asyncio
import logging
import tempfile
from pathlib import Path
from urllib.parse import urlparse

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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not TOKEN:
    raise ValueError("BOT_TOKEN topilmadi!")

def is_supported_url(text):
    try:
        host = urlparse(text).netloc.lower()
        return (
            host == "instagram.com"
            or host.endswith(".instagram.com")
            or host == "tiktok.com"
            or host.endswith(".tiktok.com")
            or host == "youtu.be"
            or host.endswith(".youtube.com")
        )
    except Exception:
        return False


def download_music(query, folder):
    output = str(Path(folder) / "%(title).80s.%(ext)s")

    if is_supported_url(query):
        source = query
    else:
        # Qo'shiq nomini SoundCloud'dan qidirish
        source = "scsearch1:" + query

    options = {
        "format": "bestaudio/best",
        "outtmpl": output,
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
        ydl.download([source])

    files = list(Path(folder).glob("*.mp3"))

    if not files:
        raise Exception("MP3 fayl tayyor bo'lmadi")

    return files[0]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎵 Salom! MusiqaIzlaBotga xush kelibsiz!\n\n"
        "📥 Instagram havolasini yuboring.\n"
        "📥 TikTok havolasini yuboring.\n"
        "🔎 Yoki qo'shiq nomini yozing.\n\n"
        "Men MP3 tayyorlashga harakat qilaman!"
    )


async def get_music(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()

    if not query:
        return

    if len(query) > 1000:
        await update.message.reply_text("❌ Matn juda uzun.")
        return

    if "://" in query and not is_supported_url(query):
        await update.message.reply_text(
            "❌ Hozircha Instagram, TikTok va YouTube havolalarini yuboring."
        )
        return

    status = await update.message.reply_text(
        "🔎 Musiqa qidirilmoqda...\nIltimos, kuting."
    )

    try:
        with tempfile.TemporaryDirectory() as folder:
            audio = await asyncio.to_thread(
                download_music, query, folder
            )

            if audio.stat().st_size > 45 * 1024 * 1024:
                await status.edit_text(
                    "❌ Fayl juda katta. Boshqa musiqa yuboring."
                )
                return

            await status.edit_text("🎵 MP3 tayyor! Yuborilmoqda...")

            with audio.open("rb") as file:
                await update.message.reply_audio(
                    audio=file,
                    title=audio.stem[:64],
                    caption="🎵 MusiqaIzlaBot"
                )

            await status.delete()

    except Exception as error:
        logger.exception("Musiqa yuklashda xato: %s", error)
        await status.edit_text(
            "❌ Musiqani topib yoki yuklab bo'lmadi.\n\n"
            "Boshqa havola yoki qo'shiq nomini yuboring."
        )


def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, get_music)
    )

    print("MusiqaIzlaBot ishga tushdi!")
    app.run_polling()


if __name__ == "__main__":
    main()
