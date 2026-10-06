import os
import asyncio
import yt_dlp
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎵 Salom! Musiqa nomini yoki YouTube/TikTok/Instagram havolasini yuboring."
    )

async def get_music(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()

    await update.message.reply_text("🔎 Qidiryapman...")

    filename = f"/tmp/{update.message.from_user.id}.%(ext)s"

    options = {
        "format": "bestaudio/best",
        "outtmpl": filename,
        "noplaylist": True,
        "quiet": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }

    try:
        if not query.startswith(("http://", "https://")):
            query = "ytsearch1:" + query

        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(query, download=True)

            if "entries" in info:
                info = info["entries"][0]

            title = info.get("title", "Musiqa")

        mp3_file = f"/tmp/{update.message.from_user.id}.mp3"

        await update.message.reply_audio(
            audio=open(mp3_file, "rb"),
            title=title
        )

        os.remove(mp3_file)

    except Exception as e:
        await update.message.reply_text(
            "❌ Musiqani topib bo‘lmadi. Boshqa nom yoki havola yuboring."
        )

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, get_music))

    print("Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
