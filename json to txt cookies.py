import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
from http.cookies import SimpleCookie



def json_to_netscape(json_file, netscape_file):
    with open(json_file, 'r', encoding='utf-8') as f:
        cookies = json.load(f)

    with open(netscape_file, 'w', encoding='utf-8') as f:
        f.write("# Netscape HTTP Cookie File\n")
        f.write("# This is a generated file! Do not edit.\n")
        for cookie in cookies:
            domain = cookie.get('domain', '')
            name = cookie.get('name', '')
            value = cookie.get('value', '')
            path = cookie.get('path', '/')
            expiry = cookie.get('expires', '')
            secure = 'TRUE' if cookie.get('secure', False) else 'FALSE'
            httponly = 'TRUE' if cookie.get('httponly', False) else 'FALSE'
            f.write(f"{domain}\tTRUE\t{path}\t{expiry}\t{secure}\t{name}\t{value}\n")

# استفاده از این تابع
print("save cookies")
json_to_netscape("cookies.json", "cookies.txt")

# import yt_dlp
# from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ReplyKeyboardMarkup, KeyboardButton
# from telegram.ext import CallbackContext, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ApplicationBuilder
# import os

# TOKEN = "7667164344:AAGexmRDdWX-uWoolMtVB46lEMkqO2SKkPE"
# application = ApplicationBuilder().token(TOKEN).build()

# def get_video_info(url):
#     options = {
#         "quiet": True,
#         "cookies": "cookies.txt"  # استفاده از کوکی‌های ذخیره‌شده
#     }
#     with yt_dlp.YoutubeDL(options) as ydl:
#         info = ydl.extract_info(url, download=False)
#         return info

# def download_youtube_audio(url, output_path="downloads/"):
#     if not os.path.exists(output_path):
#         os.makedirs(output_path)

#     options = {
#         'format': 'bestaudio/best',
#         'outtmpl': f'{output_path}%(title)s.%(ext)s',
#         'cookies': "cookies.txt",
#         'postprocessors': [{
#             'key': 'FFmpegExtractAudio',
#             'preferredcodec': 'mp3',
#             'preferredquality': '192',
#         }]
#     }

#     with yt_dlp.YoutubeDL(options) as ydl:
#         ydl.download([url])
#         info = ydl.extract_info(url, download=False)
#         return f"{output_path}{info['title']}.mp3"

# def download_youtube_video(url, quality, output_path="downloads/"):
#     if not os.path.exists(output_path):
#         os.makedirs(output_path)

#     options = {
#         'format': f'bestvideo[height<={quality}]+bestaudio/best',
#         'outtmpl': f'{output_path}%(title)s.%(ext)s',
#         'cookies': "cookies.txt",
#     }

#     with yt_dlp.YoutubeDL(options) as ydl:
#         ydl.download([url])
#         info = ydl.extract_info(url, download=False)
#         return f"{output_path}{info['title']}.mp4"

# async def youtube_download_handler(update: Update, context: CallbackContext) -> None:
#     user_id = update.message.chat_id
#     url = update.message.text.strip()

#     info = get_video_info(url)
#     duration = info.get('duration', 0)
#     title = info.get('title', 'Unknown')
#     file_size = info.get('filesize', 0)
    
#     if duration > 900 or file_size > 500 * 1024 * 1024:
#         await update.message.reply_text(f"✅ ویدیوی شما آماده دانلود است: {info['webpage_url']}")
#         return

#     keyboard = [
#         [InlineKeyboardButton("🎵 MP3 (Audio)", callback_data=f"yt_mp3|{url}"),
#          InlineKeyboardButton("📹 MP4 (Video)", callback_data=f"yt_mp4|{url}")]
#     ]
#     reply_markup = InlineKeyboardMarkup(keyboard)
    
#     await update.message.reply_text(f"🔹 ویدیو: {title}\n📌 لطفا فرمت را انتخاب کنید:", reply_markup=reply_markup)

# async def youtube_format_handler(update: Update, context: CallbackContext) -> None:
#     query = update.callback_query
#     user_id = query.from_user.id
#     data = query.data.split('|')
#     action, url = data[0], data[1]

#     try:
#         if action == "yt_mp3":
#             file_path = download_youtube_audio(url)
#             with open(file_path, "rb") as f:
#                 await context.bot.send_audio(chat_id=user_id, audio=f)
#             os.remove(file_path)
#         elif action == "yt_mp4":
#             keyboard = [[InlineKeyboardButton(q, callback_data=f"yt_quality|{q}|{url}") for q in ["360", "480", "720", "1080"]]]
#             reply_markup = InlineKeyboardMarkup(keyboard)
#             await query.message.reply_text("🔹 لطفاً کیفیت ویدیو را انتخاب کنید:", reply_markup=reply_markup)
#     except Exception as e:
#         await query.message.reply_text(f"خطا در دانلود: {str(e)}")

# async def youtube_quality_handler(update: Update, context: CallbackContext) -> None:
#     query = update.callback_query
#     user_id = query.from_user.id
#     data = query.data.split('|')
#     action, quality, url = data[0], data[1], data[2]

#     try:
#         if action == "yt_quality":
#             file_path = download_youtube_video(url, quality)
#             with open(file_path, "rb") as f:
#                 await context.bot.send_video(chat_id=user_id, video=f)
#             os.remove(file_path)
#     except Exception as e:
#         await query.message.reply_text(f"خطا در دانلود: {str(e)}")

# application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'https?://(www\.)?youtube\.com/watch\?v='), youtube_download_handler))
# application.add_handler(CallbackQueryHandler(youtube_format_handler, pattern='^yt_mp3|yt_mp4'))
# application.add_handler(CallbackQueryHandler(youtube_quality_handler, pattern='^yt_quality'))

# if __name__ == "__main__":
#     application.run_polling()
