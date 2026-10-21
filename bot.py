
import os
import re
import tempfile
import subprocess
from urllib.parse import urlparse

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("BOT_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎵 Salom!\n"
        "MP3 ga aylantirish uchun to‘g‘ridan-to‘g‘ri audio havolasini yuboring.\n"
        "Havola mp3, wav, m4a yoki boshqa audio faylga olib borishi kerak."
    )


async def get_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    if not re.match(r"^https?://", url, re.IGNORECASE):
        await update.message.reply_text(
            "Iltimos, http:// yoki https:// bilan boshlanadigan audio havolasini yuboring."
        )
        return

    parsed = urlparse(url)
    if not parsed.hostname:
        await update.message.reply_text("Havola noto‘g‘ri ko‘rinadi.")
        return

    status = await update.message.reply_text("⏳ Audio tekshirilmoqda...")

    try:
        with tempfile.TemporaryDirectory() as folder:
            source = os.path.join(folder, "audio_input")
            output = os.path.join(folder, "audio.mp3")

            # Faqat to'g'ridan-to'g'ri audio fayl havolalarini qabul qiladi.
            import urllib.request

            request = urllib.request.Request(
                url,
                headers={"User-Agent": "MusiqaIzlaBot/1.0"},
            )

            with urllib.request.urlopen(request, timeout=25) as response:
                content_type = response.headers.get("Content-Type", "").lower()
                if not content_type.startswith("audio/"):
                    await status.edit_text(
                        "❌ Bu havola to‘g‘ridan-to‘g‘ri audio fayl emas.\n"
                        "Audio faylning bevosita havolasini yuboring."
                    )
                    return

                with open(source, "wb") as f:
                    while True:
                        chunk = response.read(64 * 1024)
                        if not chunk:
                            break
                        f.write(chunk)
                        if f.tell() > 20 * 1024 * 1024:
                            raise ValueError("Audio fayl 20 MB dan katta.")

            # FFmpeg serverda mavjud bo'lsa MP3 ga aylantiradi.
            subprocess.run(
                ["ffmpeg", "-y", "-i", source, "-vn", "-codec:a",
                 "libmp3lame", "-b:a", "192k", output],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=90,
            )

            with open(output, "rb") as audio:
                await update.message.reply_audio(
                    audio=audio,
                    filename="musiqa.mp3",
                    title="MP3 audio",
                )

            await status.delete()

    except Exception:
        await status.edit_text(
            "❌ Audio tayyorlanmadi. Havola to‘g‘ridan-to‘g‘ri audio faylga "
            "olib borishini tekshiring. Serverda FFmpeg ham o‘rnatilgan bo‘lishi kerak."
        )


def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN topilmadi")

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, get_audio)
    )
    print("MusiqaIzlaBot ishga tushdi!")
    app.run_polling()


if __name__ == "__main__":
    main()
