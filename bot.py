
import os
import asyncio
import logging
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import yt_dlp
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def is_supported_url(text):
    try:
        host = urlparse(text).netloc.lower().split(":")[0]
        return (
            host == "instagram.com"
            or host.endswith(".instagram.com")
            or host == "tiktok.com"
            or host.endswith(".tiktok.com")
        )
    except Exception:
        return False


def search_songs(query):
    options = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "skip_download": True,
        "socket_timeout": 25,
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info("scsearch20:" + query, download=False)

    results = []
    seen = set()

    for item in (info.get("entries") or []):
        if not item:
            continue

        title = item.get("title") or "Nomsiz qo'shiq"
        url = item.get("webpage_url") or item.get("url")

        if not url or url in seen:
            continue

        seen.add(url)
        results.append({
            "title": title,
            "url": url,
        })

        if len(results) >= 20:
            break

    return results


def download_music(url, folder):
    options = {
        "format": "bestaudio/best",
        "outtmpl": str(Path(folder) / "%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 40,
        "retries": 2,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.download([url])

    files = list(Path(folder).glob("*.mp3"))

    if not files:
        raise Exception("MP3 tayyor bo'lmadi")

    return files[0]


def make_keyboard(results, selected):
    rows = []

    for i, song in enumerate(results):
        mark = "✅" if i in selected else "⬜"
        label = f"{mark} {i + 1}. {song['title'][:35]}"
        rows.append([
            InlineKeyboardButton(
                label,
                callback_data=f"s:{i}"
            )
        ])

    if selected:
        rows.append([
            InlineKeyboardButton(
                f"🎵 Tanlanganlarni yuklash ({len(selected)})",
                callback_data="download"
            )
        ])

    rows.append([
        InlineKeyboardButton(
            "🗑 Tanlovni tozalash",
            callback_data="clear"
        )
    ])

    return InlineKeyboardMarkup(rows)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎵 Salom! MusiqaIzlaBotga xush kelibsiz!\n\n"
        "🔎 Ijrochi yoki qo'shiq nomini yozing.\n"
        "Men 20 tagacha qo'shiq topaman.\n\n"
        "📥 Instagram yoki TikTok havolasini ham yuborishingiz mumkin."
    )


async def get_music(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()

    if not query:
        return

    if len(query) > 300:
        await update.message.reply_text("❌ Matn juda uzun.")
        return

    status = await update.message.reply_text("🔎 Musiqa qidirilmoqda...")

    try:
        if is_supported_url(query):
            with tempfile.TemporaryDirectory() as folder:
                audio = await asyncio.to_thread(
                    download_music, query, folder
                )

                if audio.stat().st_size > 45 * 1024 * 1024:
                    await status.edit_text("❌ Fayl juda katta.")
                    return

                with audio.open("rb") as file:
                    await update.message.reply_audio(
                        audio=file,
                        title=audio.stem[:64],
                        caption="🎵 MusiqaIzlaBot"
                    )

            await status.delete()
            return

        if "://" in query:
            await status.edit_text(
                "❌ Hozircha Instagram va TikTok havolalarini yuboring."
            )
            return

        results = await asyncio.to_thread(search_songs, query)

        if not results:
            await status.edit_text("❌ Qo'shiqlar topilmadi.")
            return

        context.user_data["songs"] = results
        context.user_data["selected"] = set()

        text = (
            f"🎵 {len(results)} ta natija topildi!\n\n"
            "Yoqtirgan qo'shiqlaringizni belgilang.\n"
            "Istaganingizcha tanlashingiz mumkin."
        )

        await status.edit_text(
            text,
            reply_markup=make_keyboard(results, set())
        )

    except Exception as error:
        logger.exception("Qidiruv xatosi: %s", error)
        await status.edit_text(
            "❌ Musiqani qidirishda xato yuz berdi.\n"
            "Boshqa nom bilan urinib ko'ring."
        )


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    results = context.user_data.get("songs", [])
    selected = context.user_data.get("selected", set())

    if not results:
        await query.edit_message_text(
            "Qidiruv muddati tugadi. Iltimos, qo'shiq nomini qayta yozing."
        )
        return

    if query.data.startswith("s:"):
        index = int(query.data.split(":")[1])

        if index < 0 or index >= len(results):
            return

        if index in selected:
            selected.remove(index)
        else:
            selected.add(index)

        context.user_data["selected"] = selected

        await query.edit_message_reply_markup(
            reply_markup=make_keyboard(results, selected)
        )
        return

    if query.data == "clear":
        selected.clear()
        context.user_data["selected"] = selected

        await query.edit_message_reply_markup(
            reply_markup=make_keyboard(results, selected)
        )
        return

    if query.data == "download":
        if not selected:
            await query.answer("Avval qo'shiq tanlang!", show_alert=True)
            return

        await query.edit_message_text(
            f"⏳ {len(selected)} ta qo'shiq tayyorlanmoqda..."
        )

        success = 0
        failed = 0

        for index in sorted(selected):
            song = results[index]

            try:
                with tempfile.TemporaryDirectory() as folder:
                    audio = await asyncio.to_thread(
                        download_music, song["url"], folder
                    )

                    if audio.stat().st_size > 45 * 1024 * 1024:
                        failed += 1
                        continue

                    with audio.open("rb") as file:
                        await context.bot.send_audio(
                            chat_id=query.message.chat_id,
                            audio=file,
                            title=song["title"][:64],
                            caption="🎵 MusiqaIzlaBot"
                        )

                success += 1

            except Exception as error:
                logger.warning(
                    "Yuklash xatosi: %s | %s",
                    song["title"], error
                )
                failed += 1

        context.user_data.pop("songs", None)
        context.user_data.pop("selected", None)

        await query.edit_message_text(
            f"✅ Tayyor!\n\n"
            f"Yuklandi: {success} ta\n"
            f"Xatolik: {failed} ta\n\n"
            f"Yana musiqa izlash uchun qo'shiq nomini yozing."
        )


def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN topilmadi!")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, get_music)
    )
    app.add_handler(CallbackQueryHandler(buttons))

    print("MusiqaIzlaBot ishga tushdi!")
    app.run_polling()


if __name__ == "__main__":
    main()
