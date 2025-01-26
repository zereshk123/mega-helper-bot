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

import requests
from bs4 import BeautifulSoup

def download_pinterest_image(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    # پیدا کردن لینک تصویر
    image_tag = soup.find("meta", property="og:image")
    if image_tag:
        image_url = image_tag["content"]
        print(f"✅ لینک عکس پیدا شد: {image_url}")

        # دانلود و ذخیره تصویر
        img_data = requests.get(image_url).content
        with open("pinterest_image.jpg", "wb") as img_file:
            img_file.write(img_data)
        print("✅ عکس با موفقیت دانلود شد.")
    else:
        print("❌ عکس پیدا نشد!")

# تست با لینک پینترست
pinterest_url = "https://www.pinterest.com/pin/7036943162210025/"  # لینک نمونه
download_pinterest_image(pinterest_url)

