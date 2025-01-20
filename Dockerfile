# استفاده از تصویر پایه پایتون
FROM python:3.12-slim

# نصب ffmpeg
RUN apt-get update && apt-get install -y ffmpeg

# نصب وابستگی‌های پایتون از requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# کپی کردن فایل‌های پروژه
COPY . .

# دستور پیش‌فرض برای اجرای برنامه
CMD ["python", "main.py"]
