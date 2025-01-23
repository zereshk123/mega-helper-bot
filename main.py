import sys
sys.stdout.reconfigure(encoding='utf-8')

import asyncio
import re
import yt_dlp
import os
import json
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
import sqlite3
from time import sleep
from datetime import datetime, timedelta

import pytz
tehran_tz = pytz.timezone('Asia/Tehran')


# select token
with open('config.json', 'r', encoding='utf-8') as config_file:
    config = json.load(config_file)
TOKEN = config["api1"]["token"]
SPOTIPY_CLIENT_ID = config["client_spotify"]["client_id"]
SPOTIPY_CLIENT_SECRET = config["client_spotify"]["client_secret"]

user_support_progress = {}

# --- DataBase ---
def auth_db():
    with sqlite3.connect('data.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS download_spotify_progress(
                user_id TEXT PRIMARY KEY,
                step INTEGER,
                query TEXT,
                spotify_url TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users(
            user_id TEXT NOT NULL PRIMARY KEY,
            name TEXT,
            username TEXT,
            admin_type INTEGER,
            last_dice_time TEXT,
            coins INTEGER
        )''')
        conn.commit()
    print("[BOT] database checked✅")

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
        'cookies': 'cookies.txt',
        'quiet': False
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        try:
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
            else:
                raise Exception("⚠متاسفیم... آهنگ مورد نظر شما یافت نشد :(")
        
        except Exception as e:
            raise Exception(f"خطا در دانلود: {str(e)}")

async def start(update: Update, context: CallbackContext) -> None:
    user_id = str(update.effective_user.id)
    user_name = update.effective_user.full_name
    username = update.effective_user.username

    # check user
    with sqlite3.connect("data.db") as conn:
        cursor  = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        user_status = cursor.fetchone()

        if user_status:
            None
        else:
            cursor.execute("INSERT INTO users (user_id, name, username, admin_type, coins) VALUES (?, ?, ?, ?, ?)", (user_id, user_name, username, 0, config["new_user_coin"]))
            conn.commit()
            print(f"\nnew user add to database...\nuser id => {user_id}\nname => {user_name}\nusername => {username}\n\n")
        conn.commit()

    keyboard = [
        [KeyboardButton("📥 دانـلودر 📥")],
        [KeyboardButton("📊 حساب کاربری 📊")],
        [KeyboardButton("💰 افزایش سکه 💰"), KeyboardButton("👨‍💻راهنما و پشتیبانی 👨‍💻")]
    ]
    inline_markup = ReplyKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=user_id,
        text=f"سلام {user_name} عزیز✨\n\n✨به ربات خوش اومدی\n💎برای ادامه کار میتونی از گزینه های زیر استفاده کنی...",
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

    elif text == "📊 حساب کاربری 📊":
        keyboard = [
            [KeyboardButton("🔙 بازگشت 🔙")]
        ]
        inline_markup = ReplyKeyboardMarkup(keyboard)

        with sqlite3.connect("data.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user_data = cursor.fetchone()
            
        if user_data:
            if user_data[3] == 1:
                user_type = "ادمین"
            else:
                user_type = "کاربر عادی"

            user_name = user_data[1]
            username = user_data[2]
            coins = user_data[5]

            inline_keyboard = [[InlineKeyboardButton(f"⭐ نوع حساب:  {user_type}", callback_data="no_action")]]
            inline_markup = InlineKeyboardMarkup(inline_keyboard)

            await context.bot.send_message(
                chat_id=user_id,
                text=f"🔆 اطلاعات حساب کاربری شما:\n\n💠 نام شما: {user_name}\n💠 نام کاربری شما: @{username}\n💠 شناسه عددی شما: {user_id}\n💰 تعداد سکه های شما: {coins}",
                reply_to_message_id=update.effective_message.id,
                reply_markup=inline_markup
            )

        else:
            print(f"\nUser ID {user_id} was not found!\n")

            await context.bot.send_message(
                chat_id=user_id,
                text="⚠مشکلی پیش آمده...\nلطفا دوباره ربات را استارت کنید ⬇",
                reply_to_message_id=update.effective_message.id,
                reply_markup=inline_markup
            )     

    elif text == "💰 افزایش سکه 💰":
        keyboard = [
            [KeyboardButton("🎲 تاس 🎲")],
            [KeyboardButton("🔙 بازگشت 🔙")]
        ]
        inline_markup = ReplyKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=user_id,
            text="💠یکی از گزینه های زیر را انتخاب کنید...",
            reply_to_message_id=update.effective_message.id,
            reply_markup=inline_markup
        )

    elif text == "👨‍💻راهنما و پشتیبانی 👨‍💻":
        keyboard = [
            [KeyboardButton("❌ لغو ❌")]
        ]
        inline_markup = ReplyKeyboardMarkup(keyboard)

        user_support_progress[user_id] = {"step": True}

        await context.bot.send_message(
            chat_id=user_id,
            text="💠پیشنها‌د, سوال یا انتقاد خود را در قالب یک پیام ارسال کنید:",
            reply_to_message_id=update.effective_message.id,
            reply_markup=inline_markup
        )

    elif text == "🎲 تاس 🎲":
        keyboard = [
            [KeyboardButton("🔙 بازگشت 🔙")]
        ]
        inline_markup = ReplyKeyboardMarkup(keyboard)
        current_time = datetime.now(tehran_tz)

        #__check user__
        with sqlite3.connect("data.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            res = cursor.fetchone()

        if res[3] == 1:
            None

        elif res[4] is not None:
            last_dice_time = datetime.strptime(str(res[4]), "%Y-%m-%d %H:%M:%S")
            if last_dice_time.tzinfo is None:
                last_dice_time = tehran_tz.localize(last_dice_time)
            
            time_diff = current_time - last_dice_time
            
            if time_diff < timedelta(hours=48):
                remaining_time = timedelta(hours=48) -  time_diff

                days = remaining_time.days
                hours, remainder = divmod(remaining_time.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                
                remaining_time_str = f"{days} روز, {hours} ساعت, {minutes} دقیقه, {seconds} ثانیه"

                await update.message.reply_text(
                    f"⚠ کاربر گرامی شما قبلا تاس انداخته اید! لطفا {remaining_time_str} صبر کنید...",
                    reply_markup=inline_markup
                )
                return
        else:
            None

        dice_message = await update.message.reply_dice(emoji="🎲")
        dice_result = dice_message.dice.value

        cursor.execute("INSERT INTO users (user_id, last_dice_time) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET last_dice_time = excluded.last_dice_time", (user_id, current_time.strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()

        await asyncio.sleep(4)

        if res[3] == 1:        
            await update.message.reply_text(
                f"🤖:\n{dice_result} سکه به حسابت اضافه شد...",
                reply_markup=inline_markup
            )
        else:
            await update.message.reply_text(
                f"🎉 شما {dice_result} سکه بدست اوردید\n💠 بعد از 48 ساعت می توانید دوباره تاس بیندازید...",
                reply_markup=inline_markup
            )

        cursor.execute(f"UPDATE users SET coins = ? WHERE user_id = ?", (res[5]+dice_result, user_id))
        conn.commit()
        conn.close()
        return

    elif text == "📥 دانـلودر 📥":
        keyboard = [
            [KeyboardButton("🟢 اسپاتیفای دانلودر 🟢")],
            [KeyboardButton("🔙 بازگشت 🔙")]
        ]
        inline_markup = ReplyKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=user_id,
            text="💠یکی از گزینه های زیر رو انتخاب کنید:",
            reply_to_message_id=update.effective_message.id,
            reply_markup=inline_markup
        )
        return

    elif text == "🟢 اسپاتیفای دانلودر 🟢":
        keyboard = [
            [KeyboardButton("🔙 بازگشت 🔙")]
        ]
        inline_markup = ReplyKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=user_id,
            text="💠لینک آهنگ مد نظر خود را بفرستید:",
            reply_to_message_id=update.effective_message.id,
            reply_markup=inline_markup
        )    

        with sqlite3.connect("data.db") as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO download_spotify_progress (user_id, step) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET step=?', (user_id, 1, 1))
            conn.commit()
        return

    elif text == "❌ لغو ❌":
        with sqlite3.connect("data.db") as conn:
            cursor = conn.cursor()
            cursor.execute(f'DELETE FROM download_spotify_progress WHERE user_id = ? AND EXISTS (SELECT 1 FROM download_spotify_progress WHERE user_id = ?)', (user_id, user_id))
            conn.commit()

        if user_id in user_support_progress:
            del user_support_progress[user_id]

        await start(update, context)
        return

    else:
        with sqlite3.connect("data.db") as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT step FROM download_spotify_progress WHERE user_id = {user_id}")
            download_spotify_result = cursor.fetchone()
        
        if user_id in user_support_progress:
            inline_keyboard = [
                [InlineKeyboardButton("🔙 برگشتن", callback_data="back")]
            ]
            inline_markup = InlineKeyboardMarkup(inline_keyboard)

            message = update.message.text
            sender_name = update.message.from_user.first_name
            username = update.message.from_user.username
            username_text = f"(@{username})" if username else "❌No username"

            with sqlite3.connect('data.db') as connection:
                cursor = connection.cursor()
                
                cursor.execute("SELECT user_id FROM users WHERE admin_type = 1")
                admins = [row[0] for row in cursor.fetchall()]
                
                for admin_id in admins:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=f"💠پیامی از {sender_name} {username_text}:\n\n{message}"
                    )
                        
                await update.message.reply_text(
                    "✅پیامت برای پشتیبانی ارسال شد\nدر صورت نیاز پاسخ میدن👌",
                    reply_markup=inline_markup
                )

            del user_support_progress[user_id]
            return

        elif download_spotify_result:
            if re.match(pattern, text) is not None:
                spotify_url = update.message.text.strip()
                await update.message.reply_text("💠 در حال پردازش لینک...")
                
                track_name, artist_name, album_name, release_date, cover_image = get_spotify_track_info(spotify_url)
                query = f"{track_name} {artist_name}"
                
                with sqlite3.connect("data.db") as conn:
                    cursor = conn.cursor()
                    cursor.execute('UPDATE download_spotify_progress SET step = ?, query = ?, spotify_url = ? WHERE user_id = ?', (2, query, spotify_url, user_id))
                    conn.commit()
                
                caption = (
                    f"🎵 آهنگ: {track_name}\n"
                    f"🎤 هنرمند: {artist_name}\n"
                    f"💿 آلبوم: {album_name}\n"
                    f'🔗 <a href="{spotify_url}">لینک آهنگ</a>\n'
                    f"📅 تاریخ انتشار: {release_date}\n\n"
                    "💠در صورت دانلود آهنگ 2 سکه از حساب شما کم میشود! آیا می‌خواهید این آهنگ را دانلود کنید؟"
                )

                keyboard = [
                    [InlineKeyboardButton("✅ بله", callback_data="confirm_download_spotify")],
                    [InlineKeyboardButton("❌ خیر", callback_data="cancel_download_spotify")]
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
                    text="⚠ لینک ارسال شده اشتباه است! لطفا دوباره مراحل را طی کنید...",
                    reply_to_message_id=update.effective_message.id,
                    reply_markup=inline_markup
                )

                with sqlite3.connect("data.db") as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM download_spotify_progress WHERE user_id = ?", (user_id,))
                    conn.commit()
                return
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
            return

async def handle_confirmation(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    with sqlite3.connect("data.db") as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT step FROM download_spotify_progress WHERE user_id = {user_id}")
        download_spotify_result = cursor.fetchone()

    if query.data == "confirm_download_spotify":
        if download_spotify_result:
            await context.bot.send_message(
                chat_id=user_id,
                text="💠در حال دانلود آهنگ...",
                reply_to_message_id=query.message.message_id
            )

            with sqlite3.connect("data.db") as conn:
                cursor = conn.cursor()
                cursor.execute(f"SELECT * FROM download_spotify_progress WHERE user_id = ?", (user_id,))
                download_spotify_progress = cursor.fetchone()
                download_spotify_progress = list(download_spotify_progress)
                print(f"\n\nline 464: user_id= {download_spotify_progress[0]}\nstep= {download_spotify_progress[1]}\nqury= {download_spotify_progress[2]}\n url= {download_spotify_progress[3]}\n\n")
            
            try:
                query_text = download_spotify_progress[2]
                file_path = download_from_youtube(query_text)
                
                await context.bot.send_message(
                    chat_id=user_id,
                    text="✅آهنگ با موفقیت دانلود شد👌\nدر حال ارسال فایل..."
                )
                
                # delete the coin in account 
                with sqlite3.connect("data.db") as conn:
                    cursor = conn.cursor()
                    #get the number of coins
                    cursor.execute('SELECT coins FROM users WHERE user_id = ?', (user_id,))
                    old_coins = cursor.fetchone()
                    new_coins = old_coins[0] - 2

                    #set the new number of coins
                    cursor.execute('UPDATE users SET coins = ? WHERE user_id = ?', (new_coins ,user_id,))
                    conn.commit()
            
                with open(file_path, 'rb') as audio_file:
                    await context.bot.send_audio(
                        chat_id=user_id,
                        audio=audio_file
                    )
                os.remove(file_path)

                with sqlite3.connect("data.db") as conn:
                    cursor = conn.cursor()
                    cursor.execute(f"DELETE FROM download_spotify_progress WHERE user_id = ?", (user_id,))
                    conn.commit()

                return
            
            except Exception as e:
                with sqlite3.connect("data.db") as conn:
                    cursor = conn.cursor()
                    cursor.execute('DELETE FROM download_spotify_progress WHERE user_id = ? AND EXISTS (SELECT 1 FROM download_spotify_progress WHERE user_id = ?)', (user_id, user_id))
                    conn.commit()
 
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
    
        else:
            keyboard = [
                [KeyboardButton("🔙 بازگشت 🔙")]
            ]
            inline_markup = ReplyKeyboardMarkup(keyboard)

            await context.bot.send_message(
                chat_id=user_id,
                text="⚠ مشکلی پیش آمده...\nلطفا دوباره تلاش کنید",
                reply_to_message_id=update.effective_message.id,
                reply_markup=inline_markup
            )
            return

    elif query.data == "cancel_download_spotify":
        if download_spotify_result:
            keyboard = [
                [KeyboardButton("🔙 بازگشت 🔙")]
            ]
            inline_markup = ReplyKeyboardMarkup(keyboard)
                    
            with sqlite3.connect("data.db") as conn:
                cursor = conn.cursor()
                cursor.execute(f"DELETE FROM download_spotify_progress WHERE user_id = ?", (user_id,))
                conn.commit()

            await context.bot.send_message(
                chat_id=user_id,
                text="✅ درخواست شما برای دانلود لغو شد. اگر می‌خواهید دوباره امتحان کنید، لطفاً لینک جدیدی ارسال کنید...",
                reply_markup=inline_markup,
                reply_to_message_id=query.message.message_id
            )
        
        else:
            keyboard = [
                [KeyboardButton("🔙 بازگشت 🔙")]
            ]
            inline_markup = ReplyKeyboardMarkup(keyboard)

            await context.bot.send_message(
                chat_id=user_id,
                text="⚠ این درخواست قبلاً پردازش شده است و دیگر معتبر نیست. لطفاً دوباره مراحل را طی کنید...",
                reply_markup=inline_markup,
                reply_to_message_id=query.message.message_id
            )            

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
    auth_db()
    main()