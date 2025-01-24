import sys
sys.stdout.reconfigure(encoding='utf-8')


# import json
# from http.cookies import SimpleCookie

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

# # آدرس API
# url = "https://brsapi.ir/FreeTsetmcBourseApi/Api_Free_Gold_Currency.json"

# # درخواست به API
# response = requests.get(url)

# # بررسی موفقیت درخواست
# if response.status_code == 200:
#     data = response.json()  # تبدیل پاسخ JSON به دیکشنری

#     # نمایش قیمت طلا
#     print("💰 قیمت طلا:")
#     for item in data["gold"]:
#         print(f"- {item['name']}: {item['price']:,} تومان")

#     # نمایش قیمت ارز
#     print("\n💵 قیمت ارز:")
#     for item in data["currency"]:
#         print(f"- {item['name']}: {item['price']:,} تومان")

#     # نمایش قیمت رمزارزها
#     print("\n₿ قیمت رمزارزها:")
#     for item in data["cryptocurrency"]:
#         print(f"- {item['name']}: {item['price']:,} دلار")

# else:
#     print(f"❌ خطا در دریافت داده‌ها: {response.status_code}")



import requests

# آدرس API
url = "https://api.nobitex.ir/market/global-stats"

# ارسال درخواست GET به API
response = requests.post(url)

# لیست ارزهای معروف (بدون DOT, LINK, MATIC, AVAX, UNI, ATOM, XLM, XMR)
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

# بررسی وضعیت پاسخ
if response.status_code == 200:
    # تبدیل پاسخ به JSON
    data = response.json()
    
    # استخراج داده‌های مربوط به بازارها
    markets = data.get("markets", {}).get("binance", {})
    
    # نمایش ارزهای معروف
    print("{:<10} {:<15}".format("نماد ارز", "قیمت (USD)"))
    print("-" * 25)
    for currency in popular_currencies:
        if currency in markets:
            print("{:<10} {:<15}".format(currency, markets[currency]))
        else:
            print("{:<10} {:<15}".format(currency, "یافت نشد!"))
else:
    print("خطا در دریافت داده. کد وضعیت:", response.status_code)