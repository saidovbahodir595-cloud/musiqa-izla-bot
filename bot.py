
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
PAGE_SIZE = 10

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
        info = ydl.extract_info(
            "scsearch20:" + query,
            download=False
        )

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


def selection_text(results, selected, downloaded):
    pending = selected - downloaded

    return (
        f"🎵 MUSIQA IZLA BOT\n\n"
        f"🔎 Topilgan: {len(results)} ta qo'shiq\n"
        f"☑️ Tanlangan: {len(selected)} ta\n"
        f"📥 Yuklangan: {len(downloaded)} ta\n"
        f"⏳ Navbatda: {len(pending)} ta\n\n"
        f"Kerakli qo'shiqlarni belgilang.\n"
        f"Yuklangan qo'shiqlar ro'yxatda qoladi!"
    )


def make_keyboard(results, selected, downloaded, page=0):
    rows = []

    total_pages = max(
        1, (len(results) + PAGE_SIZE - 1) // PAGE_SIZE
    )

    page = max(0, min(page, total_pages - 1))

    start = page * PAGE_SIZE
    end = min(start + PAGE_SIZE, len(results))

    for i in range(start, end):
        song = results[i]

        if i in downloaded:
            mark = "📥"
        elif i in selected:
            mark = "✅"
        else:
            mark = "⬜"

        title = song["title"][:38]

        rows.append([
            InlineKeyboardButton(
                f"{mark} {i + 1}. {title}",
                callback_data=f"s:{i}"
            )
        ])

    # Sahifalarni almashtirish
    navigation = []

    if page > 0:
        navigation.append(
            InlineKeyboardButton(
                "⬅️ Oldingi",
                callback_data=f"p:{page - 1}"
            )
        )

    navigation.append(
        InlineKeyboardButton(
            f"{page + 1}/{total_pages}",
            callback_data="noop"
        )
    )

    if page < total_pages - 1:
        navigation.append(
            InlineKeyboardButton(
                "Keyingi ➡️",
                callback_data=f"p:{page + 1}"
            )
        )

    rows.append(navigation)

    # Yuklab olish
    pending = selected - downloaded

    if pending:
        rows.append([
            InlineKeyboardButton(
                f"⬇️ Yuklab olish ({len(pending)} ta)",
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
        "🎵 MUSIQA IZLA BOTGA XUSH KELIBSIZ!\n\n"
        "🔎 Qo'shiq nomi yoki ijrochi ismini yozing.\n\n"
        "🎶 Sizga 20 tagacha qo'shiq topaman.\n"
        "☑️ Istaganingizcha qo'shiq tanlang.\n"
        "📥 Bir nechta qo'shiqni ketma-ket yuklab oling.\n\n"
        "📌 Instagram va TikTok havolalari ham ishlaydi."
    )


async def get_music(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()

    if not query:
        return

    if len(query) > 300:
        await update.message.reply_text("❌ Matn juda uzun.")
        return

    status = await update.message.reply_text(
        "🔎 Qo'shiqlar qidirilmoqda..."
    )

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
                        caption="🎵 Musiqa Izla Bot"
                    )

            await status.delete()
            return

        if "://" in query:
            await status.edit_text(
                "❌ Hozircha Instagram va TikTok "
                "havolalarini yuboring."
            )
            return

        results = await asyncio.to_thread(
            search_songs, query
        )

        if not results:
            await status.edit_text(
                "❌ Qo'shiqlar topilmadi."
            )
            return

        # Yangi qidiruv uchun yangi ro'yxat
        context.user_data["songs"] = results
        context.user_data["selected"] = set()
        context.user_data["downloaded"] = set()
        context.user_data["page"] = 0

        selected = context.user_data["selected"]
        downloaded = context.user_data["downloaded"]

        await status.edit_text(
            selection_text(results, selected, downloaded),
            reply_markup=make_keyboard(
                results, selected, downloaded, 0
            )
        )

    except Exception as error:
        logger.exception("Qidiruv xatosi: %s", error)

        await status.edit_text(
            "❌ Musiqani qidirishda xato yuz berdi.\n"
            "Boshqa nom bilan urinib ko'ring."
        )


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    results = context.user_data.get("songs", [])
    selected = context.user_data.get("selected", set())
    downloaded = context.user_data.get("downloaded", set())
    page = context.user_data.get("page", 0)

    if not results:
        await query.answer(
            "Avval qo'shiq nomini yuboring!",
            show_alert=True
        )
        return

    # Sahifa almashtirish
    if query.data.startswith("p:"):
        await query.answer()

        page = int(query.data.split(":")[1])
        context.user_data["page"] = page

        await query.edit_message_text(
            selection_text(results, selected, downloaded),
            reply_markup=make_keyboard(
                results, selected, downloaded, page
            )
        )
        return

    # Raqamli qo'shiq tanlash
    if query.data.startswith("s:"):
        await query.answer()

        index = int(query.data.split(":")[1])

        if index < 0 or index >= len(results):
            return

        if index in selected:
            selected.remove(index)
            downloaded.discard(index)
        else:
            selected.add(index)

        context.user_data["selected"] = selected
        context.user_data["downloaded"] = downloaded

        await query.edit_message_text(
            selection_text(results, selected, downloaded),
            reply_markup=make_keyboard(
                results, selected, downloaded, page
            )
        )
        return

    # Bo'sh sahifa raqami
    if query.data == "noop":
        await query.answer()
        return

    # Tanlovni tozalash
    if query.data == "clear":
        await query.answer()

        selected.clear()
        downloaded.clear()

        context.user_data["selected"] = selected
        context.user_data["downloaded"] = downloaded

        await query.edit_message_text(
            selection_text(results, selected, downloaded),
            reply_markup=make_keyboard(
                results, selected, downloaded, page
            )
        )
        return

    # Tanlangan qo'shiqlarni yuklab olish
    if query.data == "download":
        pending = sorted(selected - downloaded)

        if not pending:
            await query.answer(
                "Yuklab olinadigan qo'shiq yo'q!",
                show_alert=True
            )
            return

        await query.answer()

        await query.edit_message_text(
            f"⏳ {len(pending)} ta qo'shiq yuklanmoqda...\n\n"
            "Iltimos, kuting."
        )

        success = 0
        failed = 0

        for index in pending:
            song = results[index]

            try:
                with tempfile.TemporaryDirectory() as folder:
                    audio = await asyncio.to_thread(
                        download_music,
                        song["url"],
                        folder
                    )

                    if audio.stat().st_size > 45 * 1024 * 1024:
                        failed += 1
                        continue

                    with audio.open("rb") as file:
                        await context.bot.send_audio(
                            chat_id=query.message.chat_id,
                            audio=file,
                            title=song["title"][:64],
                            caption="🎵 Musiqa Izla Bot"
                        )

                success += 1

                # Yuklanganini belgilash
                downloaded.add(index)
                context.user_data["downloaded"] = downloaded

            except Exception as error:
                logger.warning(
                    "Yuklash xatosi: %s | %s",
                    song["title"],
                    error
                )
                failed += 1

        # MUHIM: songs va selected o'chirilmaydi!
        await query.edit_message_text(
            f"✅ YUKLASH YAKUNLANDI!\n\n"
            f"📥 Muvaffaqiyatli: {success} ta\n"
            f"❌ Xatolik: {failed} ta\n\n"
            f"☑️ Tanlangan: {len(selected)} ta\n"
            f"📥 Jami yuklangan: {len(downloaded)} ta\n\n"
            f"Qolgan qo'shiqlarni ham yuklashingiz mumkin!",
            reply_markup=make_keyboard(
                results, selected, downloaded, page
            )
        )


def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN topilmadi!")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            get_music
        )
    )

    app.add_handler(
        CallbackQueryHandler(buttons)
    )

    print("Musiqa Izla Bot ishga tushdi!")

    app.run_polling()


if __name__ == "__main__":
    main()
