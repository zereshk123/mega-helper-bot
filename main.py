import sys
sys.stdout.reconfigure(encoding='utf-8')

import yt_dlp
import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler

# اطلاعات API اسپاتیفای
SPOTIPY_CLIENT_ID = "5fe7a0ec665943c593038ab1c88f7fb6"
SPOTIPY_CLIENT_SECRET = "f1683bc1aeb847d1bbc511aeccbc4ea5"

TOKEN = '7588405517:AAHFt6wAfRb-2eiBy20w2k2v4nPSSFFW55s'

# دیکشنری برای ذخیره اطلاعات موقت کاربران
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
        
        raise Exception("⚠ آهنگ مورد نظر یافت نشد :(")

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('سلام! لطفاً لینک آهنگ اسپاتیفای را ارسال کنید.\nبرای دریافت راهنمایی، از دستور /help استفاده کنید.')

async def help(update: Update, context: CallbackContext) -> None:
    help_text = (
        "ربات دانلود آهنگ اسپاتیفای\n\n"
        "1. لینک آهنگ اسپاتیفای را ارسال کنید تا آن را از یوتیوب دانلود کنم.\n"
        "2. برای استفاده از ربات، کافیست لینک اسپاتیفای را ارسال کنید.\n"
        "3. برای اطلاعات بیشتر از دستور /start استفاده کنید."
    )
    await update.message.reply_text(help_text)

async def handle_spotify_link(update: Update, context: CallbackContext) -> None:
    spotify_url = update.message.text.strip()
    await update.message.reply_text("💠 در حال پردازش لینک...")
    
    try:
        # دریافت اطلاعات آهنگ از اسپاتیفای
        track_name, artist_name, album_name, release_date, cover_image = get_spotify_track_info(spotify_url)
        query = f"{track_name} {artist_name}"
        
        # ذخیره اطلاعات موقت برای کاربر
        user_data[update.message.from_user.id] = {
            "query": query,
            "spotify_url": spotify_url,
            "message_id": update.message.message_id  # ذخیره شناسه پیام
        }
        
        # ارسال اطلاعات آهنگ و تصویر به کاربر
        caption = (
            f"🎵 آهنگ: {track_name}\n"
            f"🎤 هنرمند: {artist_name}\n"
            f"💿 آلبوم: {album_name}\n"
            f"📅 تاریخ انتشار: {release_date}\n\n"
            "آیا می‌خواهید این آهنگ را دانلود کنید؟"
        )
        keyboard = [
            [InlineKeyboardButton("✅ بله", callback_data="confirm")],
            [InlineKeyboardButton("❌ خیر", callback_data="cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_photo(photo=cover_image, caption=caption, reply_markup=reply_markup)
    
    except Exception as e:
        await update.message.reply_text(f"⚠ مشکلی پیش آمده:\n{e}")

async def handle_confirmation(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    try:
        # حذف پیام قبلی که حاوی اطلاعات آهنگ است
        if user_id in user_data and "message_id" in user_data[user_id]:
            message_id = user_data[user_id]["message_id"]
            await context.bot.delete_message(chat_id=user_id, message_id=message_id)
        
        if query.data == "confirm":
            await context.bot.send_message(chat_id=user_id, text="💠 در حال دانلود آهنگ...")
            
            try:
                # دریافت اطلاعات موقت کاربر
                query_text = user_data[user_id]["query"]
                file_path = download_from_youtube(query_text)
                
                await context.bot.send_message(chat_id=user_id, text="✅ در حال ارسال فایل...")
                with open(file_path, 'rb') as audio_file:
                    await context.bot.send_audio(chat_id=user_id, audio=audio_file)
                os.remove(file_path)
            
            except Exception as e:
                await context.bot.send_message(chat_id=user_id, text=f"⚠ مشکلی پیش آمده:\n{e}")
        
        else:
            await context.bot.send_message(chat_id=user_id, text="❌ فرآیند دانلود لغو شد")
    
    except Exception as e:
        await context.bot.send_message(chat_id=user_id, text=f"⚠ خطایی رخ داد:\n{e}")
    
    finally:
        if user_id in user_data:
            del user_data[user_id]

def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_spotify_link))
    application.add_handler(CallbackQueryHandler(handle_confirmation))

    application.run_polling()

if __name__ == '__main__':
    main()