
import os
import asyncio
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

if not TOKEN:
    raise ValueError("BOT_TOKEN topilmadi")

ALLOWED_DOMAINS = (
    "youtube.com",
    "youtu.be",
    "instagram.com",
    "tiktok.com",
)


def valid_url(url):
    try:
        host = (urlparse(url).hostname or "").lower()
        return any(
            host == domain or host.endswith("." + domain)
            for domain in ALLOWED_DOMAINS
        )
    except ValueError:
        return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎵 Salom! Instagram Reels, TikTok yoki "
        "YouTube havolasini yuboring.\n"
        "Men ruxsatingiz bor videodan MP3 tayyorlashga urinaman."
    )


async def get_music(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    if not valid_url(url):
        await update.message.reply_text(
            "❌ Iltimos, Instagram, TikTok yoki "
            "YouTube havolasini yuboring."
        )
        return

    status = await update.message.reply_text(
        "⏳ Audio tayyorlanmoqda..."
    )

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = str(Path(temp_dir) / "audio.%(ext)s")

            options = {
                "format": "bestaudio/best",
                "outtmpl": output,
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
                "socket_timeout": 30,
                "retries": 1,
                "max_filesize": 45 * 1024 * 1024,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
            }

            def download():
                with yt_dlp.YoutubeDL(options) as ydl:
                    ydl.download([url])

            await asyncio.to_thread(download)

            files = list(Path(temp_dir).glob("audio.mp3"))

            if not files:
                raise FileNotFoundError("MP3 fayl yaratilmagan")

            audio = files[0]

            with audio.open("rb") as file:
                await update.message.reply_audio(
                    audio=file,
                    title="Musiqa Izla MP3",
                    caption="🎵 MP3 tayyor!"
                )

            await status.delete()

    except Exception as error:
        print(f"Audio xatosi: {error}")
        await status.edit_text(
            "❌ Audio olinmadi. Havola yopiq bo‘lishi "
            "yoki sayt qo‘shimcha tasdiq talab qilishi mumkin. "
            "Boshqa havolani sinab ko‘ring."
        )


def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, get_music)
    )

    print("Musiqa Izla bot ishga tushdi!")
    app.run_polling()


if __name__ == "__main__":
    main()

