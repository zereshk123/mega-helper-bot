# import yt_dlp
# import re
# import os
# import sys
# sys.stdout.reconfigure(encoding='utf-8') 

# # استخراج نام آهنگ و هنرمند از لینک اسپاتیفای (بدون نیاز به API)
# def extract_song_info(spotify_url):
#     # تلاش برای استخراج شناسه آهنگ از URL
#     pattern = re.compile(r"https://open\.spotify\.com/track/([^?]+)")
#     match = pattern.search(spotify_url)
#     if match:
#         track_id = match.group(1)
#         return f"Spotify track {track_id}"
#     else:
#         raise ValueError("لینک اسپاتیفای معتبر نیست!")

# # دانلود آهنگ از یوتیوب با استفاده از کوکی‌ها
# def download_from_youtube(query, output_path="downloads/"):
#     if not os.path.exists(output_path):
#         os.makedirs(output_path)

#     options = {
#         'format': 'bestaudio/best',
#         'outtmpl': f'{output_path}%(title)s.%(ext)s',
#         'postprocessors': [{
#             'key': 'FFmpegExtractAudio',
#             'preferredcodec': 'mp3',
#             'preferredquality': '192',
#         }],
#         'cookiefile': 'cookies.txt',  # فایل کوکی‌های استخراج‌شده
#     }

#     with yt_dlp.YoutubeDL(options) as ydl:
#         search_results = ydl.extract_info(f"ytsearch:{query}", download=False)
#         if 'entries' in search_results and len(search_results['entries']) > 0:
#             info = search_results['entries'][0]
#             ydl.download([info['webpage_url']])
#             return f"{output_path}{info['title']}.mp3"

# # دریافت لینک اسپاتیفای و دانلود آهنگ
# def download_spotify_track(spotify_url):
#     try:
#         print("در حال پردازش لینک اسپاتیفای...")
#         query = extract_song_info(spotify_url)
#         print(f"جستجو برای آهنگ: {query}")
        
#         print("در حال دانلود از یوتیوب...")
#         file_path = download_from_youtube(query)
#         print(f"دانلود کامل شد! فایل ذخیره‌شده: {file_path}")
#     except Exception as e:
#         print(f"خطا: {e}")

# # اجرای برنامه
# if __name__ == "__main__":
#     spotify_url = input("لینک آهنگ اسپاتیفای را وارد کنید: ")
#     download_spotify_track(spotify_url)


#BOT TELEGRAM

import sys
sys.stdout.reconfigure(encoding='utf-8')

import yt_dlp
import re
import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# اطلاعات API اسپاتیفای
SPOTIPY_CLIENT_ID = "5fe7a0ec665943c593038ab1c88f7fb6"
SPOTIPY_CLIENT_SECRET = "f1683bc1aeb847d1bbc511aeccbc4ea5"

TOKEN = '7588405517:AAHFt6wAfRb-2eiBy20w2k2v4nPSSFFW55s'

def get_spotify_track_info(spotify_url):
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET))
    track_id = spotify_url.split("/")[-1].split("?")[0]
    track_info = sp.track(track_id)
    track_name = track_info["name"]
    artist_name = track_info["artists"][0]["name"]
    return f"{track_name} {artist_name}"

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
        
        raise Exception("آهنگ مورد نظر یافت نشد!")

def download_spotify_track(spotify_url):
    try:
        query = get_spotify_track_info(spotify_url)
        file_path = download_from_youtube(query)
        return file_path
    except Exception as e:
        return str(e)

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('سلام! لطفاً لینک آهنگ اسپاتیفای را ارسال کنید.\nبرای دریافت راهنمایی، از دستور /help استفاده کنید.')

async def help_command(update: Update, context: CallbackContext) -> None:
    help_text = (
        "ربات دانلود آهنگ اسپاتیفای\n\n"
        "1. لینک آهنگ اسپاتیفای را ارسال کنید تا آن را از یوتیوب دانلود کنم.\n"
        "2. برای استفاده از ربات، کافیست لینک اسپاتیفای را ارسال کنید.\n"
        "3. برای اطلاعات بیشتر از دستور /start استفاده کنید."
    )
    await update.message.reply_text(help_text)

async def download(update: Update, context: CallbackContext) -> None:
    spotify_url = update.message.text.strip()
    await update.message.reply_text("💠 در حال پردازش لینک...")
    
    file_path = download_spotify_track(spotify_url)
    
    if "خطا" in file_path or "یافت نشد" in file_path:
        await update.message.reply_text(f"⚠ مشکلی پیش امده: {file_path}")
    else:
        await update.message.reply_text("✅ در حال ارسال فایل...")
        try:
            with open(file_path, 'rb') as audio_file:
                await update.message.reply_audio(audio=audio_file)
            os.remove(file_path)
        except Exception as e:
            await update.message.reply_text(f"⚠ خطا در ارسال فایل: {e}")

def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download))

    application.run_polling()

if __name__ == '__main__':
    main()
