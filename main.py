import sys
sys.stdout.reconfigure(encoding='utf-8')
import re
import yt_dlp
import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler


SPOTIPY_CLIENT_ID = "5fe7a0ec665943c593038ab1c88f7fb6"
SPOTIPY_CLIENT_SECRET = "f1683bc1aeb847d1bbc511aeccbc4ea5"
TOKEN = '7909360615:AAESgbGRtLj5_9RnW-qJTA4Rxnyi-gb_DgQ'
user_data = {}


def get_spotify_track_info(spotify_url):
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET))
    track_id = spotify_url.split("/")[-1].split("?")[0]
    track_info = sp.track(track_id)
    track_name = track_info["name"]
    artist_name = track_info["artists"][0]["name"]
    album_name = track_info["album"]["name"]
    release_date = track_info["album"]["release_date"]
    cover_image = track_info["album"]["images"][0]["url"]
    
    return track_name, artist_name, album_name, release_date, cover_image

def download_from_youtube(query, output_path="downloads/"):
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    options = {
        'format': 'bestaudio/best',
        'outtmpl': f'{output_path}%(title)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        search_results = ydl.extract_info(f"ytsearch5:{query}", download=False)
        
        if 'entries' in search_results and len(search_results['entries']) > 0:
            best_match = None
            for entry in search_results['entries']:
                title = entry['title'].lower()
                if all(word in title for word in query.lower().split()):
                    best_match = entry
                    break
            
            if best_match:
                ydl.download([best_match['webpage_url']])
                return f"{output_path}{best_match['title']}.mp3"
        
        raise Exception("⚠متاسفیم... آهنگ مورد نظر شما یافت نشد :(")

async def start(update: Update, context: CallbackContext) -> None:
    user_id = str(update.effective_user.id)
    user_name = update.effective_user.full_name
    username = update.effective_user.username

    keyboard = [
        [KeyboardButton("📊 حساب کاربری 📊")],
        [KeyboardButton("💰 افزایش سکه 💰"), KeyboardButton("👨‍💻راهنما و پشتیبانی 👨‍💻")]
    ]
    inline_markup = ReplyKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=user_id,
        text=f"سلام {user_name} عزیز\n\n✨به ربات اسپاتیفای دانلود خوش اومدی\n💎برای شروع کار میتونی از دکمه های زیر استفاده کنی یا اگه میخوای آهنگی دانلود کنی کافیه لینک آهنگو برام بفرستی",
        reply_to_message_id=update.effective_message.id,
        reply_markup=inline_markup
    )
    return

async def help(update: Update, context: CallbackContext) -> None:
    help_text = (
        "ربات دانلود آهنگ اسپاتیفای\n\n"
        "1. لینک آهنگ اسپاتیفای را ارسال کنید تا آن را از یوتیوب دانلود کنم.\n"
        "2. برای استفاده از ربات، کافیست لینک اسپاتیفای را ارسال کنید.\n"
        "3. برای اطلاعات بیشتر از دستور /start استفاده کنید."
    )
    await update.message.reply_text(help_text)

async def echo(update: Update, context: CallbackContext) -> None:
    user_id = str(update.effective_user.id)
    text = update.message.text
    pattern = r'https?://open\.spotify\.com/(track|album|playlist|artist)/[a-zA-Z0-9]+'
    
    if text == "🔙 بازگشت 🔙":
        await start(update, context)
        return
    
    elif re.match(pattern, text) is not None:
        spotify_url = update.message.text.strip()
        await update.message.reply_text("💠 در حال پردازش لینک...")
        
        track_name, artist_name, album_name, release_date, cover_image = get_spotify_track_info(spotify_url)
        query = f"{track_name} {artist_name}"
        
        user_data[update.message.from_user.id] = {
            "query": query,
            "spotify_url": spotify_url,
            "message_id": update.message.message_id
        }
        
        caption = (
            f"🎵 آهنگ: {track_name}\n"
            f"🎤 هنرمند: {artist_name}\n"
            f"💿 آلبوم: {album_name}\n"
            f'<a href="{spotify_url}">🔗 لینک آهنگ</a>\n'
            f"📅 تاریخ انتشار: {release_date}\n\n"
            "💠آیا می‌خواهید این آهنگ را دانلود کنید؟"
        )

        keyboard = [
            [InlineKeyboardButton("✅ بله", callback_data="confirm")],
            [InlineKeyboardButton("❌ خیر", callback_data="cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_photo(
            photo=cover_image,
            caption=caption,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    
    else:
        keyboard = [
            [KeyboardButton("🔙 بازگشت 🔙")]
        ]
        inline_markup = ReplyKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=user_id,
            text="دستور شما نا مفهموم هست!\nلطفا دکمه بازگشت را بزنید تا دستورات به شما نمایش داده شود ⬇",
            reply_to_message_id=update.effective_message.id,
            reply_markup=inline_markup
        )

async def handle_confirmation(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == "confirm":
        await context.bot.send_message(chat_id=user_id, text="💠در حال دانلود آهنگ...")
        
        try:
            query_text = user_data[user_id]["query"]
            file_path = download_from_youtube(query_text)
            
            await context.bot.send_message(chat_id=user_id, text="✅آهنگ با موفقیت دانلود شد👌\nدر حال ارسال فایل...")
            with open(file_path, 'rb') as audio_file:
                await context.bot.send_audio(chat_id=user_id, audio=audio_file)
            os.remove(file_path)
        
        except Exception as e:
            error_message = str(e)

            if error_message == "1008096572":
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"⚠مشکلی پیش آمده:\n\nمهلت دانلود این آهنگ گذشته است! لطفا دوباره لینک آن را بفرستید..."
                )
            else:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"⚠مشکلی پیش آمده:\n\n{error_message}"
                )
    
    elif query.data == "cancel":
        await context.bot.send_message(chat_id=user_id, text="❌فرآیند دانلود لغو شد")

def main():
    print("[BOT] initializing...")
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    application.add_handler(CallbackQueryHandler(handle_confirmation))
    print("[BOT] running bot...")
    application.run_polling()

if __name__ == '__main__':
    main()