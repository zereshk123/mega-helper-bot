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


import subprocess

def download_soundcloud(track_url, output_file="soundcloud_audio.mp3"):
    command = [
        "yt-dlp",
        "-f", "bestaudio",
        "--extract-audio",
        "--audio-format", "mp3",
        "-o", output_file,
        track_url
    ]
    
    subprocess.run(command, check=True)
    print(f"✅ دانلود کامل شد: {output_file}")

# 🔹 لینک آهنگ SoundCloud را اینجا بگذارید
track_url = "https://soundcloud.com/majid-rodgar-581819939/tazvir-intro-prod-saraei?in=majid-rodgar-581819939/sets/tazvir&si=aec066110dd64f6e82963e521acaad45&utm_source=clipboard&utm_medium=text&utm_campaign=social_sharing"

# دانلود آهنگ
download_soundcloud(track_url)
