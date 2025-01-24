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
json_to_netscape("cookies.json", "cookies.txt")
