import sys
sys.stdout.reconfigure(encoding='utf-8')

from bs4 import BeautifulSoup
import traceback
from fuzzywuzzy import fuzz
import requests
import instaloader
import subprocess
import glob
import shutil
import asyncio
import re
import yt_dlp
import os
import json
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ChatMember
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler, JobQueue
import sqlite3
from telegram.error import TimedOut, Forbidden
from time import sleep
from datetime import datetime, timedelta
import qrcode 
import cv2
from pyzbar.pyzbar import decode
from googletrans import Translator

import pytz
tehran_tz = pytz.timezone('Asia/Tehran')   

translator = Translator()

# select token
with open('config.json', 'r', encoding='utf-8') as config_file:
    config = json.load(config_file)
TOKEN = config["api1"]["token"]
SPOTIPY_CLIENT_ID = config["client_spotify"]["client_id"]
SPOTIPY_CLIENT_SECRET = config["client_spotify"]["client_secret"]
max_leng_cap = config["max_len_capt"]
dev_user_id = config["dev_user_id"]

loader = instaloader.Instaloader(
    download_pictures=config["insta_loader_opt"]["download_pictures"],
    download_videos=config["insta_loader_opt"]["download_videos"],
    download_comments=config["insta_loader_opt"]["download_comments"],
    save_metadata=config["insta_loader_opt"]["save_metadata"]
)

user_support_progress = {}
MAX_FILE_SIZE = 50 * 1024 * 1024
DOWNLOADS_DIR = "downloads"

# --- DataBase ---
def auth_db():
    with sqlite3.connect('data.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users(
            user_id TEXT NOT NULL PRIMARY KEY,
            name TEXT,
            username TEXT,
            admin_type INTEGER,
            last_dice_time TEXT,
            coins INTEGER,
            referrer_id TEXT
        )''')
        conn.commit()
    print("[BOT] database checked✅")

def get_soundcloud_track_info(soundcloud_url):
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(soundcloud_url, download=False)
        
        track_name = info_dict.get('title', 'Unknown Title')
        artist_name = info_dict.get('uploader', 'Unknown Artist')
        album_name = info_dict.get('album', 'Unknown Album')
        release_date = info_dict.get('release_date', 'Unknown Date')
        cover_image = info_dict.get('thumbnail', None)

        return track_name, artist_name, album_name, release_date, cover_image

def get_spotify_track_info(spotify_single_url):
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET))
    track_id = spotify_single_url.split("/")[-1].split("?")[0]
    track_info = sp.track(track_id)
    track_name = track_info["name"]
    artist_name = track_info["artists"][0]["name"]
    album_name = track_info["album"]["name"]
    release_date = track_info["album"]["release_date"]
    cover_image = track_info["album"]["images"][0]["url"]
    
    return track_name, artist_name, album_name, release_date, cover_image

def get_playlist_info(playlist_url, client_id, client_secret):
    if "open.spotify.com/playlist/" not in playlist_url:
        raise ValueError("❌ لینک ارسال شده اشتباه است! لطفاً یک لینک معتبر از اسپاتیفای ارسال کنید.")
    
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=client_id, client_secret=client_secret))
    playlist_id = playlist_url.split('/')[-1].split('?')[0]
    playlist_info = sp.playlist(playlist_id)
    
    playlist_name = playlist_info['name']
    playlist_owner = playlist_info['owner']['display_name']
    playlist_image = playlist_info['images'][0]['url'] if playlist_info['images'] else None
    track_count = playlist_info['tracks']['total']
    
    return playlist_id, playlist_name, playlist_owner, playlist_image, track_count

def get_playlist_tracks(playlist_id, client_id, client_secret):
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=client_id, client_secret=client_secret))
    results = sp.playlist_tracks(playlist_id)
    tracks = []
    for item in results['items']:
        track = item['track']
        track_name = track['name']
        artist_name = track['artists'][0]['name']
        tracks.append(f"{track_name} {artist_name}")
    return tracks

def download_playlist(query, output_path="downloads/"):
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
        'quiet': False,
        'noplaylist': True
    }
    
    with yt_dlp.YoutubeDL(options) as ydl:
        try:
            search_results = ydl.extract_info(f"ytsearch:{query}", download=False)
            if 'entries' in search_results and search_results['entries']:
                best_match = search_results['entries'][0]
                ydl.download([best_match['webpage_url']])
                return f"{output_path}{best_match['title']}.mp3"
            else:
                print(f"⚠ آهنگ '{query}' یافت نشد.")
        except Exception as e:
            print(f"خطا در دانلود {query}: {str(e)}")

def download_from_spotify(query, output_path="downloads/"):
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

def download_from_soundcloud(query, output_path="downloads/"):
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
            search_results = ydl.extract_info(f"ytsearch:{query}", download=False)

            if 'entries' in search_results and len(search_results['entries']) > 0:
                best_match = None
                highest_similarity = 0
                
                for entry in search_results['entries']:
                    title = entry['title'].lower()
                    similarity_score = fuzz.partial_ratio(query.lower(), title)
                    
                    if similarity_score > highest_similarity:
                        highest_similarity = similarity_score
                        best_match = entry

                if best_match and highest_similarity > 50:
                    download_path = f"{output_path}{best_match['title']}.mp3"
                    ydl.download([best_match['webpage_url']])
                    return download_path
                else:
                    raise Exception("⚠️ هیچ آهنگی یافت نشد :(")
            else:
                raise Exception("⚠ متاسفیم... آهنگ مورد نظر شما یافت نشد :(")

        except Exception as e:
            raise Exception(f"خطا در دانلود: {str(e)}")

async def check_user_in_channel(user_id: int, chat_id: str, context: CallbackContext) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        return member.status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.OWNER]
    
    except Exception as e:
        print(f"\nError checking user membership: {e}\n\n")
        return False

def get_audio_info(url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'cookiefile': 'cookies.txt',
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=False)  # فقط اطلاعات بدون دانلود
        title = info_dict.get('title', 'downloaded_video')  # گرفتن عنوان ویدیو
        filesize = info_dict.get('filesize', 0)  # دریافت حجم فایل
        return title, filesize

def convert_to_mp3(input_file, title):
    output_file = os.path.join(DOWNLOADS_DIR, f"{title}.mp3")
    subprocess.run(["ffmpeg", "-i", input_file, "-b:a", "128k", "-y", output_file], 
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output_file

async def start(update: Update, context: CallbackContext) -> None:
    user_id = str(update.effective_user.id)
    user_name = update.effective_user.full_name
    username = update.effective_user.username

    # check channels
    required_channels = config["channels"]
    not_joined_channels = []

    for channel in required_channels:
        if not await check_user_in_channel(user_id, channel, context):
            not_joined_channels.append(channel)

    if not_joined_channels:
        keyboard = [
            [InlineKeyboardButton(text=f"🔗 {channel}", url=f"https://t.me/{channel[1:]}")]
            for channel in not_joined_channels
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        message = (
            "⚠️ برای استفاده از ربات، لطفاً ابتدا عضو کانال‌های زیر شوید:\n\n"
            "پس از عضویت، دوباره پیام بفرستید."
        )
        await context.bot.send_message(
            chat_id=user_id,
            text=message,
            reply_markup=reply_markup
        )
        return

    # check new user
    with sqlite3.connect("data.db") as conn:
        cursor  = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        user_status = cursor.fetchone()

        if user_status:
            None
        else:
            cursor.execute("INSERT INTO users (user_id, name, username, admin_type, coins) VALUES (?, ?, ?, ?, ?)", (user_id, user_name, username, 0, config["new_user_coin"]))
            conn.commit()

            await context.bot.send_message(
                chat_id=dev_user_id,
                text=f"✨ کاربر جدیدی در ربات ثبت نام کرد!\n\nنام: {user_name}\nنام کاربری: {username}\nیوزر آیدی: {user_id}"
            )

    # Check referral link
    if context.args and len(context.args) > 0:
        referrer_id = context.args[0]
        with sqlite3.connect("data.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(user_id) FROM users WHERE user_id = ?",(referrer_id,))
            check_user = cursor.fetchone()[0]

        if check_user == 1:
            referrer_id = None

        # Prevent self-referral
        if referrer_id and referrer_id != user_id:
            with sqlite3.connect("data.db") as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (referrer_id,))
                if cursor.fetchone():  # Check if referrer exists
                    cursor.execute("UPDATE users SET referrer_id = ? WHERE user_id = ?", (referrer_id, user_id))
                    conn.commit()

                    # Reward both users
                    cursor.execute("UPDATE users SET coins = coins + 10 WHERE user_id = ?", (user_id,))
                    conn.commit()
                    cursor.execute("UPDATE users SET coins = coins + 15 WHERE user_id = ?", (referrer_id,))
                    conn.commit()

                    await context.bot.send_message(
                        chat_id=referrer_id,
                        text=f"🎉 کاربر {user_name} (@{username}) با لینک دعوت شما وارد ربات شد."
                    )

    keyboard = [
        [KeyboardButton("📥 دانـلودر 📥"), KeyboardButton("💵 قیمت ارز 💵")],
        [KeyboardButton("🔳 QR Code 🔳"), KeyboardButton("🌐 مترجم متنی 🌐")],
        [KeyboardButton("📊 حساب کاربری 📊"), KeyboardButton("💰 افزایش سکه 💰")],
        [KeyboardButton("👨‍💻راهنما و پشتیبانی 👨‍💻")]
    ]

    # check user
    with sqlite3.connect("data.db") as conn:
        cursor  = conn.cursor()
        cursor.execute("SELECT admin_type FROM users WHERE user_id = ?", (user_id,))
        admin_type = cursor.fetchone()

    if int(admin_type[0]) == 1:
        keyboard.extend([
            [KeyboardButton("🛑 پنل ادمین 🛑")],
            [KeyboardButton("پیام به همه"), KeyboardButton("پیام به کاربر")],
            [KeyboardButton("تعداد کاربران")],
            [KeyboardButton("کاهش سکه"), KeyboardButton("افزایش سکه")],
            [KeyboardButton("دریافت دیتابیس"), KeyboardButton("اطلاعات کاربر")]
        ])

    inline_markup = ReplyKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=user_id,
        text=f"سلام {user_name} عزیز✨\n\n✨به ربات خوش اومدی\n💎برای ادامه کار میتونی از گزینه های زیر استفاده کنی...",
        reply_to_message_id=update.effective_message.id,
        reply_markup=inline_markup
    )
    return

async def help(update: Update, context: CallbackContext) -> None:
    None

async def echo(update: Update, context: CallbackContext) -> None:
    user_id = str(update.effective_user.id)
    text = update.message.text
    spotify_single_pattern = r'https?://open\.spotify\.com/(track|artist)/[a-zA-Z0-9]+'
    spotify_playlist_pattern = r'https?://open\.spotify\.com/(playlist)/[a-zA-Z0-9]+'
    soudncloud_pattern = r'https?://(www\.)?soundcloud\.com/[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+(\?.*)?'
    
    # check channels
    required_channels = config["channels"]
    not_joined_channels = []

    for channel in required_channels:
        if not await check_user_in_channel(user_id, channel, context):
            not_joined_channels.append(channel)

    if not_joined_channels:
        keyboard = [
            [InlineKeyboardButton(text=f"🔗 {channel}", url=f"https://t.me/{channel[1:]}")]
            for channel in not_joined_channels
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        message = (
            "⚠️ برای استفاده از ربات، لطفاً ابتدا عضو کانال‌های زیر شوید:\n\n"
            "پس از عضویت، دوباره پیام بفرستید."
        )
        await context.bot.send_message(
            chat_id=user_id,
            text=message,
            reply_markup=reply_markup
        )
        return
    
    
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

    elif text == "🌐 مترجم متنی 🌐":
        keyboard = [
            [KeyboardButton("🇬🇧 انگلیسی"), KeyboardButton("🇪🇸 اسپانیایی"), KeyboardButton("🇮🇷 فارسی")],
            [KeyboardButton("🇷🇺 روسی"), KeyboardButton("🇸🇦 عربی"), KeyboardButton("🇩🇪 آلمانی")],
            [KeyboardButton("🇮🇹 ایتالیایی"), KeyboardButton("🇹🇷 ترکی"), KeyboardButton("🇯🇵 ژاپنی")],
            [KeyboardButton("🔙 بازگشت 🔙")]
        ]
        inline_markup = ReplyKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=user_id,
            text="💠 لطفاً زبان مقصد برای ترجمه را از لیست زیر انتخاب کنید:",
            reply_markup=inline_markup
        )
        return
        
    elif text == "🇮🇷 فارسی":
        keyboard = [
            [KeyboardButton("❌ لغو ❌")]
        ]
        inline_markup = ReplyKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=user_id,
            text="💠 متنی که می‌خواهید به فارسی ترجمه شود را ارسال کنید:",
            reply_markup=inline_markup
        )

        context.user_data["trans_to_fa"] = True
        return

    elif text == "🇪🇸 اسپانیایی":
        keyboard = [
            [KeyboardButton("❌ لغو ❌")]
        ]
        inline_markup = ReplyKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=user_id,
            text="💠 متنی که می‌خواهید به اسپانیایی ترجمه شود را ارسال کنید:",
            reply_markup=inline_markup
        )

        context.user_data["trans_to_es"] = True
        return

    elif text == "🇬🇧 انگلیسی":
        keyboard = [
            [KeyboardButton("❌ لغو ❌")]
        ]
        inline_markup = ReplyKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=user_id,
            text="💠 متنی که می‌خواهید به انگلیسی ترجمه شود را ارسال کنید:",
            reply_markup=inline_markup
        )

        context.user_data["trans_to_en"] = True
        return

    elif text == "🇩🇪 آلمانی":
        keyboard = [
            [KeyboardButton("❌ لغو ❌")]
        ]
        inline_markup = ReplyKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=user_id,
            text="💠 متنی که می‌خواهید به آلمانی ترجمه شود را ارسال کنید:",
            reply_markup=inline_markup
        )

        context.user_data["trans_to_de"] = True
        return

    elif text == "🇸🇦 عربی":
        keyboard = [
            [KeyboardButton("❌ لغو ❌")]
        ]
        inline_markup = ReplyKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=user_id,
            text="💠 متنی که می‌خواهید به عربی ترجمه شود را ارسال کنید:",
            reply_markup=inline_markup
        )

        context.user_data["trans_to_ar"] = True
        return

    elif text == "🇷🇺 روسی":
        keyboard = [
            [KeyboardButton("❌ لغو ❌")]
        ]
        inline_markup = ReplyKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=user_id,
            text="💠 متنی که می‌خواهید به روسی ترجمه شود را ارسال کنید:",
            reply_markup=inline_markup
        )

        context.user_data["trans_to_ru"] = True
        return

    elif text == "🇹🇷 ترکی":
        keyboard = [
            [KeyboardButton("❌ لغو ❌")]
        ]
        inline_markup = ReplyKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=user_id,
            text="💠 متنی که می‌خواهید به ترکی ترجمه شود را ارسال کنید:",
            reply_markup=inline_markup
        )

        context.user_data["trans_to_tr"] = True
        return
 
    elif text == "🇮🇹 ایتالیایی":
        keyboard = [
            [KeyboardButton("❌ لغو ❌")]
        ]
        inline_markup = ReplyKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=user_id,
            text="💠 متنی که می‌خواهید به ایتالیایی ترجمه شود را ارسال کنید:",
            reply_markup=inline_markup
        )

        context.user_data["trans_to_it"] = True
        return

    elif text == "🇯🇵 ژاپنی":
        keyboard = [
            [KeyboardButton("❌ لغو ❌")]
        ]
        inline_markup = ReplyKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=user_id,
            text="💠 متنی که می‌خواهید به ژاپنی ترجمه شود را ارسال کنید:",
            reply_markup=inline_markup
        )

        context.user_data["trans_to_jp"] = True
        return

    elif text == "🔳 QR Code 🔳":
        keyboard = [
            [KeyboardButton("📤 ساخت QR Code"), KeyboardButton("📥 خواندن QR Code")],
            [KeyboardButton("🔙 بازگشت 🔙")]
        ]
        inline_markup = ReplyKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=user_id,
            text="💠 لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
            reply_markup=inline_markup
        )
        return

    elif text == "📤 ساخت QR Code":
        keyboard = [
            [KeyboardButton("❌ لغو ❌")]
        ]
        inline_markup = ReplyKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=user_id,
            text="💠 لطفاً متنی که می‌خواهید به QR Code تبدیل شود را ارسال کنید:\n🔹 این متن می‌تواند لینک، شماره تماس، متن ساده یا هر اطلاعات دیگری باشد.\n🔸 مثال: https://example.com یا 09123456789",
            reply_markup=inline_markup
        )
        context.user_data["create_qr"] = True
        return

    elif text == "📥 خواندن QR Code":
        keyboard = [
            [KeyboardButton("❌ لغو ❌")]
        ]
        inline_markup = ReplyKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=user_id,
            text="💠لطفا عکس qrcode خود را بفرستید:",
            reply_markup=inline_markup
        )
        context.user_data["read_qr"] = True
        return

    elif text == "💰 افزایش سکه 💰":
        keyboard = [
            [KeyboardButton("🎲 تاس 🎲"), KeyboardButton("🔗 زیر مجموعه گیری 🔗")],
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

    elif text == "🔗 زیر مجموعه گیری 🔗":
        user_id = str(update.effective_user.id)
        bot_username = context.bot.username
        referral_link = f"https://t.me/{bot_username}?start={user_id}"
        
        await context.bot.send_message(
            chat_id=user_id,
            text=f"🔗 لینک دعوت شما:\n\n{referral_link}\n\nبا ارسال این لینک به دوستان خود، 15 سکه به حساب شما و 10 سکه به حساب دوستتان اضافه خواهد شد!",
        )
        return

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
            [KeyboardButton("🔴 (پست)اینستاگرام 🔴"), KeyboardButton("🔴 پینترست(عکس) 🔴")],
            [KeyboardButton("🟢 اسپاتیفای پلی لیست 🟢"), KeyboardButton("🟢 اسپاتیفای تکی 🟢")], 
            [KeyboardButton("🔴 یوتیوب 🔴"), KeyboardButton("🟠 ساوند کلاود 🟠")],
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

    elif text == "🟢 اسپاتیفای تکی 🟢":
        keyboard = [
            [KeyboardButton("❌ لغو ❌")]
        ]
        inline_markup = ReplyKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=user_id,
            text="💠لینک آهنگ مد نظر خود را بفرستید:",
            reply_to_message_id=update.effective_message.id,
            reply_markup=inline_markup
        )

        context.user_data["spotify_single_step"] = 1
        return

    elif text == "🟢 اسپاتیفای پلی لیست 🟢":
        keyboard = [
            [KeyboardButton("❌ لغو ❌")]
        ]
        inline_markup = ReplyKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=user_id,
            text="💠لینک پلی لیست مد نظر خود را بفرستید:\n\n⚠ هر پلی لیست فقط تا 50 اهنگ دانلود میشود و سکه ها به تعداد آهنگ ها کم می شود!",
            reply_to_message_id=update.effective_message.id,
            reply_markup=inline_markup
        )

        context.user_data["spotify_playlist_step"] = 1
        return

    elif text == "🔴 (پست)اینستاگرام 🔴":
        keyboard = [
            [KeyboardButton("❌ لغو ❌")]
        ]
        inline_markup = ReplyKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=user_id,
            text="💠لینک پست را بفرستید:",
            reply_to_message_id=update.effective_message.id,
            reply_markup=inline_markup
        )    

        context.user_data["insta_post_step"] = 1
        return

    elif text == "🔴 پینترست(عکس) 🔴":
        keyboard = [
            [KeyboardButton("❌ لغو ❌")]
        ]
        inline_markup = ReplyKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=user_id,
            text="💠لینک عکس را بفرستید:",
            reply_to_message_id=update.effective_message.id,
            reply_markup=inline_markup
        )    

        context.user_data["pin_step"] = 1
        return
    
    elif text == "🟠 ساوند کلاود 🟠":
        keyboard = [
            [KeyboardButton("❌ لغو ❌")]
        ]
        inline_markup = ReplyKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=user_id,
            text="💠لینک آهنگ مد نظر خود را بفرستید:\n\n⚠ لینک اهنگ باید به این صورت باشد: https://soundcloud.com/...",
            reply_to_message_id=update.effective_message.id,
            reply_markup=inline_markup
        )

        context.user_data["soundcloud_step"] = 1
        return

    elif text == "🔴 یوتیوب 🔴":
        keyboard = [
            [KeyboardButton("❌ لغو ❌")]
        ]
        inline_markup = ReplyKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=user_id,
            text="💠لینک ویدیو را بفرستید:\n⚠ ترجیحا ویدیو های بالای 1 ساعت را نفرستید! بعد از ارسال لینک فایل صوتی آن برای شما ارسال می شود...",
            reply_to_message_id=update.effective_message.id,
            reply_markup=inline_markup
        )

        context.user_data["youtube_step"] = 1
        return

    elif text == "💵 قیمت ارز 💵":
        keyboard = [
            [KeyboardButton("💰 طلا 💰"), KeyboardButton("💵 واحد پولی 💵"), KeyboardButton("₿ رمزارز ₿")],
            [KeyboardButton("🔙 بازگشت 🔙")]
        ]
        inline_markup = ReplyKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=user_id,
            text="💠یکی از ارز های زیر را انتخاب کنید...",
            reply_to_message_id=update.effective_message.id,
            reply_markup=inline_markup
        )
        return

    elif text == "💰 طلا 💰":
        response = requests.get(config["api_currency"])

        if response.status_code == 200:
            keyboard = [
                [InlineKeyboardButton("قیمت ارز", callback_data="a"),
                InlineKeyboardButton("نام ارز", callback_data="a")]
            ]

            data = response.json()

            for item in data["gold"]:
                name_button = InlineKeyboardButton(item['name'],  callback_data="a")
                price_button = InlineKeyboardButton(f"{item['price']:,} تومان",  callback_data="a")

                keyboard.append([price_button, name_button])

            inline_markup = InlineKeyboardMarkup(keyboard)

            await context.bot.send_message(
                chat_id=user_id,
                text="💰 لیست قیمت‌های طلا:",
                reply_to_message_id=update.effective_message.id,
                reply_markup=inline_markup
            )
            return

        else:
            keyboard = [
                [KeyboardButton("🔙 بازگشت 🔙")]
            ]
            inline_markup = ReplyKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                chat_id=user_id,
                text="⚠ مشکلی پیش آمده!\nلطفا به پشتیبانی اطلاع دهید...",
                reply_to_message_id=update.effective_message.id,
                reply_markup=inline_markup
            )
            return

    elif text == "💵 واحد پولی 💵":
        response = requests.get(config["api_currency"])

        if response.status_code == 200:
            keyboard = [
                [InlineKeyboardButton("قیمت ارز", callback_data="a"),
                InlineKeyboardButton("نام ارز", callback_data="a")]
            ]

            data = response.json()

            for item in data["currency"]:
                name_button = InlineKeyboardButton(item['name'],  callback_data="a")
                price_button = InlineKeyboardButton(f"{item['price']:,} تومان",  callback_data="a")

                keyboard.append([price_button, name_button])

            inline_markup = InlineKeyboardMarkup(keyboard)

            await context.bot.send_message(
                chat_id=user_id,
                text="💵 لیست قیمت‌ واحد های پولی:",
                reply_to_message_id=update.effective_message.id,
                reply_markup=inline_markup
            )
            return
        else:
            keyboard = [
                [KeyboardButton("🔙 بازگشت 🔙")]
            ]
            
            inline_markup = ReplyKeyboardMarkup(keyboard)

            await context.bot.send_message(
                chat_id=user_id,
                text="⚠ مشکلی پیش آمده! لطفا به پشتیبانی اطلاع دهید...",
                reply_to_message_id=update.effective_message.id,
                reply_markup=inline_markup
            )
            return
        
    elif text == "₿ رمزارز ₿":
        response = requests.post(config["api_currency_digi"])

        popular_currencies = [
            "btc",   # بیت‌کوین
            "eth",   # اتریوم
            "bnb",   # بایننس کوین
            "xrp",   # ریپل
            "ada",   # کاردانو
            "sol",   # سولانا
            "doge",  # دوج‌کوین
            "ltc",   # لایت‌کوین
            "shib",  # شیبا اینو
            "trx",   # ترون
            "etc",   # اتریوم کلاسیک
        ]

        if response.status_code == 200:
            keyboard = [
                [InlineKeyboardButton("قیمت ارز", callback_data="a"),
                InlineKeyboardButton("نام ارز", callback_data="a")]
            ]

            data = response.json()

            markets = data.get("markets", {}).get("binance", {})

            for currency in popular_currencies:
                if currency in markets:
                    name_button = InlineKeyboardButton(currency,  callback_data="a")
                    price_button = InlineKeyboardButton(markets[currency],  callback_data="a")
                else:
                    name_button = InlineKeyboardButton(currency,  callback_data="a")
                    price_button = InlineKeyboardButton("یافت نشد",  callback_data="a")

                keyboard.append([price_button, name_button])

            inline_markup = InlineKeyboardMarkup(keyboard)

            await context.bot.send_message(
                chat_id=user_id,
                text="₿ لیست قیمت‌ رمزارز ها:",
                reply_to_message_id=update.effective_message.id,
                reply_markup=inline_markup
            )
            return
        else:
            keyboard = [
                [KeyboardButton("🔙 بازگشت 🔙")]
            ]

            await context.bot.send_message(
                chat_id=user_id,
                text="⚠ مشکلی پیش آمده! لطفا به پشتیبانی اطلاع دهید...",
                reply_to_message_id=update.effective_message.id,
                reply_markup=inline_markup
            )
            return

    elif text == "❌ لغو ❌":
        if "spotify_single_step" in context.user_data:
            del context.user_data["spotify_single_step"]
        if "spotify_single_query" in context.user_data:
            del context.user_data["spotify_single_query"]
        if "spotify_single_url" in context.user_data:
            del context.user_data["spotify_single_url"]

        if "pin_step" in context.user_data:
            del context.user_data["pin_step"]

        if "insta_post_url" in context.user_data:
            del context.user_data["insta_post_url"]
        if "insta_post_step" in context.user_data:
            del context.user_data["insta_post_step"]

        if "soundcloud_step" in context.user_data:
            del context.user_data["soundcloud_step"]
        if "soundcloud_query" in context.user_data:
            del context.user_data["soundcloud_query"]
        if "soundcloud_url" in context.user_data:
            del context.user_data["soundcloud_url"]

        if "coin_add_step" in context.user_data:
            del context.user_data["coin_add_step"]
        if "coin_add_user_id_dest" in context.user_data:
            del context.user_data["coin_add_user_id_dest"]
        if "add_num_coins" in context.user_data:
            del context.user_data["add_num_coins"]

        if "coin_remove_step" in context.user_data:
            del context.user_data["coin_remove_step"]
        if "coin_remove_user_id_dest" in context.user_data:
            del context.user_data["coin_remove_user_id_dest"]
        if "remove_num_coins" in context.user_data:
            del context.user_data["remove_num_coins"]

        if "create_qr" in context.user_data:
            del context.user_data["create_qr"]

        if "read_qr" in context.user_data:
            del context.user_data["read_qr"]

        if "msg_user_step" in context.user_data:
            del context.user_data["msg_user_step"]
        if "msg_user_id" in context.user_data:
            del context.user_data["msg_user_id"]
        if "txt_send_user" in context.user_data:
            del context.user_data["txt_send_user"]

        if "send_all_step" in context.user_data:
            del context.user_data["send_all_step"]
        if "send_all_txt" in context.user_data:
            del context.user_data["send_all_txt"]

        if user_id in user_support_progress:
            del user_support_progress[user_id]

        #translator
        if "trans_to_fa" in context.user_data:
            del context.user_data["trans_to_fa"]
        if "trans_to_es" in context.user_data:
            del context.user_data["trans_to_es"]
        if "trans_to_en" in context.user_data:
            del context.user_data["trans_to_en"]
        if "trans_to_de" in context.user_data:
            del context.user_data["trans_to_de"]
        if "trans_to_ar" in context.user_data:
            del context.user_data["trans_to_ar"]
        if "trans_to_ru" in context.user_data:
            del context.user_data["trans_to_ru"]
        if "trans_to_tr" in context.user_data:
            del context.user_data["trans_to_tr"]
        if "trans_to_it" in context.user_data:
            del context.user_data["trans_to_it"]
        if "trans_to_jp" in context.user_data:
            del context.user_data["trans_to_jp"]

        await start(update, context)
        return
    
    elif text == "🛑 پنل ادمین 🛑":
        None
        return

    #admin 
    elif text == "پیام به همه":
        #check admin
        with sqlite3.connect("data.db") as conn:
            cursor  = conn.cursor()
            cursor.execute("SELECT admin_type FROM users WHERE user_id = ?", (user_id,))
            admin_type = cursor.fetchone()

        if int(admin_type[0]) != 1:
            None

        keyboard = [
            [KeyboardButton("❌ لغو ❌")]
        ]
        inline_markup = ReplyKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=user_id,
            text="🤖 متن پیام را ارسال کنید:",
            reply_to_message_id=update.effective_message.id,
            reply_markup=inline_markup
        )
        context.user_data["send_all_step"] = 1
        return

    elif text == "تعداد کاربران":
        #check admin
        with sqlite3.connect("data.db") as conn:
            cursor  = conn.cursor()
            cursor.execute("SELECT admin_type FROM users WHERE user_id = ?", (user_id,))
            admin_type = cursor.fetchone()

        if int(admin_type[0]) != 1:
            None

        keyboard = [
            [KeyboardButton("❌ لغو ❌")]
        ]
        inline_markup = ReplyKeyboardMarkup(keyboard)

        with sqlite3.connect("data.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            num_users = cursor.fetchone()[0]

        await context.bot.send_message(
            chat_id=user_id,
            text=f"🤖 تعداد کاربران ربات تا الان: {num_users} نفر 📊",
            reply_to_message_id=update.effective_message.id,
            reply_markup=inline_markup
        )
        return

    elif text == "افزایش سکه":
        #check admin
        with sqlite3.connect("data.db") as conn:
            cursor  = conn.cursor()
            cursor.execute("SELECT admin_type FROM users WHERE user_id = ?", (user_id,))
            admin_type = cursor.fetchone()

        if int(admin_type[0]) != 1:
            None

        keyboard = [
            [KeyboardButton("❌ لغو ❌")]
        ]
        inline_markup = ReplyKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=user_id,
            text="🤖 شناسه عددی کاربر مد نظر را وارد کنید:",
            reply_to_message_id=update.effective_message.id,
            reply_markup=inline_markup
        )
        context.user_data["coin_add_step"] = 1
        return

    elif text == "کاهش سکه":
        #check admin
        with sqlite3.connect("data.db") as conn:
            cursor  = conn.cursor()
            cursor.execute("SELECT admin_type FROM users WHERE user_id = ?", (user_id,))
            admin_type = cursor.fetchone()

        if int(admin_type[0]) != 1:
            None

        keyboard = [
            [KeyboardButton("❌ لغو ❌")]
        ]
        inline_markup = ReplyKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=user_id,
            text="🤖 شناسه عددی کاربر مد نظر را وارد کنید:",
            reply_to_message_id=update.effective_message.id,
            reply_markup=inline_markup
        )
        context.user_data["coin_remove_step"] = 1
        return

    elif text == "دریافت دیتابیس":
        with sqlite3.connect("data.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT admin_type FROM users WHERE user_id = ?", (user_id,))
            admin_type = cursor.fetchone()

        if int(admin_type[0]) != 1:
            return

        if os.path.exists("data.db"):
            await context.bot.send_document(
                chat_id=user_id,
                document=open("data.db", "rb"),
                filename="data.db",
                caption="📂 این فایل دیتابیس شماست."
            )
        else:
            await context.bot.send_message(
                chat_id=user_id,
                text="⚠ فایل دیتابیس یافت نشد!"
            )

    elif text == "اطلاعات کاربر":
        #check admin
        with sqlite3.connect("data.db") as conn:
            cursor  = conn.cursor()
            cursor.execute("SELECT admin_type FROM users WHERE user_id = ?", (user_id,))
            admin_type = cursor.fetchone()

        if int(admin_type[0]) != 1:
            None

        keyboard = [
            [KeyboardButton("❌ لغو ❌")]
        ]
        inline_markup = ReplyKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=user_id,
            text="🤖 شناسه عددی کاربر مد نظر را وارد کنید:",
            reply_to_message_id=update.effective_message.id,
            reply_markup=inline_markup
        )
        context.user_data["step_about_user"] = True
        return

    elif text == "پیام به کاربر":
        #check admin
        with sqlite3.connect("data.db") as conn:
            cursor  = conn.cursor()
            cursor.execute("SELECT admin_type FROM users WHERE user_id = ?", (user_id,))
            admin_type = cursor.fetchone()

        if int(admin_type[0]) != 1:
            None

        keyboard = [
            [KeyboardButton("❌ لغو ❌")]
        ]
        inline_markup = ReplyKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=user_id,
            text="🤖 یوزر آیدی کاربر را وارد کنید:",
            reply_to_message_id=update.effective_message.id,
            reply_markup=inline_markup
        )
        context.user_data["msg_user_step"] = 1
        return

    else:
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

        elif "spotify_single_step" in context.user_data:
            if re.match(spotify_single_pattern, text) is not None:
                spotify_single_url = update.message.text.strip()
                await update.message.reply_text("💠 در حال پردازش لینک...")
                
                track_name, artist_name, album_name, release_date, cover_image = get_spotify_track_info(spotify_single_url)
                query = f"{track_name} {artist_name}"

                context.user_data["spotify_single_step"] = 2
                context.user_data["spotify_single_query"] = query
                context.user_data["spotify_single_url"] = spotify_single_url
                
                caption = (
                    f"🎵 آهنگ: {track_name}\n"
                    f"🎤 هنرمند: {artist_name}\n"
                    f"💿 آلبوم: {album_name}\n"
                    f'🔗 <a href="{spotify_single_url}">لینک آهنگ</a>\n'
                    f"📅 تاریخ انتشار: {release_date}\n\n"
                    "💠در صورت دانلود آهنگ 2 سکه از حساب شما کم میشود! آیا می‌خواهید این آهنگ را دانلود کنید؟"
                )

                keyboard = [
                    [InlineKeyboardButton("✅ بله", callback_data="confirm_download_spotify_single")],
                    [InlineKeyboardButton("❌ خیر", callback_data="cancel_download_spotify_single")]
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

                if "spotify_single_step" in context.user_data:
                    del context.user_data["spotify_single_step"]
                if "spotify_single_query" in context.user_data:
                    del context.user_data["spotify_single_query"]
                if "spotify_single_url" in context.user_data:
                    del context.user_data["spotify_single_url"]

                return

        elif "spotify_playlist_step" in context.user_data:
            if re.match(spotify_playlist_pattern, text) is not None:
                spotify_playlist_url = update.message.text.strip()
                await update.message.reply_text("💠 در حال پردازش لینک...")
                
                playlist_id, playlist_name, playlist_owner, playlist_image, track_count = get_playlist_info(spotify_playlist_url, SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET)
                
                context.user_data["playlist_id"] = playlist_id
                context.user_data["playlist_track_count"] = track_count
            
                caption = (f"🎵 پلی‌لیست: {playlist_name}\n"
                   f"👤 ساخته‌شده توسط: {playlist_owner}\n"
                   f"🎶 تعداد آهنگ‌ها: {track_count}\n"
                   "\n✅ آیا می‌خواهید همه آهنگ‌های این پلی‌لیست را دانلود کنید؟"
                )
                
                keyboard = [
                    [InlineKeyboardButton("✅ بله", callback_data="confirm_download_spotify_playlist")],
                    [InlineKeyboardButton("❌ خیر", callback_data="cancel_download_spotify_playlist")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                        
                if playlist_image:
                    await update.message.reply_photo(photo=playlist_image, caption=caption, reply_markup=reply_markup)
                else:
                    await update.message.reply_text(text=caption, reply_markup=reply_markup)           
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

                if "spotify_playlist_step" in context.user_data:
                    del context.user_data["spotify_playlist_step"]
                if "spotify_playlist_query" in context.user_data:
                    del context.user_data["spotify_playlist_query"]
                if "spotify_playlist_url" in context.user_data:
                    del context.user_data["spotify_playlist_url"]

                return
            
        elif "pin_step" in context.user_data:
            if not any(substring in text for substring in ["pinterest.com/pin/", "pin.it/"]):
                await update.message.reply_text("❌ لطفاً یک لینک معتبر از پینترست ارسال کنید.")
                if "pin_step" in context.user_data:
                    del context.user_data["pin_step"]
                return

            pin_img_url = update.message.text.strip()
            await update.message.reply_text("💠 در حال پردازش لینک...")

            keyboard = [
                [InlineKeyboardButton("✅ بله", callback_data="confirm_download_pin")],
                [InlineKeyboardButton("❌ خیر", callback_data="cancel_download_pin")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            pin_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
                        
            response = requests.get(pin_img_url, headers=pin_headers)
            pin_soup = BeautifulSoup(response.text, "html.parser")
            pin_image_tag = pin_soup.find("meta", property="og:image")

            if pin_image_tag:
                context.user_data["pin_img_url"] = pin_image_tag["content"]
                await update.message.reply_text(
                    "💠در صورت دانلود این عکس 2 سکه از حساب شما کم میشود! آیا می‌خواهید این پست را دانلود کنید؟",
                    reply_markup=reply_markup,
                )
                return
            else:
                await update.message.reply_text(
                    "❌ متاسفانه عکسی برای دانلود پیدا نشد!",
                    reply_markup=reply_markup,
                )

                if "pin_step" in context.user_data:
                    del context.user_data["pin_step"]
                return

        elif "insta_post_step" in context.user_data:
            post_url = update.message.text

            try:
                shortcode = post_url.split("/")[-2]

                context.user_data["insta_post_url"] = shortcode

                keyboard = [
                    [InlineKeyboardButton("❌ خیر", callback_data="cancel_download_insta_post"), InlineKeyboardButton("✅ بله", callback_data="confirm_download_insta_post")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    "💠در صورت دانلود این پست 2 سکه از حساب شما کم میشود! آیا می‌خواهید این پست را دانلود کنید؟",
                    reply_markup=reply_markup,
                )
                return
            except Exception as e:
                await update.message.reply_text(f"خطا: {e}")
                
                if "insta_post_url" in context.user_data:
                    del context.user_data["insta_post_url"]
                if "insta_post_step" in context.user_data:
                    del context.user_data["insta_post_step"]
                return

        elif "soundcloud_step" in context.user_data:
            if re.match(soudncloud_pattern, text) is not None:
                soundcloud_url = update.message.text.strip()
                await update.message.reply_text("💠 در حال پردازش لینک...")
                
                track_name, artist_name, album_name, release_date, cover_image = get_soundcloud_track_info(soundcloud_url)
                query = f"{track_name} {artist_name}"

                context.user_data["soundcloud_step"] = 2
                context.user_data["soundcloud_query"] = query
                context.user_data["soundcloud_url"] = soundcloud_url
                
                caption = (
                    f"🎵 آهنگ: {track_name}\n"
                    f"🎤 هنرمند: {artist_name}\n"
                    f"💿 آلبوم: {album_name}\n"
                    f'🔗 <a href="{soundcloud_url}">لینک آهنگ</a>\n'
                    f"📅 تاریخ انتشار: {release_date}\n\n"
                    "💠در صورت دانلود آهنگ 2 سکه از حساب شما کم میشود! آیا می‌خواهید این آهنگ را دانلود کنید؟"
                )

                keyboard = [
                    [InlineKeyboardButton("✅ بله", callback_data="confirm_download_soundcloud")],
                    [InlineKeyboardButton("❌ خیر", callback_data="cancel_download_soundcloud")]
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

                if "soundcloud_step" in context.user_data:
                    del context.user_data["soundcloud_step"]
                if "soundcloud_query" in context.user_data:
                    del context.user_data["soundcloud_query"]
                if "soundcloud_url" in context.user_data:
                    del context.user_data["soundcloud_url"]

                return

        elif "youtube_step" in context.user_data:
            if any(substring in text for substring in ["youtube.com/", "youtu.be/"]):
                youtube_url = update.message.text

                keyboard = [
                    [InlineKeyboardButton("✅ بله", callback_data="confirm_download_youtube")],
                    [InlineKeyboardButton("❌ خیر", callback_data="cancel_download_youtube")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await context.bot.send_message(
                    chat_id=user_id,
                    text="در صورت دانلود آن 2 سکه از حساب شما کم میشود! آیا از اینکار مطمئن هستید؟",
                    reply_markup=reply_markup
                )
                context.user_data["youtube_url"] = youtube_url
                return
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

                if "youtube_step" in context.user_data:
                    del context.user_data["youtube_step"]
                return

        #translator
        elif "trans_to_fa" in context.user_data:
            fa_text = update.message.text
            keyboard = [
                [KeyboardButton("🔙 بازگشت 🔙")]
            ]
            inline_markup = ReplyKeyboardMarkup(keyboard)
            
            if len(fa_text) > 1:
                target_language = "fa"
                translated = await translator.translate(fa_text, dest=target_language)
                
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"✅ متن شما با موفقیت ترجمه شد:\n\n{translated.text}",
                    reply_markup=inline_markup
                )
            else:
                await update.message.reply_text("⚠ مشکلی پیش آمده! لطفا به پشتیبانی اطلاع دهید...\n\nERROR_TEXT: tra_fa")

            if "trans_to_fa" in context.user_data:
                del context.user_data["trans_to_fa"]
            return

        elif "trans_to_es" in context.user_data:
            es_text = update.message.text
            keyboard = [
                [KeyboardButton("🔙 بازگشت 🔙")]
            ]
            inline_markup = ReplyKeyboardMarkup(keyboard)
            
            if len(es_text) > 1:
                target_language = "es"
                translated = await translator.translate(es_text, dest=target_language)
                
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"✅ متن شما با موفقیت ترجمه شد:\n\n{translated.text}",
                    reply_markup=inline_markup
                )
            else:
                await update.message.reply_text("⚠ مشکلی پیش آمده! لطفا به پشتیبانی اطلاع دهید...\n\nERROR_TEXT: tra_es")

            if "trans_to_es" in context.user_data:
                del context.user_data["trans_to_es"]
            return

        elif "trans_to_en" in context.user_data:
            en_text = update.message.text
            keyboard = [
                [KeyboardButton("🔙 بازگشت 🔙")]
            ]
            inline_markup = ReplyKeyboardMarkup(keyboard)
            
            if len(en_text) > 1:
                target_language = "en"
                translated = await translator.translate(en_text, dest=target_language)
                
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"✅ متن شما با موفقیت ترجمه شد:\n\n{translated.text}",
                    reply_markup=inline_markup
                )
            else:
                await update.message.reply_text("⚠ مشکلی پیش آمده! لطفا به پشتیبانی اطلاع دهید...\n\nERROR_TEXT: tra_en")

            if "trans_to_en" in context.user_data:
                del context.user_data["trans_to_en"]
            return

        elif "trans_to_de" in context.user_data:
            de_text = update.message.text
            keyboard = [
                [KeyboardButton("🔙 بازگشت 🔙")]
            ]
            inline_markup = ReplyKeyboardMarkup(keyboard)
            
            if len(de_text) > 1:
                target_language = "de"
                translated = await translator.translate(de_text, dest=target_language)
                
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"✅ متن شما با موفقیت ترجمه شد:\n\n{translated.text}",
                    reply_markup=inline_markup
                )
            else:
                await update.message.reply_text("⚠ مشکلی پیش آمده! لطفا به پشتیبانی اطلاع دهید...\n\nERROR_TEXT: tra_de")

            if "trans_to_de" in context.user_data:
                del context.user_data["trans_to_de"]
            return

        elif "trans_to_ar" in context.user_data:
            ar_text = update.message.text
            keyboard = [
                [KeyboardButton("🔙 بازگشت 🔙")]
            ]
            inline_markup = ReplyKeyboardMarkup(keyboard)
            
            if len(ar_text) > 1:
                target_language = "ar"
                translated = await translator.translate(ar_text, dest=target_language)
                
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"✅ متن شما با موفقیت ترجمه شد:\n\n{translated.text}",
                    reply_markup=inline_markup
                )
            else:
                await update.message.reply_text("⚠ مشکلی پیش آمده! لطفا به پشتیبانی اطلاع دهید...\n\nERROR_TEXT: tra_ar")

            if "trans_to_ar" in context.user_data:
                del context.user_data["trans_to_ar"]
            return

        elif "trans_to_ru" in context.user_data:
            ru_text = update.message.text
            keyboard = [
                [KeyboardButton("🔙 بازگشت 🔙")]
            ]
            inline_markup = ReplyKeyboardMarkup(keyboard)
            
            if len(ru_text) > 1:
                target_language = "ru"
                translated = await translator.translate(ru_text, dest=target_language)
                
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"✅ متن شما با موفقیت ترجمه شد:\n\n{translated.text}",
                    reply_markup=inline_markup
                )
            else:
                await update.message.reply_text("⚠ مشکلی پیش آمده! لطفا به پشتیبانی اطلاع دهید...\n\nERROR_TEXT: tra_ru")

            if "trans_to_ru" in context.user_data:
                del context.user_data["trans_to_ru"]
            return

        elif "trans_to_tr" in context.user_data:
            tr_text = update.message.text
            keyboard = [
                [KeyboardButton("🔙 بازگشت 🔙")]
            ]
            inline_markup = ReplyKeyboardMarkup(keyboard)
            
            if len(tr_text) > 1:
                target_language = "tr"
                translated = await translator.translate(tr_text, dest=target_language)
                
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"✅ متن شما با موفقیت ترجمه شد:\n\n{translated.text}",
                    reply_markup=inline_markup
                )
            else:
                await update.message.reply_text("⚠ مشکلی پیش آمده! لطفا به پشتیبانی اطلاع دهید...\n\nERROR_TEXT: tra_tr")

            if "trans_to_tr" in context.user_data:
                del context.user_data["trans_to_tr"]
            return

        elif "trans_to_it" in context.user_data:
            it_text = update.message.text
            keyboard = [
                [KeyboardButton("🔙 بازگشت 🔙")]
            ]
            inline_markup = ReplyKeyboardMarkup(keyboard)
            
            if len(it_text) > 1:
                target_language = "it"
                translated = await translator.translate(it_text, dest=target_language)
                
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"✅ متن شما با موفقیت ترجمه شد:\n\n{translated.text}",
                    reply_markup=inline_markup
                )
            else:
                await update.message.reply_text("⚠ مشکلی پیش آمده! لطفا به پشتیبانی اطلاع دهید...\n\nERROR_TEXT: tra_it")

            if "trans_to_it" in context.user_data:
                del context.user_data["trans_to_it"]
            return

        elif "trans_to_jp" in context.user_data:
            jp_text = update.message.text
            keyboard = [
                [KeyboardButton("🔙 بازگشت 🔙")]
            ]
            inline_markup = ReplyKeyboardMarkup(keyboard)
            
            if len(jp_text) > 1:
                target_language = "ja"
                translated = await translator.translate(jp_text, dest=target_language)
                
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"✅ متن شما با موفقیت ترجمه شد:\n\n{translated.text}",
                    reply_markup=inline_markup
                )
            else:
                await update.message.reply_text("⚠ مشکلی پیش آمده! لطفا به پشتیبانی اطلاع دهید...\n\nERROR_TEXT: tra_jp")

            if "trans_to_jp" in context.user_data:
                del context.user_data["trans_to_jp"]
            return

        #admin
        elif context.user_data.get("msg_user_step") == 1:
            msg_user_id = update.message.text

            keyboard = [
                [KeyboardButton("❌ لغو ❌")]
            ]
            inline_markup = ReplyKeyboardMarkup(keyboard)

            if not msg_user_id.isdigit():
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❌ یوزر آیدی وارد شده معتبر نیست!",
                    reply_to_message_id=update.effective_message.id,
                    reply_markup=inline_markup
                )
                if "msg_user_step" in context.user_data:
                    context.user_data["msg_user_step"]
                return

            msg_user_id = int(msg_user_id)

            if msg_user_id < 1:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❌ یوزر آیدی وارد شده اشتباه است!",
                    reply_to_message_id=update.effective_message.id,
                    reply_markup=inline_markup
                )
                if "msg_user_step" in context.user_data:
                    context.user_data["msg_user_step"]
                return

            await context.bot.send_message(
                chat_id=user_id,
                text=f"پیام خود را بنویسید:",
                reply_markup=inline_markup
            )
            context.user_data["msg_user_id"] = msg_user_id
            context.user_data["msg_user_step"] = 2
            return

        elif context.user_data.get("msg_user_step") == 2:
            txt_send_user = update.message.text

            keyboard = [
                [KeyboardButton("❌ لغو ❌")]
            ]
            inline_markup = ReplyKeyboardMarkup(keyboard)

            keyboard = [
                [InlineKeyboardButton("✅ ارسال", callback_data="confirm_send_user")],
                [InlineKeyboardButton("❌ خیر", callback_data="cancel_send_user")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            with sqlite3.connect("data.db") as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name, username FROM users WHERE user_id = ?", (context.user_data.get("msg_user_id"),))
                msg_user_data = cursor.fetchone()
                msg_user_data = list(msg_user_data)

            if msg_user_data[1] is not None:
                msg_username = f"@{msg_user_data[1]}"
            else:
                msg_username = "No_username"

            await context.bot.send_message(
                chat_id=user_id,
                text=f"🤖 شما در حال ارسال پیام زیر به کاربر {msg_user_data[0]} با آیدی  {msg_username} و یوزر آیدی {context.user_data.get("msg_user_id")} هستید. اگر پیام را تایید میکنید روی ارسال کیلک کنید در غیر این صورت روی لغو کلیک کنید...\n\n📜 پیام شما:\n{txt_send_user}",
                reply_markup=reply_markup
            )
            context.user_data["msg_user_step"] = 3
            context.user_data["txt_send_user"] = txt_send_user
            return

        elif context.user_data.get("send_all_step"):
            send_all_txt = update.message.text

            keyboard = [
                [InlineKeyboardButton("✅ بله", callback_data="confirm_send_all")],
                [InlineKeyboardButton("❌ خیر", callback_data="cancel_send_all")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await context.bot.send_message(
                chat_id=user_id,
                text=f"🤖 شما در حال ارسال متن زیر برای همه کاربران ربات هستید! اگر از کار خود مطمئن هستید روی 'بله' کلیک کنید در غیر این صورت روی 'لغو' کلید کنید تا فرآیند شما لغو شود...\n\n📜 پیام شما:\n{send_all_txt}",
                reply_markup=reply_markup
            )
            context.user_data["send_all_txt"] = send_all_txt
            context.user_data["send_all_step"] = 2
            return            

        elif context.user_data.get("coin_add_step") == 1:
            user_id_dest = update.message.text

            keyboard = [
                [KeyboardButton("❌ لغو ❌")]
            ]
            inline_markup = ReplyKeyboardMarkup(keyboard)

            if not str(user_id_dest).isdigit():                
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❌ یوزر آیدی وارد شده اشتباه است!",
                    reply_to_message_id=update.effective_message.id,
                    reply_markup=inline_markup
                )
                if "coin_add_step" in context.user_data:
                    context.user_data["coin_add_step"]
                return

            if len(str(user_id_dest)) < 6:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❌ یوزر آیدی وارد شده معتبر نیست!",
                    reply_to_message_id=update.effective_message.id,
                    reply_markup=inline_markup
                )
                if "coin_add_step" in context.user_data:
                    context.user_data["coin_add_step"]
                return

            with sqlite3.connect("data.db") as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM users WHERE user_id = ?", (user_id_dest,))
                user_exists = cursor.fetchone()[0]

            if user_exists == 0:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❌ این کاربر در ربات ثبت نام نکرده است!",
                    reply_to_message_id=update.effective_message.id,
                    reply_markup=inline_markup
                )
                if "coin_add_step" in context.user_data:
                    context.user_data["coin_add_step"]
                return

            await context.bot.send_message(
                chat_id=user_id,
                text="🤖 تعداد سکه های مدنظر را وارد کنید:",
                reply_to_message_id=update.effective_message.id,
                reply_markup=inline_markup
            )
            context.user_data["coin_add_user_id_dest"] = user_id_dest
            context.user_data["coin_add_step"] = 2
            return

        elif context.user_data.get("coin_add_step") == 2:
            num_coins = update.message.text

            keyboard = [
                [KeyboardButton("❌ لغو ❌")]
            ]
            inline_markup = ReplyKeyboardMarkup(keyboard)

            if not num_coins.isdigit():
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❌ مقدار وارد شده اشتباه است!",
                    reply_to_message_id=update.effective_message.id,
                    reply_markup=inline_markup
                )
                if "coin_add_step" in context.user_data:
                    context.user_data["coin_add_step"]
                if "coin_add_user_id_dest" in context.user_data:
                    context.user_data["coin_add_user_id_dest"]
                return

            num_coins = int(num_coins)

            if num_coins < 1:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❌ مقدار وارد شده اشتباه است!",
                    reply_to_message_id=update.effective_message.id,
                    reply_markup=inline_markup
                )
                if "coin_add_step" in context.user_data:
                    context.user_data["coin_add_step"]
                if "coin_add_user_id_dest" in context.user_data:
                    context.user_data["coin_add_user_id_dest"]
                return

            keyboard = [
                [InlineKeyboardButton("✅ بله", callback_data="confirm_coin_add")],
                [InlineKeyboardButton("❌ خیر", callback_data="cancel_coin_add")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            with sqlite3.connect("data.db") as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE user_id = ?", (context.user_data.get("coin_add_user_id_dest"),))
                user_dest_data = cursor.fetchone()
                user_dest_data = list(user_dest_data)

            if user_dest_data[2] is not None:
                username_dest = f"@{user_dest_data[2]}"
            else:
                username_dest = "No_username"

            await context.bot.send_message(
                chat_id=user_id,
                text=f"⚠ شما مطمئن هستید میخواهید مقدار {num_coins} سکه به سکه های کاربر {user_dest_data[1]} با آیدی {username_dest} و یوزر آیدی {user_dest_data[0]} اضافه کنید؟",
                reply_markup=reply_markup
            )
            context.user_data["add_num_coins"] = num_coins
            return

        elif context.user_data.get("coin_remove_step") == 1:
            user_id_dest = update.message.text

            keyboard = [
                [KeyboardButton("❌ لغو ❌")]
            ]
            inline_markup = ReplyKeyboardMarkup(keyboard)

            if not str(user_id_dest).isdigit():                
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❌ یوزر آیدی وارد شده اشتباه است!",
                    reply_to_message_id=update.effective_message.id,
                    reply_markup=inline_markup
                )
                if "coin_remove_step" in context.user_data:
                    context.user_data["coin_remove_step"]
                return

            if len(str(user_id_dest)) < 6:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❌ یوزر آیدی وارد شده معتبر نیست!",
                    reply_to_message_id=update.effective_message.id,
                    reply_markup=inline_markup
                )
                if "coin_remove_step" in context.user_data:
                    context.user_data["coin_remove_step"]
                return

            with sqlite3.connect("data.db") as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM users WHERE user_id = ?", (user_id_dest,))
                user_exists = cursor.fetchone()[0]

            if user_exists == 0:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❌ این کاربر در ربات ثبت نام نکرده است!",
                    reply_to_message_id=update.effective_message.id,
                    reply_markup=inline_markup
                )
                if "coin_remove_step" in context.user_data:
                    context.user_data["coin_remove_step"]
                return

            await context.bot.send_message(
                chat_id=user_id,
                text="🤖 تعداد سکه های مدنظر را وارد کنید:",
                reply_to_message_id=update.effective_message.id,
                reply_markup=inline_markup
            )
            context.user_data["coin_remove_user_id_dest"] = user_id_dest
            context.user_data["coin_remove_step"] = 2
            return

        elif context.user_data.get("coin_remove_step") == 2:
            num_coins = update.message.text

            keyboard = [
                [KeyboardButton("❌ لغو ❌")]
            ]
            inline_markup = ReplyKeyboardMarkup(keyboard)

            if not num_coins.isdigit():
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❌ مقدار وارد شده اشتباه است!",
                    reply_to_message_id=update.effective_message.id,
                    reply_markup=inline_markup
                )
                if "coin_remove_step" in context.user_data:
                    context.user_data["coin_remove_step"]
                if "coin_remove_user_id_dest" in context.user_data:
                    context.user_data["coin_remove_user_id_dest"]
                return

            num_coins = int(num_coins)

            if num_coins < 1:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❌ مقدار وارد شده اشتباه است!",
                    reply_to_message_id=update.effective_message.id,
                    reply_markup=inline_markup
                )
                if "coin_remove_step" in context.user_data:
                    context.user_data["coin_remove_step"]
                if "coin_remove_user_id_dest" in context.user_data:
                    context.user_data["coin_remove_user_id_dest"]
                return

            keyboard = [
                [InlineKeyboardButton("✅ بله", callback_data="confirm_coin_remove")],
                [InlineKeyboardButton("❌ خیر", callback_data="cancel_coin_remove")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            with sqlite3.connect("data.db") as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE user_id = ?", (context.user_data.get("coin_remove_user_id_dest"),))
                user_dest_data = cursor.fetchone()
                user_dest_data = list(user_dest_data)

            if user_dest_data[2] is not None:
                username_dest = f"@{user_dest_data[2]}"
            else:
                username_dest = "No_username"

            await context.bot.send_message(
                chat_id=user_id,
                text=f"⚠ شما مطمئن هستید میخواهید مقدار {num_coins} سکه از سکه های کاربر {user_dest_data[1]} با آیدی {username_dest} و یوزر آیدی {user_dest_data[0]} کم کنید؟",
                reply_markup=reply_markup
            )
            context.user_data["remove_num_coins"] = num_coins
            return

        elif context.user_data.get("step_about_user") == True:
            about_user_id = update.message.text
            
            keyboard = [
                [KeyboardButton("🔙 بازگشت 🔙")]
            ]
            inline_markup = ReplyKeyboardMarkup(keyboard)

            if not str(about_user_id).isdigit():                
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❌ یوزر آیدی وارد شده اشتباه است!",
                    reply_to_message_id=update.effective_message.id,
                    reply_markup=inline_markup
                )
                if "step_about_user" in context.user_data:
                    context.user_data["step_about_user"]
                return

            if len(str(about_user_id)) < 6:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❌ یوزر آیدی وارد شده معتبر نیست!",
                    reply_to_message_id=update.effective_message.id,
                    reply_markup=inline_markup
                )
                if "step_about_user" in context.user_data:
                    context.user_data["step_about_user"]
                return

            with sqlite3.connect("data.db") as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM users WHERE user_id = ?", (about_user_id,))
                user_exists = cursor.fetchone()[0]

            if user_exists == 0:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❌ این کاربر در ربات ثبت نام نکرده است!",
                    reply_to_message_id=update.effective_message.id,
                    reply_markup=inline_markup
                )
                if "step_about_user" in context.user_data:
                    context.user_data["step_about_user"]
                return

            with sqlite3.connect("data.db") as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE user_id = ?", (about_user_id,))
                about_user_data = cursor.fetchone()
                
            if about_user_data:
                if about_user_data[3] == 1:
                    user_type = "ادمین"
                else:
                    user_type = "کاربر عادی"

                user_name = about_user_data[1]
                username = about_user_data[2]
                coins = about_user_data[5]

                inline_keyboard = [[InlineKeyboardButton(f"⭐ نوع حساب:  {user_type}", callback_data="no_action")]]
                inline_markup = InlineKeyboardMarkup(inline_keyboard)

                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"🔆 اطلاعات حساب:\n\n💠 نام: {user_name}\n💠 نام کاربری: @{username}\n💠 شناسه عددی: {user_id}\n💰 تعداد سکه ها: {coins}",
                    reply_to_message_id=update.effective_message.id,
                    reply_markup=inline_markup
                )

                if "step_about_user" in context.user_data:
                    del context.user_data["step_about_user"]
                return

        elif context.user_data.get("create_qr") == True:
            qrcode_text = " ".join(update.message.text)

            keyboard = [
                [KeyboardButton("🔙 بازگشت 🔙")]
            ]
            inline_markup = ReplyKeyboardMarkup(keyboard)

            #check length text
            if len(qrcode_text) > config["max_txt_qrcode"]:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❌ متن شما خیلی طولانی است! لطفاً متنی کوتاه‌ تر ارسال کنید.!",
                    reply_to_message_id=update.effective_message.id,
                    reply_markup=inline_markup
                )
                if "create_qr" in context.user_data:
                    del context.user_data["create_qr"]
                return
            
            qr = qrcode.make(qrcode_text)
            qr_path = f"qr_{user_id}.png"
            qr.save(qr_path)

            await update.message.reply_photo(
                photo=open(qr_path, "rb"), 
                caption="✅ این هم QR Code شما!"
            )
            os.remove(qr_path)

            if "create_qr" in context.user_data:
                del context.user_data["create_qr"]
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

async def echo_photo(update: Update, context: CallbackContext) -> None:
    user_id = str(update.effective_user.id)
    
    # check channels
    required_channels = config["channels"]
    not_joined_channels = []

    for channel in required_channels:
        if not await check_user_in_channel(user_id, channel, context):
            not_joined_channels.append(channel)

    if not_joined_channels:
        keyboard = [
            [InlineKeyboardButton(text=f"🔗 {channel}", url=f"https://t.me/{channel[1:]}")]
            for channel in not_joined_channels
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        message = (
            "⚠️ برای استفاده از ربات، لطفاً ابتدا عضو کانال‌های زیر شوید:\n\n"
            "پس از عضویت، دوباره پیام بفرستید."
        )
        await context.bot.send_message(
            chat_id=user_id,
            text=message,
            reply_markup=reply_markup
        )
        return
    

    if context.user_data.get("read_qr") == True:
        keyboard = [
            [KeyboardButton("🔙 بازگشت 🔙")]
        ]
        inline_markup = ReplyKeyboardMarkup(keyboard)

        await update.message.reply_text("📸 در حال خواندن QR Code...")
        
        file = await update.message.photo[-1].get_file()
        qr_path = f"qr_scan_{user_id}.png"
        await file.download_to_drive(qr_path)

        image = cv2.imread(qr_path)
        qr_codes = decode(image)

        if not qr_codes:
            await context.bot.send_message(
                chat_id=user_id,
                text="❌ هیچ qrcode ای در تصویر یافت نشد!",
                reply_markup=inline_markup
            )
            os.remove(qr_path)
            if "read_qr" in context.user_data:
                del context.user_data["read_qr"]
            return
        
        result_qrcode = "\n".join([qr.data.decode() for qr in qr_codes])
        result_qrcode = result_qrcode.replace(" ", "")

        await context.bot.send_message(
            chat_id=user_id,
            text=f"📄 محتوای QR:\n`{result_qrcode}`",
            reply_markup=inline_markup,
            parse_mode="Markdown"
        )

        os.remove(qr_path)
        
        if "read_qr" in context.user_data:
            del context.user_data["read_qr"]
        return

async def handle_confirmation(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == "confirm_download_spotify_single":
        if "spotify_single_step" in context.user_data:
            await query.edit_message_caption(
                caption="🎧 در حال دانلود آهنگ..."
            )

            query_text = context.user_data.get("spotify_single_query")
            file_path = download_from_spotify(query_text)
            
            # delete the coin in account 
            with sqlite3.connect("data.db") as conn:
                cursor = conn.cursor()
                #get the number of coins
                cursor.execute('SELECT coins FROM users WHERE user_id = ?', (user_id,))
                old_coins = cursor.fetchone()

                if old_coins[0]-2 >= 0:
                    new_coins = old_coins[0] - 2
                    #set the new number of coins
                    cursor.execute('UPDATE users SET coins = ? WHERE user_id = ?', (new_coins ,user_id,))
                    conn.commit()
                else:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text="⚠ سکه های شما کافی نمیباشد!\nشما میتوانید از طریق بخش افزایش سکه تعداد سکه های خود را افزایش دهید...",
                    )
                    if "spotify_single_step" in context.user_data:
                        del context.user_data["spotify_single_step"]
                    if "spotify_single_query" in context.user_data:
                        del context.user_data["spotify_single_query"]
                    if "spotify_single_url" in context.user_data:
                        del context.user_data["spotify_single_url"]

                    return
        
            await context.bot.send_message(
                chat_id=user_id,
                text="✅ آهنگ با موفقیت دانلود شد👌\nدر حال ارسال فایل..."
            )

            caption = (
                f'<a href="https://t.me/Megaa_helperbot">@megaa_helperbot</a> | <a href="{context.user_data.get("spotify_single_url")}">Music link</a>'
            )

            #send to channel
            bot = context.bot
            with open(file_path, 'rb') as audio_file:
                await bot.send_audio(
                    chat_id=config["channels"][0],
                    audio=audio_file,
                    caption=caption,
                    parse_mode="HTML"
                )

            #send to user
            with open(file_path, 'rb') as audio_file:
                await context.bot.send_audio(
                    chat_id=user_id,
                    audio=audio_file,
                    caption=caption,
                    parse_mode="HTML"
                )

            os.remove(file_path)

            if "spotify_single_step" in context.user_data:
                del context.user_data["spotify_single_step"]
            if "spotify_single_query" in context.user_data:
                del context.user_data["spotify_single_query"]
            if "spotify_single_url" in context.user_data:
                del context.user_data["spotify_single_url"]

            return
        
        else:
            await query.edit_message_caption(
                caption="⚠ مشکلی پیش آمده...\nلطفا دوباره تلاش کنید",
            )

            if "spotify_single_step" in context.user_data:
                del context.user_data["spotify_single_step"]
            if "spotify_single_query" in context.user_data:
                del context.user_data["spotify_single_query"]
            if "spotify_single_url" in context.user_data:
                del context.user_data["spotify_single_url"]

            return

    elif query.data == "cancel_download_spotify_single":
        if "spotify_single_step" in context.user_data:
            if "spotify_single_step" in context.user_data:
                del context.user_data["spotify_single_step"]
            if "spotify_single_query" in context.user_data:
                del context.user_data["spotify_single_query"]
            if "spotify_single_url" in context.user_data:
                del context.user_data["spotify_single_url"]

            await query.edit_message_caption(
                caption="درخواست شما با موفقیت لغو شد ✅"
            )

            return
        else:
            await query.edit_message_caption(
                caption="⚠ این درخواست قبلاً پردازش شده است و دیگر معتبر نیست. لطفاً دوباره مراحل را طی کنید..."
            )

            if "spotify_single_step" in context.user_data:
                del context.user_data["spotify_single_step"]
            if "spotify_single_query" in context.user_data:
                del context.user_data["spotify_single_query"]
            if "spotify_single_url" in context.user_data:
                del context.user_data["spotify_single_url"]

            return       

    if query.data == "confirm_download_spotify_playlist":
        if "playlist_id" in context.user_data:
            await query.edit_message_caption(
                caption="⏳ در حال دریافت لیست آهنگ‌ها..."
            )
            
            playlist_id = context.user_data.get("playlist_id")
            tracks = get_playlist_tracks(playlist_id, SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET)
            await query.message.reply_text(f"{len(tracks)} آهنگ پیدا شد. در حال دانلود...")
            
            downloaded_files = []
            for track in tracks:
                file_path = download_playlist(track)
                if file_path and os.path.exists(file_path):
                    downloaded_files.append(file_path)
                    
            if downloaded_files:
                for file_path in downloaded_files:
                    await context.bot.send_audio(chat_id=query.message.chat_id, audio=open(file_path, 'rb'))
                    
                # delete the coin in account 
                with sqlite3.connect("data.db") as conn:
                    cursor = conn.cursor()
                    #get the number of coins
                    cursor.execute('SELECT coins FROM users WHERE user_id = ?', (user_id,))
                    old_coins = cursor.fetchone()

                    if old_coins[0]-context.user_data.get("playlist_track_count") >= 0:
                        new_coins = old_coins[0]-context.user_data.get("playlist_track_count")
                        #set the new number of coins
                        cursor.execute('UPDATE users SET coins = ? WHERE user_id = ?', (new_coins ,user_id,))
                        conn.commit()
                    else:
                        await context.bot.send_message(
                            chat_id=user_id,
                            text="⚠ سکه های شما کافی نمیباشد!\nشما میتوانید از طریق بخش افزایش سکه تعداد سکه های خود را افزایش دهید...",
                        )
                        if "spotify_playlist_step" in context.user_data:
                            del context.user_data["spotify_playlist_step"]
                        if "spotify_playlist_query" in context.user_data:
                            del context.user_data["spotify_playlist_query"]
                        if "spotify_playlist_url" in context.user_data:
                            del context.user_data["spotify_playlist_url"]

                        return
    
                await query.message.reply_text("✅ همه آهنگ‌ ها ارسال شدند!")
            else:
                await query.message.reply_text("❌ هیچ آهنگی دانلود نشد.")     
        else:
            await query.edit_message_caption(
                caption="⚠ مشکلی پیش آمده...\nلطفا دوباره تلاش کنید",
            )
            if "spotify_playlist_step" in context.user_data:
                del context.user_data["spotify_playlist_step"]
            if "spotify_playlist_query" in context.user_data:
                del context.user_data["spotify_playlist_query"]
            if "spotify_playlist_url" in context.user_data:
                del context.user_data["spotify_playlist_url"]

            return

    elif query.data == "cancel_download_spotify_playlist":
        if "spotify_playlist_step" in context.user_data:
            if "spotify_playlist_step" in context.user_data:
                del context.user_data["spotify_playlist_step"]
            if "spotify_playlist_query" in context.user_data:
                del context.user_data["spotify_playlist_query"]
            if "spotify_playlist_url" in context.user_data:
                del context.user_data["spotify_playlist_url"]

            await query.edit_message_caption(
                caption="درخواست شما با موفقیت لغو شد ✅"
            )

            return
        else:
            await query.edit_message_caption(
                caption="⚠ این درخواست قبلاً پردازش شده است و دیگر معتبر نیست. لطفاً دوباره مراحل را طی کنید..."
            )

            if "spotify_playlist_step" in context.user_data:
                del context.user_data["spotify_playlist_step"]
            if "spotify_playlist_query" in context.user_data:
                del context.user_data["spotify_playlist_query"]
            if "spotify_playlist_url" in context.user_data:
                del context.user_data["spotify_playlist_url"]

            return       

    elif query.data == "confirm_download_pin":
        if "pin_step" in context.user_data:
            pin_url = context.user_data.get("pin_img_url")

            await query.message.edit_text(
                text="📩 در حال دانلود عکس...",
                reply_markup=None
            )

            keyboard = [
                [KeyboardButton("🔙 بازگشت 🔙")]
            ]
            inline_markup = ReplyKeyboardMarkup(keyboard)

            try:
                pin_img_name = os.path.basename(pin_url)
                pin_img_data = requests.get(pin_url).content

                with open(pin_img_name, "wb") as img_file:
                    img_file.write(pin_img_data)

                # delete the coin in account 
                with sqlite3.connect("data.db") as conn:
                    cursor = conn.cursor()
                    #get the number of coins
                    cursor.execute('SELECT coins FROM users WHERE user_id = ?', (user_id,))
                    old_coins = cursor.fetchone()

                    if old_coins[0]-2 >= 0:
                        new_coins = old_coins[0] - 2
                        #set the new number of coins
                        cursor.execute('UPDATE users SET coins = ? WHERE user_id = ?', (new_coins ,user_id,))
                        conn.commit()
                    else:
                        await context.bot.send_message(
                            chat_id=user_id,
                            text="⚠ سکه های شما کافی نمیباشد!\nشما میتوانید از طریق بخش افزایش سکه تعداد سکه های خود را افزایش دهید...",
                        )
                        
                        if "pin_step" in context.user_data:
                            del context.user_data["pin_step"]
                        if "pin_img_url" in context.user_data:
                            del context.user_data["pin_img_url"]
                        return
       
                with open(pin_img_name, "rb") as img_file:
                    await context.bot.send_document(
                        chat_id=user_id,
                        document=img_file,
                        caption="✅ عکس شما با موفقیت دانلود شد."
                    )
                
                os.remove(pin_img_name)     

                if "pin_step" in context.user_data:
                    del context.user_data["pin_step"]
                if "pin_img_url" in context.user_data:
                    del context.user_data["pin_img_url"]
                return    
            except TimedOut:
                if "pin_step" in context.user_data:
                    del context.user_data["pin_step"]
                if "pin_img_url" in context.user_data:
                    del context.user_data["pin_img_url"]

                await update.callback_query.edit_message_text(
                    "⚠ خطا: مشکلی در دانلود فایل پیش آمده. لطفا بعدا دوباره مراحل را طی کنید...",
                    reply_markup=inline_markup
                )
                return
            except Exception as e:
                if "pin_step" in context.user_data:
                    del context.user_data["pin_step"]
                if "pin_img_url" in context.user_data:
                    del context.user_data["pin_img_url"]

                await update.callback_query.edit_message_text(f"⚠ مشکلی پیش آمده!\nلطفا به پشتیبانی اطلاع دهید...\n\n{e}")
                return
        else:
            await query.edit_message_caption(
                caption="⚠ این درخواست قبلاً پردازش شده است و دیگر معتبر نیست. لطفاً دوباره مراحل را طی کنید..."
            )

            if "pin_step" in context.user_data:
                del context.user_data["pin_step"]
            if "pin_img_url" in context.user_data:
                del context.user_data["pin_img_url"]
            return

    elif query.data == "cancel_download_pin":
        if "pin_step" in context.user_data:
            if "pin_step" in context.user_data:
                del context.user_data["pin_step"]
            if "pin_img_url" in context.user_data:
                del context.user_data["pin_img_url"]

            await query.edit_message_text(
                "درخواست شما با موفقیت لغو شد ✅",
            )
            return
        else:
            await query.edit_message_caption(
                caption="⚠ این درخواست قبلاً پردازش شده است و دیگر معتبر نیست. لطفاً دوباره مراحل را طی کنید..."
            )

            if "pin_step" in context.user_data:
                del context.user_data["pin_step"]
            if "pin_img_url" in context.user_data:
                del context.user_data["pin_img_url"]
            return

    elif query.data == "confirm_download_insta_post":
        if "insta_post_step" in context.user_data:
            post_url = context.user_data.get("insta_post_url")
            post_folder = None

            await query.message.edit_text(
                text="📩 در حال دانلود پست...",
                reply_markup=None
            )

            keyboard = [
                [KeyboardButton("🔙 بازگشت 🔙")]
            ]
            inline_markup = ReplyKeyboardMarkup(keyboard)

            try:
                post = instaloader.Post.from_shortcode(loader.context, post_url)

                loader.download_post(post, target=post_url)

                post_folder = os.path.join(os.getcwd(), post_url)

                if not os.path.exists(post_folder):
                    await update.callback_query.edit_message_text(
                        "⚠خطا: فایل ها دانلود نشدند. لطفا دوباره مراحل را طی کنید...",
                        reply_markup=inline_markup
                    )

                    if "insta_post_url" in context.user_data:
                        del context.user_data["insta_post_url"]
                    if "insta_post_step" in context.user_data:
                        del context.user_data["insta_post_step"]
                    return

                downloaded_files = glob.glob(os.path.join(post_folder, "*"))
                
                if not downloaded_files:
                    await update.callback_query.edit_message_text(
                        "⚠خطا: فایل ها دانلود نشدند. لطفا دوباره مراحل را طی کنید...",
                        reply_markup=inline_markup
                    )
                    if "insta_post_url" in context.user_data:
                        del context.user_data["insta_post_url"]
                    if "insta_post_step" in context.user_data:
                        del context.user_data["insta_post_step"]
                    return

                is_video = post.is_video

                # delete the coin in account 
                with sqlite3.connect("data.db") as conn:
                    cursor = conn.cursor()
                    #get the number of coins
                    cursor.execute('SELECT coins FROM users WHERE user_id = ?', (user_id,))
                    old_coins = cursor.fetchone()

                    if old_coins[0]-2 >= 0:
                        new_coins = old_coins[0] - 2
                        #set the new number of coins
                        cursor.execute('UPDATE users SET coins = ? WHERE user_id = ?', (new_coins ,user_id,))
                        conn.commit()
                    else:
                        await update.callback_query.edit_message_text(
                            "⚠ سکه های شما کافی نمیباشد!\nشما میتوانید از طریق بخش افزایش سکه تعداد سکه های خود را افزایش دهید...",
                            reply_markup=inline_markup
                        )
                        if "insta_post_url" in context.user_data:
                            del context.user_data["insta_post_url"]
                        if "insta_post_step" in context.user_data:
                            del context.user_data["insta_post_step"]
                        return

                if is_video:
                    video_files = [f for f in downloaded_files if f.endswith(".mp4")]
                    if video_files:
                        media_path = video_files[0]
                        
                        if len(post.caption) > config["max_len_capt"]:
                            post_capt = post.caption[:max_leng_cap]
                        else:
                            post_capt = post.caption

                        with open(media_path, "rb") as media_file:
                            await update.callback_query.message.reply_video(
                                video=media_file,
                                caption=post_capt
                            )
                            if "insta_post_url" in context.user_data:
                                del context.user_data["insta_post_url"]
                            if "insta_post_step" in context.user_data:
                                del context.user_data["insta_post_step"]
                            return
                    else:
                        await update.callback_query.edit_message_text(
                            "⚠خطا: ویدیو دانلود نشده است. لطفا دوباره مراحل را طی کنید...",
                            reply_markup=inline_markup
                        )
                        if "insta_post_url" in context.user_data:
                            del context.user_data["insta_post_url"]
                        if "insta_post_step" in context.user_data:
                            del context.user_data["insta_post_step"]
                        return
                else:
                    image_files = [f for f in downloaded_files if f.endswith((".jpg", ".png"))]
                    if image_files:
                        media_path = image_files[0]
                        
                        if len(post.caption) > config["max_len_capt"]:
                            post_capt = post.caption[:max_leng_cap]
                        else:
                            post_capt = post.caption

                        with open(media_path, "rb") as media_file:
                            await update.callback_query.message.reply_photo(
                                photo=media_file,
                                caption=post_capt
                            )
                            if "insta_post_url" in context.user_data:
                                del context.user_data["insta_post_url"]
                            if "insta_post_step" in context.user_data:
                                del context.user_data["insta_post_step"]
                            return
                    else:
                        await update.callback_query.edit_message_text(
                            "⚠خطا: عکس دانلود نشده است. لطفا دوباره مراحل را طی کنید...",
                            reply_markup=inline_markup
                        )
                        if "insta_post_url" in context.user_data:
                            del context.user_data["insta_post_url"]
                        if "insta_post_step" in context.user_data:
                            del context.user_data["insta_post_step"]
                        return

            except TimedOut:
                await update.callback_query.edit_message_text(
                    "⚠ خطا: مشکلی در دانلود فایل پیش آمده. لطفا بعدا دوباره مراحل را طی کنید...",
                    reply_markup=inline_markup
                )
                if "insta_post_url" in context.user_data:
                    del context.user_data["insta_post_url"]
                if "insta_post_step" in context.user_data:
                    del context.user_data["insta_post_step"]
                return
            except Exception as e:
                await update.callback_query.edit_message_text(f"⚠ خطا:\n{e}")
                if "insta_post_url" in context.user_data:
                    del context.user_data["insta_post_url"]
                if "insta_post_step" in context.user_data:
                    del context.user_data["insta_post_step"]
                return
            finally:
                if post_folder and os.path.exists(post_folder):
                    shutil.rmtree(post_folder)
                if "insta_post_url" in context.user_data:
                    del context.user_data["insta_post_url"]
                if "insta_post_step" in context.user_data:
                    del context.user_data["insta_post_step"]
                return
        else:
            await query.edit_message_caption(
                caption="⚠ این درخواست قبلاً پردازش شده است و دیگر معتبر نیست. لطفاً دوباره مراحل را طی کنید..."
            )

            if "insta_post_url" in context.user_data:
                del context.user_data["insta_post_url"]
            if "insta_post_step" in context.user_data:
                del context.user_data["insta_post_step"]
            return

    elif query.data == "cancel_download_insta_post":
        if "insta_post_step" in context.user_data:    
            if "insta_post_url" in context.user_data:
                del context.user_data["insta_post_url"]
            if "insta_post_step" in context.user_data:
                del context.user_data["insta_post_step"]

            await query.edit_message_text(
                "درخواست شما با موفقیت لغو شد ✅",
            )
            return
        else:
            await query.edit_message_caption(
                caption="⚠ این درخواست قبلاً پردازش شده است و دیگر معتبر نیست. لطفاً دوباره مراحل را طی کنید..."
            )

            if "insta_post_url" in context.user_data:
                del context.user_data["insta_post_url"]
            if "insta_post_step" in context.user_data:
                del context.user_data["insta_post_step"]
            return

    elif query.data == "confirm_download_soundcloud":
        if "soundcloud_step" in context.user_data:
            await query.edit_message_caption(
                caption="🎧 در حال دانلود آهنگ..."
            )

            try:
                soundcloud_url = context.user_data.get("soundcloud_query")
                file_path = download_from_soundcloud(soundcloud_url)

                print(os.listdir("downloads/"))

                
                # delete the coin in account 
                with sqlite3.connect("data.db") as conn:
                    cursor = conn.cursor()
                    #get the number of coins
                    cursor.execute('SELECT coins FROM users WHERE user_id = ?', (user_id,))
                    old_coins = cursor.fetchone()

                    if old_coins[0]-2 >= 0:
                        new_coins = old_coins[0] - 2
                        #set the new number of coins
                        cursor.execute('UPDATE users SET coins = ? WHERE user_id = ?', (new_coins ,user_id,))
                        conn.commit()
                    else:
                        await context.bot.send_message(
                            chat_id=user_id,
                            text="⚠ سکه های شما کافی نمیباشد!\nشما میتوانید از طریق بخش افزایش سکه تعداد سکه های خود را افزایش دهید...",
                        )
                        if "spotify_single_step" in context.user_data:
                            del context.user_data["spotify_single_step"]
                        if "spotify_single_query" in context.user_data:
                            del context.user_data["spotify_single_query"]
                        if "spotify_single_url" in context.user_data:
                            del context.user_data["spotify_single_url"]

                        return
            
                await context.bot.send_message(
                    chat_id=user_id,
                    text="✅ آهنگ با موفقیت دانلود شد👌\nدر حال ارسال فایل..."
                )

                caption=(
                    f'<a href="https://t.me/Megaa_helperbot">@megaa_helperbot</a> | <a href="{context.user_data.get("soundcloud_url")}">Music link</a>'
                )

                #send to channel
                bot = context.bot
                with open(file_path, 'rb') as audio_file:
                    await bot.send_audio(
                        chat_id=config["channels"][0],
                        audio=audio_file,
                        caption=caption,
                        parse_mode="HTML"
                    )

                #send to user
                with open(file_path, 'rb') as audio_file:
                    await context.bot.send_audio(
                        chat_id=user_id,
                        audio=audio_file,
                        caption=caption,
                        parse_mode="HTML"
                    )

                if "soundcloud_step" in context.user_data:
                    del context.user_data["soundcloud_step"]
                if "soundcloud_query" in context.user_data:
                    del context.user_data["soundcloud_query"]
                if "soundcloud_url" in context.user_data:
                    del context.user_data["soundcloud_url"]
                return
            
            except Exception as e:
                # Add the coin in account 
                with sqlite3.connect("data.db") as conn:
                    cursor = conn.cursor()
                    #get the number of coins
                    cursor.execute('SELECT coins FROM users WHERE user_id = ?', (user_id,))
                    old_coins = cursor.fetchone()

                    new_coins = old_coins[0] + 2
                    #set the new number of coins
                    cursor.execute('UPDATE users SET coins = ? WHERE user_id = ?', (new_coins ,user_id,))
                    conn.commit()
 

                if "soundcloud_step" in context.user_data:
                    del context.user_data["soundcloud_step"]
                if "soundcloud_query" in context.user_data:
                    del context.user_data["soundcloud_query"]
                if "soundcloud_url" in context.user_data:
                    del context.user_data["soundcloud_url"]
 
                error_message = str(e)

                if error_message == "1008096572":
                    await query.edit_message_caption(
                        caption="⏳ زمان دانلود به پایان رسید!\n\nلطفاً لینک آهنگ را دوباره ارسال کنید تا بتوانید آن را دانلود کنید."
                    )
                elif error_message == "⚠️ هیچ آهنگی یافت نشد :(":
                    await query.edit_message_caption(
                        caption="💠 متاسفانه امکان دانلود این اهنگ وجود ندارد..."
                    )
                elif error_message == "⚠ متاسفیم... آهنگ مورد نظر شما یافت نشد :(":
                    await query.edit_message_caption(
                        caption="💠 متاسفانه امکان دانلود این اهنگ وجود ندارد..."
                    )
                else:
                    await query.edit_message_caption(
                        caption=f"⚠ مشکلی پیش آمده:\n\nلطفا به پشتیبانی اطلاع دهید تا به این مشکل رسیدگی کند...\nERROR_CODE: {error_message}"
                    )
        else:
            await query.edit_message_caption(
                caption="⚠ مشکلی پیش آمده...\nلطفا دوباره تلاش کنید",
            )

            if "soundcloud_step" in context.user_data:
                del context.user_data["soundcloud_step"]
            if "soundcloud_query" in context.user_data:
                del context.user_data["soundcloud_query"]
            if "soundcloud_url" in context.user_data:
                del context.user_data["soundcloud_url"]
            return

    elif query.data == "cancel_download_soundcloud":
        if "soundcloud_step" in context.user_data:
            if "soundcloud_step" in context.user_data:
                del context.user_data["soundcloud_step"]
            if "soundcloud_query" in context.user_data:
                del context.user_data["soundcloud_query"]
            if "soundcloud_url" in context.user_data:
                del context.user_data["soundcloud_url"]

            await query.edit_message_caption(
                caption="درخواست شما با موفقیت لغو شد ✅"
            )

            return
        else:
            await query.edit_message_caption(
                caption="⚠ این درخواست قبلاً پردازش شده است و دیگر معتبر نیست. لطفاً دوباره مراحل را طی کنید..."
            )

            if "soundcloud_step" in context.user_data:
                del context.user_data["soundcloud_step"]
            if "soundcloud_query" in context.user_data:
                del context.user_data["soundcloud_query"]
            if "soundcloud_url" in context.user_data:
                del context.user_data["soundcloud_url"]
            return       

    elif query.data == "confirm_download_youtube":
        if "youtube_step" in context.user_data:
            title, file_size = get_audio_info(context.user_data.get("youtube_url"))

            if file_size > MAX_FILE_SIZE:
                    await update.message.reply_text("❌ حجم فایل بیش از ۵۰ مگابایت است! متاسفانه نمیتوان این فایل را دانلود کرد!")
                    if "youtube_step" in context.user_data:
                        del context.user_data["youtube_step"]
                    if "youtube_url" in context.user_data:
                        del context.user_data["youtube_url"]
                    return
            
            await context.bot.send_message(
                chat_id=user_id,
                text="🔄 در حال دانلود فایل صوتی..."
            )

            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': f'{DOWNLOADS_DIR}/{title}.%(ext)s',
                'quiet': True,
                'cookiefile': 'cookies.txt',
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([context.user_data.get("youtube_url")])

            # تبدیل به mp3
            file_path = os.path.join(DOWNLOADS_DIR, f"{title}.webm")  # فرض بر این است که فرمت ویدیو webm است
            mp3_file = convert_to_mp3(file_path, title)

            # delete the coin in account 
            with sqlite3.connect("data.db") as conn:
                cursor = conn.cursor()
                #get the number of coins
                cursor.execute('SELECT coins FROM users WHERE user_id = ?', (user_id,))
                old_coins = cursor.fetchone()

                if old_coins[0]-2 >= 0:
                    new_coins = old_coins[0] - 2
                    #set the new number of coins
                    cursor.execute('UPDATE users SET coins = ? WHERE user_id = ?', (new_coins ,user_id,))
                    conn.commit()
                else:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text="⚠ سکه های شما کافی نمیباشد!\nشما میتوانید از طریق بخش افزایش سکه تعداد سکه های خود را افزایش دهید...",
                    )
                    
                    if "youtube_step" in context.user_data:
                        del context.user_data["youtube_step"]
                    if "youtube_url" in context.user_data:
                        del context.user_data["youtube_url"]

                    os.remove(file_path)
                    os.remove(mp3_file)
                    return

            with open(mp3_file, "rb") as audio_file:
                await context.bot.send_audio(
                    chat_id=user_id,
                    audio=audio_file
                )
            
            # حذف فایل‌ها در هر صورت
            os.remove(file_path)
            os.remove(mp3_file)
            
            if "youtube_step" in context.user_data:
                del context.user_data["youtube_step"]
            if "youtube_url" in context.user_data:
                del context.user_data["youtube_url"]
            return
        else:
            await query.edit_message_text(
                "⚠ این درخواست قبلاً پردازش شده است و دیگر معتبر نیست. لطفاً دوباره مراحل را طی کنید..."
            )

            if "youtube_step" in context.user_data:
                del context.user_data["youtube_step"]
            if "youtube_url" in context.user_data:
                del context.user_data["youtube_url"]
            return       

    elif query.data == "cancel_download_youtube":
        if "youtube_step" in context.user_data:
            if "youtube_step" in context.user_data:
                del context.user_data["youtube_step"]
            if "youtube_url" in context.user_data:
                del context.user_data["youtube_url"]

            await query.edit_message_text(
                "درخواست شما با موفقیت لغو شد ✅"
            )

            return
        else:
            await query.edit_message_text(
                "⚠ این درخواست قبلاً پردازش شده است و دیگر معتبر نیست. لطفاً دوباره مراحل را طی کنید..."
            )

            if "youtube_step" in context.user_data:
                del context.user_data["youtube_step"]
            if "youtube_url" in context.user_data:
                del context.user_data["youtube_url"]
            return       


    #admins
    elif query.data == "confirm_send_user":
        if context.user_data.get("msg_user_step") == 3:
            keyboard = [
                [KeyboardButton("🔙 بازگشت 🔙")]
            ]
            inline_markup = ReplyKeyboardMarkup(keyboard)

            await context.bot.send_message(
                chat_id=context.user_data.get("msg_user_id"),
                text=f"{context.user_data.get("txt_send_user")}",
            )

            await context.bot.send_message(
                chat_id=user_id,
                text=f"✅ پیام شما با موفقیت برای کاربر ارسال شد...",
                reply_markup=inline_markup
            )

            if "msg_user_step" in context.user_data:
                del context.user_data["msg_user_step"]
            if "msg_user_id" in context.user_data:
                del context.user_data["msg_user_id"]
            if "txt_send_user" in context.user_data:
                del context.user_data["txt_send_user"]
            return
        else:
            await context.bot.send_message(
                chat_id=user_id,
                text="⚠ این درخواست قبلاً پردازش شده است و دیگر معتبر نیست. لطفاً دوباره مراحل را طی کنید..."
            )

            if "msg_user_step" in context.user_data:
                del context.user_data["msg_user_step"]
            if "msg_user_id" in context.user_data:
                del context.user_data["msg_user_id"]
            if "txt_send_user" in context.user_data:
                del context.user_data["txt_send_user"]
            return 

    elif query.data == "cancel_send_user":
        if context.user_data.get("msg_user_step") == 3:
            keyboard = [
                [KeyboardButton("🔙 بازگشت 🔙")]
            ]
            inline_markup = ReplyKeyboardMarkup(keyboard)

            await context.bot.send_message(
                chat_id=user_id,
                text=f"✅ عملیات با موفقیت لغو شد.",
                reply_markup=inline_markup
            )

            if "msg_user_step" in context.user_data:
                del context.user_data["msg_user_step"]
            if "msg_user_id" in context.user_data:
                del context.user_data["msg_user_id"]
            if "txt_send_user" in context.user_data:
                del context.user_data["txt_send_user"]
            return
        else:
            await context.bot.send_message(
                chat_id=user_id,
                text="⚠ این درخواست قبلاً پردازش شده است و دیگر معتبر نیست. لطفاً دوباره مراحل را طی کنید..."
            )

            if "msg_user_step" in context.user_data:
                del context.user_data["msg_user_step"]
            if "msg_user_id" in context.user_data:
                del context.user_data["msg_user_id"]
            if "txt_send_user" in context.user_data:
                del context.user_data["txt_send_user"]
            return 

    elif query.data == "confirm_send_all":
        if context.user_data.get("send_all_step") == 2:
            keyboard = [
                [KeyboardButton("🔙 بازگشت 🔙")]
            ]
            inline_markup = ReplyKeyboardMarkup(keyboard)

            with sqlite3.connect("data.db") as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT user_id FROM users")
                all_user_ids = [auser_id[0] for auser_id in cursor.fetchall()]
        
            try:
                for all_user_id in all_user_ids:
                    await context.bot.send_message(
                        chat_id=all_user_id,
                        text=f"{context.user_data.get("send_all_txt")}",
                    )
                await asyncio.sleep(0.5)
            except Forbidden:
                print(f"کاربر {user_id} ربات را مسدود کرده است. پیام ارسال نشد.")

            await context.bot.send_message(
                chat_id=user_id,
                text=f"✅ متن شما با موفقیت برای همه کاربران ارسال شد...",
                reply_markup=inline_markup
            )

            if "send_all_step" in context.user_data:
                del context.user_data["send_all_step"]
            if "send_all_txt" in context.user_data:
                del context.user_data["send_all_txt"]
            return
        else:
            await context.bot.send_message(
                chat_id=user_id,
                text="⚠ این درخواست قبلاً پردازش شده است و دیگر معتبر نیست. لطفاً دوباره مراحل را طی کنید..."
            )

            if "send_all_step" in context.user_data:
                del context.user_data["send_all_step"]
            if "send_all_txt" in context.user_data:
                del context.user_data["send_all_txt"]
            return 

    elif query.data == "confirm_send_all":
        if context.user_data.get("send_all_step") == 2:
            keyboard = [
                [KeyboardButton("🔙 بازگشت 🔙")]
            ]
            inline_markup = ReplyKeyboardMarkup(keyboard)

            await context.bot.send_message(
                chat_id=user_id,
                text=f"✅ درخواست شما با موفقیت لغو شد...",
                reply_markup=inline_markup
            )

            if "send_all_step" in context.user_data:
                del context.user_data["send_all_step"]
            if "send_all_txt" in context.user_data:
                del context.user_data["send_all_txt"]
            return
        else:
            await context.bot.send_message(
                chat_id=user_id,
                text="⚠ این درخواست قبلاً پردازش شده است و دیگر معتبر نیست. لطفاً دوباره مراحل را طی کنید..."
            )

            if "send_all_step" in context.user_data:
                del context.user_data["send_all_step"]
            if "send_all_txt" in context.user_data:
                del context.user_data["send_all_txt"]
            return 

    elif query.data == "confirm_coin_add":
        if "coin_add_step" in context.user_data:
            keyboard = [
                [KeyboardButton("🔙 بازگشت 🔙")]
            ]
            inline_markup = ReplyKeyboardMarkup(keyboard)

            # add coin for the user dest
            with sqlite3.connect("data.db") as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT coins FROM users WHERE user_id = ?",(context.user_data.get("coin_add_user_id_dest"),))
                old_coins = cursor.fetchone()

                new_coins = old_coins[0] + context.user_data.get('add_num_coins')

                cursor.execute("UPDATE users SET coins = ? WHERE user_id = ?", (new_coins, context.user_data.get("coin_add_user_id_dest"),))
                conn.commit()
            
            # send message for the user dest
            await context.bot.send_message(
                chat_id=context.user_data.get("coin_add_user_id_dest"),
                text=f"🎉 ادمین برای شما {context.user_data.get("add_num_coins")} سکه شارژ کرد!",
            )

            await context.bot.send_message(
                chat_id=user_id,
                text="✅ سکه ها با موفقیت برای کاربر مدنظر شارژ شد.",
                reply_to_message_id=update.effective_message.id,
                reply_markup=inline_markup
            )

            if "coin_add_step" in context.user_data:
                del context.user_data["coin_add_step"]
            if "coin_add_user_id_dest" in context.user_data:
                del context.user_data["coin_add_user_id_dest"]
            if "add_num_coins" in context.user_data:
                del context.user_data["add_num_coins"]
            return  
        else:
            await context.bot.send_message(
                chat_id=user_id,
                text="⚠ این درخواست قبلاً پردازش شده است و دیگر معتبر نیست. لطفاً دوباره مراحل را طی کنید...",
                reply_to_message_id=update.effective_message.id
            )

            if "coin_add_step" in context.user_data:
                del context.user_data["coin_add_step"]
            if "coin_add_user_id_dest" in context.user_data:
                del context.user_data["coin_add_user_id_dest"]
            if "add_num_coins" in context.user_data:
                del context.user_data["add_num_coins"]
            return  

    elif query.data == "cancel_coin_add":
        if "coin_add_step" in context.user_data:
            keyboard = [
                [KeyboardButton("🔙 بازگشت 🔙")]
            ]
            inline_markup = ReplyKeyboardMarkup(keyboard)

            await context.bot.send_message(
                chat_id=user_id,
                text="✅ درخواست با موفقیت لغو شد.",
                reply_to_message_id=update.effective_message.id,
                reply_markup=inline_markup
            )

            if "coin_add_step" in context.user_data:
                del context.user_data["coin_add_step"]
            if "coin_add_user_id_dest" in context.user_data:
                del context.user_data["coin_add_user_id_dest"]
            if "add_num_coins" in context.user_data:
                del context.user_data["add_num_coins"]
            return  
        else:
            await context.bot.send_message(
                chat_id=user_id,
                text="⚠ این درخواست قبلاً پردازش شده است و دیگر معتبر نیست. لطفاً دوباره مراحل را طی کنید...",
                reply_to_message_id=update.effective_message.id
            )

            if "coin_add_step" in context.user_data:
                del context.user_data["coin_add_step"]
            if "coin_add_user_id_dest" in context.user_data:
                del context.user_data["coin_add_user_id_dest"]
            if "add_num_coins" in context.user_data:
                del context.user_data["add_num_coins"]
            return  

    elif query.data == "confirm_coin_remove":
        if "coin_remove_step" in context.user_data:
            keyboard = [
                [KeyboardButton("🔙 بازگشت 🔙")]
            ]
            inline_markup = ReplyKeyboardMarkup(keyboard)

            # add coin for the user dest
            with sqlite3.connect("data.db") as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT coins FROM users WHERE user_id = ?",(context.user_data.get("coin_remove_user_id_dest"),))
                old_coins = cursor.fetchone()

                if (old_coins[0] - context.user_data.get('remove_num_coins')) < 0:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text="⚠ سکه های کاربر کمتر از مقدار وارد شده است!",
                        reply_to_message_id=update.effective_message.id,
                        reply_markup=inline_markup
                    )

                    if "coin_remove_step" in context.user_data:
                        del context.user_data["coin_remove_step"]
                    if "coin_remove_user_id_dest" in context.user_data:
                        del context.user_data["coin_remove_user_id_dest"]
                    if "remove_num_coins" in context.user_data:
                        del context.user_data["remove_num_coins"]
                    return
                
                new_coins = old_coins[0] - context.user_data.get('remove_num_coins')

                cursor.execute("UPDATE users SET coins = ? WHERE user_id = ?", (new_coins, context.user_data.get("coin_remove_user_id_dest"),))
                conn.commit()
            
            # send message for the user dest
            await context.bot.send_message(
                chat_id=context.user_data.get("coin_remove_user_id_dest"),
                text=f"🤖 ادمین {context.user_data.get("remove_num_coins")} سکه از حساب شما کم کرد.",
            )

            await context.bot.send_message(
                chat_id=user_id,
                text="✅ سکه ها با موفقیت از حساب کاربر کم شد.",
                reply_to_message_id=update.effective_message.id,
                reply_markup=inline_markup
            )

            if "coin_remove_step" in context.user_data:
                del context.user_data["coin_remove_step"]
            if "coin_remove_user_id_dest" in context.user_data:
                del context.user_data["coin_remove_user_id_dest"]
            if "remove_num_coins" in context.user_data:
                del context.user_data["remove_num_coins"]
            return  
        else:
            await context.bot.send_message(
                chat_id=user_id,
                text="⚠ این درخواست قبلاً پردازش شده است و دیگر معتبر نیست. لطفاً دوباره مراحل را طی کنید...",
                reply_to_message_id=update.effective_message.id
            )

            if "coin_remove_step" in context.user_data:
                del context.user_data["coin_remove_step"]
            if "coin_remove_user_id_dest" in context.user_data:
                del context.user_data["coin_remove_user_id_dest"]
            if "remove_num_coins" in context.user_data:
                del context.user_data["remove_num_coins"]
            return  

    elif query.data == "cancel_coin_remove":
        if "coin_remove_step" in context.user_data:
            keyboard = [
                [KeyboardButton("🔙 بازگشت 🔙")]
            ]
            inline_markup = ReplyKeyboardMarkup(keyboard)

            await context.bot.send_message(
                chat_id=user_id,
                text="✅ درخواست با موفقیت لغو شد.",
                reply_to_message_id=update.effective_message.id,
                reply_markup=inline_markup
            )

            if "coin_remove_step" in context.user_data:
                del context.user_data["coin_remove_step"]
            if "coin_remove_user_id_dest" in context.user_data:
                del context.user_data["coin_remove_user_id_dest"]
            if "remove_num_coins" in context.user_data:
                del context.user_data["remove_num_coins"]
            return  
        else:
            await context.bot.send_message(
                chat_id=user_id,
                text="⚠ این درخواست قبلاً پردازش شده است و دیگر معتبر نیست. لطفاً دوباره مراحل را طی کنید...",
                reply_to_message_id=update.effective_message.id
            )

            if "coin_remove_step" in context.user_data:
                del context.user_data["coin_remove_step"]
            if "coin_remove_user_id_dest" in context.user_data:
                del context.user_data["coin_remove_user_id_dest"]
            if "remove_num_coins" in context.user_data:
                del context.user_data["remove_num_coins"]
            return  

async def error_handler(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    error_message = traceback.format_exception(None, context.error, context.error.__traceback__)
    error_text = ''.join(error_message)
    bot = context.bot
    
    await bot.send_message(
        chat_id=user_id,
        text=f"🛑 مشکلی در ربات پیش آمده...\nلطفا بعدا دوباره تست کنید."
    )
    
    await bot.send_message(
        chat_id=config["dev_user_id"],
        text=f"🚨 خطا در ربات:\n\n`{error_text}`",
        parse_mode="markdown"
    )

# async def backup_db(context):
#     bot = context.bot

#     if os.path.exists("data.db"):
#         await bot.send_document(
#             chat_id=config["backup_db_channel"],
#             document=open("data.db", 'rb'),
#             caption="📁 بکاپ دیتابیس"
#         )


def main():
    print("[BOT] initializing...")
    application = Application.builder().token(TOKEN).concurrent_updates(True).build()
    job_queue: JobQueue = application.job_queue
    application.add_error_handler(error_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    application.add_handler(MessageHandler(filters.PHOTO, echo_photo))
    application.add_handler(CallbackQueryHandler(handle_confirmation))
    print("[BOT] running bot...")
    # job_queue.run_repeating(backup_db, interval=int(config["backup_time"]), first=0)
    application.run_polling()

if __name__ == '__main__':
    auth_db()
    main()