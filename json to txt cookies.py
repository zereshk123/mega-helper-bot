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

# import requests

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

