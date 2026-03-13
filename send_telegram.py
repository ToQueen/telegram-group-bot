import json
import os
import sys
from datetime import datetime, timezone

import requests

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
MESSAGES_FILE = "messages.json"
TIMEOUT = 30


def fail(msg: str) -> None:
    print(f"ERROR: {msg}")
    sys.exit(1)


def telegram_api(method: str) -> str:
    return f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"


def load_messages():
    if not os.path.exists(MESSAGES_FILE):
        fail(f"File {MESSAGES_FILE} tidak ditemukan.")

    with open(MESSAGES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list) or not data:
        fail("messages.json harus berupa array dan minimal berisi 1 item.")

    if len(data) > 5:
        fail("Maksimal hanya 5 item konten berbeda.")

    normalized = []
    for i, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            fail(f"Item ke-{i} harus object JSON.")

        text = str(item.get("text", "")).strip()
        images = item.get("images", [])

        if not isinstance(images, list):
            fail(f"images pada item ke-{i} harus array.")

        if len(images) > 10:
            fail(f"Item ke-{i} memiliki lebih dari 10 gambar.")

        cleaned_images = [str(x).strip() for x in images if str(x).strip()]

        if not text and not cleaned_images:
            fail(f"Item ke-{i} harus punya text atau minimal 1 gambar.")

        normalized.append({
            "text": text,
            "images": cleaned_images
        })

    return normalized


def send_text(text: str) -> None:
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    r = requests.post(telegram_api("sendMessage"), json=payload, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    if not data.get("ok"):
        fail(f"sendMessage gagal: {data}")


def send_single_photo(photo_url: str, caption: str = "") -> None:
    payload = {
        "chat_id": CHAT_ID,
        "photo": photo_url,
        "caption": caption,
        "parse_mode": "HTML"
    }
    r = requests.post(telegram_api("sendPhoto"), json=payload, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    if not data.get("ok"):
        fail(f"sendPhoto gagal: {data}")


def send_media_group(images, caption: str = "") -> None:
    media = []
    for idx, img in enumerate(images):
        item = {
            "type": "photo",
            "media": img
        }
        # Caption ditaruh di item pertama
        if idx == 0 and caption:
            item["caption"] = caption
            item["parse_mode"] = "HTML"
        media.append(item)

    payload = {
        "chat_id": CHAT_ID,
        "media": media
    }

    r = requests.post(telegram_api("sendMediaGroup"), json=payload, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    if not data.get("ok"):
        fail(f"sendMediaGroup gagal: {data}")


def choose_message(messages):
    # Bergilir berdasarkan jam UTC / 3 jam
    # Jadi setiap run terjadwal akan pindah ke item berikutnya.
    slot = datetime.now(timezone.utc).hour // 3
    index = slot % len(messages)
    return messages[index], index


def main():
    if not BOT_TOKEN:
        fail("TELEGRAM_BOT_TOKEN belum di-set.")
    if not CHAT_ID:
        fail("TELEGRAM_CHAT_ID belum di-set.")

    messages = load_messages()
    item, index = choose_message(messages)

    text = item["text"]
    images = item["images"]

    print(f"Mengirim item ke-{index + 1} dari total {len(messages)} item.")

    if images:
        if len(images) == 1:
            send_single_photo(images[0], text)
        else:
            send_media_group(images[:10], text)
    else:
        send_text(text)

    print("Pesan berhasil dikirim.")


if __name__ == "__main__":
    main()