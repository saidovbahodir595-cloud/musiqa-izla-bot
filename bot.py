
import os
from urllib.parse import quote_plus
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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎵 Salom! Musiqa nomini yuboring. "
        "Men sizga qidiruv havolasini beraman."
    )


async def get_music(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()

    if not query:
        await update.message.reply_text("Musiqa nomini yozing.")
        return

    search_url = (
        "https://www.youtube.com/results?search_query="
        + quote_plus(query)
    )

    await update.message.reply_text(
        f"🎵 Qidiruv: {query}\n\n"
        f"🔎 Musiqani shu yerdan toping:\n{search_url}"
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
