import os
import requests
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not BOT_TOKEN:
    raise SystemExit("Missing TELEGRAM_BOT_TOKEN in .env")

url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"

response = requests.get(url, timeout=15)
response.raise_for_status()

data = response.json()

for update in data.get("result", []):
    message = update.get("message")

    if message:
        chat = message.get("chat")
        print("Chat ID:", chat.get("id"))