import json
import os
import sys
import time
import requests

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
MESSAGES_FILE = "messages.json"
TIMEOUT = 30
DELAY_BETWEEN_MESSAGES = 15
MAX_CAPTION = 1000
MAX_RETRY = 3


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


def request_with_retry(method, payload):
    for attempt in range(1, MAX_RETRY + 1):
        try:
            r = requests.post(telegram_api(method), json=payload, timeout=TIMEOUT)
            data = r.json()

            print(f"Response ({method}):", data)

            if r.status_code == 200 and data.get("ok"):
                return True
            else:
                print(f"Gagal attempt {attempt}: {data}")

        except Exception as e:
            print(f"Error attempt {attempt}: {e}")

        time.sleep(5)

    return False


def send_text(text: str) -> bool:
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "disable_web_page_preview": True
    }
    return request_with_retry("sendMessage", payload)


def send_single_photo(photo_url: str, caption: str = "") -> bool:
    payload = {
        "chat_id": CHAT_ID,
        "photo": photo_url,
        "caption": caption
    }
    return request_with_retry("sendPhoto", payload)


def send_media_group(images, caption: str = "") -> bool:
    media = []

    for idx, img in enumerate(images[:10]):
        item = {
            "type": "photo",
            "media": img
        }
        if idx == 0 and caption:
            item["caption"] = caption
        media.append(item)

    payload = {
        "chat_id": CHAT_ID,
        "media": media
    }

    return request_with_retry("sendMediaGroup", payload)


def send_item(item, index: int):
    text = item["text"][:MAX_CAPTION]
    images = item["images"]

    print(f"\n=== Mengirim pesan ke-{index} ===")

    success = False

    try:
        if images:
            if len(images) == 1:
                success = send_single_photo(images[0], text)
            else:
                success = send_media_group(images, text)
        else:
            success = send_text(text)

    except Exception as e:
        print(f"ERROR kirim pesan ke-{index}: {e}")

    if success:
        print(f"Pesan ke-{index} BERHASIL")
    else:
        print(f"Pesan ke-{index} GAGAL (lanjut ke berikutnya)")


def main():
    if not BOT_TOKEN:
        fail("TELEGRAM_BOT_TOKEN belum di-set.")
    if not CHAT_ID:
        fail("TELEGRAM_CHAT_ID belum di-set.")

    messages = load_messages()

    print(f"Total pesan: {len(messages)}")

    for idx, item in enumerate(messages, start=1):
        send_item(item, idx)

        if idx < len(messages):
            print(f"Tunggu {DELAY_BETWEEN_MESSAGES} detik...\n")
            time.sleep(DELAY_BETWEEN_MESSAGES)

    print("\nSELESAI: Semua pesan sudah diproses.")


if __name__ == "__main__":
    main()
