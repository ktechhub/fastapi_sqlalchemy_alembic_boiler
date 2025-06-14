import requests
from app.core.config import settings

TELEGRAM_CHAT_ID = settings.TELEGRAM_CHAT_ID
TELEGRAM_BOT_TOKEN = settings.TELEGRAM_BOT_TOKEN


def send_telegram_msg(msg, chat_id=TELEGRAM_CHAT_ID):
    bot_token = settings.TELEGRAM_BOT_TOKEN
    send_msg = f"https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={chat_id}&parse_mode=Markdown&text={msg}"
    response = requests.get(send_msg)
    return response.json()


def send_telegram_image(url, chat_id=TELEGRAM_CHAT_ID):
    send_msg = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto?chat_id={chat_id}&photo={url}"
    response = requests.get(send_msg)
    return response.json()


def send_telegram_video(url, chat_id=TELEGRAM_CHAT_ID):
    send_msg = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo?chat_id={chat_id}&video={url}"
    response = requests.get(send_msg)
    return response.json()


def send_telegram_audio(url, chat_id=TELEGRAM_CHAT_ID):
    send_msg = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendAudio?chat_id={chat_id}&audio={url}"
    response = requests.get(send_msg)
    return response.json()


def send_telegram_document(url, chat_id=TELEGRAM_CHAT_ID):
    send_msg = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument?chat_id={chat_id}&document={url}"
    response = requests.get(send_msg)
    return response.json()


def send_telegram_sticker(url, chat_id=TELEGRAM_CHAT_ID):
    send_msg = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendSticker?chat_id={chat_id}&sticker={url}"
    response = requests.get(send_msg)
    return response.json()


def send_telegram_animation(url, chat_id=TELEGRAM_CHAT_ID):
    send_msg = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendAnimation?chat_id={chat_id}&animation={url}"
    response = requests.get(send_msg)
    return response.json()
