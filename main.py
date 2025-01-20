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
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

TOKEN = '7588405517:AAHFt6wAfRb-2eiBy20w2k2v4nPSSFFW55s'

def extract_song_info(spotify_url):
    pattern = re.compile(r"https://open\.spotify\.com/track/([^?]+)")
    match = pattern.search(spotify_url)
    if match:
        track_id = match.group(1)
        return f"Spotify track {track_id}"
    else:
        raise ValueError("لینک اسپاتیفای معتبر نیست!")

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
        'cookiefile': 'cookies.txt',
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        search_results = ydl.extract_info(f"ytsearch:{query}", download=False)
        if 'entries' in search_results and len(search_results['entries']) > 0:
            info = search_results['entries'][0]
            ydl.download([info['webpage_url']])
            return f"{output_path}{info['title']}.mp3"
        else:
            raise Exception("آهنگ مورد نظر یافت نشد!")

# دریافت لینک اسپاتیفای و دانلود آهنگ
def download_spotify_track(spotify_url):
    try:
        query = extract_song_info(spotify_url)
        file_path = download_from_youtube(query)
        return file_path
    except Exception as e:
        return str(e)

# فرمان start برای ربات تلگرام
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('سلام! لطفاً لینک آهنگ اسپاتیفای را ارسال کنید.\nبرای دریافت راهنمایی، از دستور /help استفاده کنید.')

# فرمان help برای ربات تلگرام
async def help_command(update: Update, context: CallbackContext) -> None:
    help_text = (
        "ربات دانلود آهنگ اسپاتیفای\n\n"
        "1. لینک آهنگ اسپاتیفای را ارسال کنید تا آن را از یوتیوب دانلود کنم.\n"
        "2. برای استفاده از ربات، کافیست لینک اسپاتیفای را ارسال کنید.\n"
        "3. برای اطلاعات بیشتر از دستور /start استفاده کنید."
    )
    await update.message.reply_text(help_text)

# فرمان دانلود برای ربات تلگرام
async def download(update: Update, context: CallbackContext) -> None:
    spotify_url = update.message.text.strip()

    await update.message.reply_text("💠 در حال پردازش لینک...")
    
    # دانلود آهنگ از اسپاتیفای و یوتیوب
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
