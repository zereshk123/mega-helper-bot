FROM python:3.12-slim

RUN apt-get update && apt-get install -y ffmpeg

RUN apt-get update && apt-get install -y libzbar0

RUN pip install pyzbar opencv-python

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
