# bot.py
import os
import time
import logging
import random
import threading
import requests
import schedule
from flask import Flask
from groq import Groq

# ------------------ Config & Logging ------------------
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(message)s"
)

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]                 # string; group ids look like -100...
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
EVERY_MINUTES = int(os.environ.get("EVERY_MINUTES", "180"))  # default 3 hours
PORT = int(os.environ.get("PORT", "5000"))      # Render provides $PORT

TG_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

client = Groq(api_key=GROQ_API_KEY)

# ------------------ Content Rotation ------------------
CATEGORY_ORDER = ["news", "lesson", "idea", "tool", "research"]
_cat_index = 0

CATEGORY_PROMPTS = {
    "news": "🌐 Share a trending AI topic or news item that happened recently. "
            "Use simple, friendly language, add 1–2 sentences of context, and include ONE credible source link.",
    "lesson": "📘 Teach a short AI/ML concept for beginners (e.g., embeddings, overfitting, cross-validation). "
              "Explain clearly in 3–5 sentences with a tiny example. Include one link for further reading.",
    "idea": "💡 Propose a creative AI idea or use case (practical). Explain how it works and why it’s useful in 3–5 sentences.",
    "tool": "🔧 Introduce a new or notable AI tool/library/platform. Describe what it does, who it’s for, and include ONE official link.",
    "research": "📄 Summarize a recent AI research paper in 4–6 sentences (what, why, how, results, takeaway). Include ONE arXiv or official link."
}

SYSTEM_STYLE = (
    "You are an AI updates assistant. Write in clear, simple, friendly language. "
    "Avoid special Markdown characters that break Telegram (no unbalanced *, _, [, ]). "
    "Use one short title line with an emoji, then a concise explanation, then one link."
)

def next_category() -> str:
    global _cat_index
    cat = CATEGORY_ORDER[_cat_index % len(CATEGORY_ORDER)]
    _cat_index += 1
    return cat

# ------------------ Groq Generation ------------------
def generate_message(category: str) -> str:
    prompt = CATEGORY_PROMPTS[category]
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",   # you can switch to "llama-3.1-70b-versatile" for higher quality
            messages=[
                {"role": "system", "content": SYSTEM_STYLE},
                {"role": "user", "content": f"Category: {category}\nTask: {prompt}"}
            ],
            max_tokens=350,
            temperature=0.8
        )
        text = completion.choices[0].message.content.strip()
        return text
    except Exception as e:
        logging.exception("Groq generation failed")
        return f"⚠️ Could not generate {category} update this time."

# ------------------ Telegram Sender ------------------
def _split_chunks(text: str, limit: int = 4000):
    # Telegram max text is ~4096; keep margin
    parts = []
    while len(text) > limit:
        cut = text.rfind("\n", 0, limit)
        if cut == -1:
            cut = limit
        parts.append(text[:cut])
        text = text[cut:].lstrip()
    parts.append(text)
    return parts

def send_telegram(text: str):
    # Try Markdown first; if Telegram rejects, retry without parsing
    for part in _split_chunks(text):
        payload = {"chat_id": CHAT_ID, "text": part, "parse_mode": "Markdown"}
        try:
            r = requests.post(TG_API_URL, json=payload, timeout=20)
            if r.status_code == 429:
                retry_after = r.json().get("parameters", {}).get("retry_after", 5)
                logging.warning(f"Rate limited. Retrying after {retry_after}s.")
                time.sleep(retry_after)
                r = requests.post(TG_API_URL, json=payload, timeout=20)
            if r.status_code != 200 and "can't parse entities" in r.text.lower():
                logging.warning("Markdown parse error. Retrying without parse_mode.")
                r = requests.post(TG_API_URL, json={"chat_id": CHAT_ID, "text": part}, timeout=20)
            if r.status_code != 200:
                logging.error(f"Telegram error {r.status_code}: {r.text}")
            else:
                logging.info("Message part sent to Telegram.")
        except Exception:
            logging.exception("Failed to send message to Telegram")

# ------------------ Job ------------------
def send_update():
    category = next_category()
    logging.info(f"Generating category: {category}")
    msg = generate_message(category)
    logging.info(f"Sending category: {category}")
    send_telegram(msg)

# ------------------ Scheduler Thread ------------------
def scheduler_thread():
    logging.info(f"Scheduling updates every {EVERY_MINUTES} minutes.")
    schedule.every(EVERY_MINUTES).minutes.do(send_update)
    # Send one immediately on startup
    send_update()
    while True:
        schedule.run_pending()
        time.sleep(5)

# ------------------ Flask Keep-Alive ------------------
app = Flask(__name__)

@app.route("/")
def health():
    return "✅ AI Updates bot is running.", 200

@app.route("/trigger")
def trigger():
    # Manual trigger endpoint (useful for testing)
    threading.Thread(target=send_update, daemon=True).start()
    return "Triggered an update.", 200

def run_flask():
    logging.info(f"Starting HTTP server on port {PORT}…")
    app.run(host="0.0.0.0", port=PORT)

# ------------------ Main ------------------
if __name__ == "__main__":
    # Start the web server in a background thread so the process stays alive on Render
    threading.Thread(target=run_flask, daemon=True).start()
    # Start the scheduler loop in the main thread
    scheduler_thread()
