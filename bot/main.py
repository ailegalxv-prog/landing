"""ORBITA IX — бот запису на розбір (@AI_legal_practice_bot), раніше жив у n8n.

Юрист приходить із кнопки на orbita-ix.com (/start <мітка кнопки>), відповідає на три
питання — ім'я, фірма, контакт — і заявка приходить власнику через окремий бот
сповіщень (@legal_ai_post_bot). Усе, що людина пише поза анкетою, теж пересилається.

Токени й секрет вебхука — у змінних середовища (з Secret Manager), у коді їх немає.
Стан анкети тримається в пам'яті: сервіс запущено з max-instances=1. Якщо стан
загубився (перезапуск), повідомлення людини все одно доходить власнику як вільний текст.
"""
import hmac
import html
import json
import logging
import os
import threading
import urllib.request
from collections import OrderedDict
from datetime import datetime
from zoneinfo import ZoneInfo

from flask import Flask, jsonify, request

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("landing-bot")

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
NOTIFY_TOKEN = os.environ.get("NOTIFY_TOKEN", "")
NOTIFY_CHAT_IDS = [c.strip() for c in os.environ.get("NOTIFY_CHAT_IDS", "").split(",") if c.strip()]
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")
KYIV = ZoneInfo("Europe/Kyiv")
SOURCES = {"hero", "dock", "contact"}  # мітки кнопок сайту (public/index.html, data-cta)

TEXT_START = (
    "Вітаємо! Це ORBITA IX — автоматизуємо процеси юридичних фірм. "
    "Запишемо Вас на безкоштовний розбір: три короткі питання — і відповімо того ж дня.\n\n"
    "Як до Вас звертатися?"
)
TEXT_FIRM = "Як називається Ваша фірма чи практика?"
TEXT_CONTACT = (
    "Як з Вами зв'язатися? Натисніть «📱 Поділитися номером» "
    "або напишіть телефон чи інший зручний спосіб."
)
TEXT_DONE = "Дякуємо! Заявку отримали — відповімо сьогодні."
TEXT_FORWARDED = "Дякуємо! Передали Ваше повідомлення — відповімо сьогодні."
TEXT_ONLY_TEXT = "Напишіть, будь ласка, текстом — так ми точно його отримаємо."
BTN_PHONE = "📱 Поділитися номером"

_lock = threading.Lock()
_state = {}  # chat_id -> {"step": "name"|"firm"|"contact", "source": str, "name": str, "firm": str}
_seen = OrderedDict()  # update_id, щоб не обробляти повтори від Telegram


def tg(token, method, **params):
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{method}",
        data=json.dumps(params).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            ok = json.loads(r.read()).get("ok", False)
    except Exception as exc:  # мережа / Telegram недоступний / 4xx
        log.error("telegram %s failed: %s %s", method, type(exc).__name__, getattr(exc, "code", ""))
        return False
    if not ok:
        log.error("telegram %s returned ok=false", method)
    return ok


def say(chat_id, text, keyboard=None):
    params = {"chat_id": chat_id, "text": text}
    if keyboard is not None:
        params["reply_markup"] = keyboard
    return tg(BOT_TOKEN, "sendMessage", **params)


def notify(text):
    if not NOTIFY_CHAT_IDS:
        log.error("NOTIFY_CHAT_IDS is empty, lead not delivered")
        return False
    results = [tg(NOTIFY_TOKEN, "sendMessage", chat_id=c, text=text, parse_mode="HTML",
                  disable_web_page_preview=True) for c in NOTIFY_CHAT_IDS]
    return any(results)


def who(user):
    h = html.escape
    name = " ".join(x for x in (user.get("first_name"), user.get("last_name")) if x) or "без імені"
    if user.get("username"):
        return f"{h(name)} (@{h(user['username'])})"
    return f'<a href="tg://user?id={int(user.get("id", 0))}">{h(name)}</a>, id {int(user.get("id", 0))}'


def now():
    return datetime.now(KYIV).strftime("%d.%m.%Y %H:%M")


def lead_message(st, contact, user):
    h = html.escape
    return (
        "🔔 <b>Нова заявка з сайту</b>\n\n"
        f"👤 Ім'я: <b>{h(st.get('name', ''))}</b>\n"
        f"🏢 Фірма: <b>{h(st.get('firm', ''))}</b>\n"
        f"📞 Контакт: <b>{h(contact)}</b>\n"
        f"💬 Telegram: {who(user)}\n"
        f"📍 Кнопка на сайті: {h(st.get('source') or '—')}\n"
        f"🕒 {now()}"
    )


def free_message(text, user):
    return (
        "💬 <b>Повідомлення в боті сайту</b>\n\n"
        f"{html.escape(text)}\n\n"
        f"Від: {who(user)}\n"
        f"🕒 {now()}"
    )


def handle(msg):
    chat = msg.get("chat", {})
    if chat.get("type") != "private":
        return
    chat_id = chat["id"]
    user = msg.get("from", {})
    text = (msg.get("text") or "").strip()[:1000]

    if text.startswith("/start"):
        payload = text[len("/start"):].strip()
        with _lock:
            _state[chat_id] = {"step": "name", "source": payload if payload in SOURCES else ""}
        say(chat_id, TEXT_START, {"remove_keyboard": True})
        return

    with _lock:
        st = _state.get(chat_id)
        step = st["step"] if st else None

    if step == "contact":
        phone = (msg.get("contact") or {}).get("phone_number")
        contact = phone or text
        if not contact:
            say(chat_id, TEXT_ONLY_TEXT)
            return
        notify(lead_message(st, contact, user))
        with _lock:
            _state.pop(chat_id, None)
        say(chat_id, TEXT_DONE, {"remove_keyboard": True})
        return

    if not text:
        say(chat_id, TEXT_ONLY_TEXT)
        return

    if step == "name":
        with _lock:
            st.update(step="firm", name=text[:120])
        say(chat_id, TEXT_FIRM)
    elif step == "firm":
        with _lock:
            st.update(step="contact", firm=text[:200])
        say(chat_id, TEXT_CONTACT, {
            "keyboard": [[{"text": BTN_PHONE, "request_contact": True}]],
            "resize_keyboard": True,
            "one_time_keyboard": True,
        })
    else:
        # Поза анкетою (або стан загубився після перезапуску) — пересилаємо як є.
        notify(free_message(text, user))
        say(chat_id, TEXT_FORWARDED)


@app.get("/")
def health():
    return jsonify(ok=True)


@app.post("/telegram")
def webhook():
    got = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not WEBHOOK_SECRET or not hmac.compare_digest(got, WEBHOOK_SECRET):
        return jsonify(ok=False), 403
    update = request.get_json(silent=True) or {}
    uid = update.get("update_id")
    with _lock:
        if uid in _seen:
            return jsonify(ok=True)
        _seen[uid] = True
        while len(_seen) > 1000:
            _seen.popitem(last=False)
    try:
        if update.get("message"):
            handle(update["message"])
    except Exception:
        log.exception("update %s failed", uid)
    # Завжди 200: інакше Telegram повторюватиме те саме оновлення.
    return jsonify(ok=True)
