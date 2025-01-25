import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
from http.cookies import SimpleCookie



# def json_to_netscape(json_file, netscape_file):
#     with open(json_file, 'r', encoding='utf-8') as f:
#         cookies = json.load(f)

#     with open(netscape_file, 'w', encoding='utf-8') as f:
#         f.write("# Netscape HTTP Cookie File\n")
#         f.write("# This is a generated file! Do not edit.\n")
#         for cookie in cookies:
#             domain = cookie.get('domain', '')
#             name = cookie.get('name', '')
#             value = cookie.get('value', '')
#             path = cookie.get('path', '/')
#             expiry = cookie.get('expires', '')
#             secure = 'TRUE' if cookie.get('secure', False) else 'FALSE'
#             httponly = 'TRUE' if cookie.get('httponly', False) else 'FALSE'
#             f.write(f"{domain}\tTRUE\t{path}\t{expiry}\t{secure}\t{name}\t{value}\n")

# # استفاده از این تابع
# json_to_netscape("cookies.json", "cookies.txt")

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from googletrans import Translator

# توکن ربات تلگرام
TELEGRAM_TOKEN = '7667164344:AAGexmRDdWX-uWoolMtVB46lEMkqO2SKkPE'

translator = Translator()

# تابع برای ترجمه پیام
async def translate(update: Update, context) -> None:
    text = update.message.text
    # جداسازی زبان هدف از متن پیام
    parts = text.split(' ', 1)
    if len(parts) > 1:
        target_language = parts[0]  # زبان هدف (مثلاً 'en')
        text_to_translate = parts[1]  # متن برای ترجمه
        translated = await translator.translate(text_to_translate, dest=target_language)
        await update.message.reply_text(f"Translated Text: {translated.text}")
    else:
        await update.message.reply_text("Please provide a target language code followed by text to translate.\nExample: 'en Hello world'.")

# شروع ربات
async def start(update: Update, context) -> None:
    await update.message.reply_text("Welcome! Send a message in the format: 'language_code text_to_translate'.\nExample: 'en Hello world'.")

def main():
    # ایجاد اپلیکیشن جدید با توکن ربات
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # افزودن هندلرها
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, translate))

    # شروع ربات
    application.run_polling()

if __name__ == '__main__':
    main()