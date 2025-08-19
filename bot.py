# bot.py
import os
import time
import logging
import threading
import requests
import schedule
from flask import Flask

# ------------------ Config & Logging ------------------
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(message)s"
)

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]                 # string; group ids look like -100...
EVERY_MINUTES = int(os.environ.get("EVERY_MINUTES", "20"))  # default 3 hours
PORT = int(os.environ.get("PORT", "5000"))      # Render provides $PORT

TG_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

# ------------------ Lessons ------------------
# You can add as many lessons as you want here
lessons = [
    {
        "part1": "📘 *Introduction: Cosine Similarity*\n\nCosine similarity measures how similar two vectors are based on the angle between them. Think of it as how much two arrows point in the same direction, ignoring their length.",
        "part2": "📐 *Math Behind Cosine Similarity*\n\nFormula:\n\ncos(θ) = (A · B) / (||A|| ||B||)\n\nWhere:\n- A · B = dot product of vectors\n- ||A|| = magnitude of A\n- ||B|| = magnitude of B\n\ncos(θ)=1 → same direction, cos(θ)=0 → perpendicular, cos(θ)=-1 → opposite.",
        "part3": "🔧 *Real-Life Example*\n\nComparing two documents:\n- Doc1: 'I love data science and machine learning'\n- Doc2: 'Machine learning is amazing for data-driven science'\n\nAfter vectorization → cosine similarity ≈ 0.92 → very similar!\n\nThis is why search engines and RAG systems use cosine similarity."
    },
    {
        "part1": "📘 *Introduction: Euclidean Distance*\n\nEuclidean distance is the ordinary straight-line distance between two points in space.",
        "part2": "📐 *Math Behind Euclidean Distance*\n\nFor 2D points A(x1, y1), B(x2, y2):\n\nd(A,B) = sqrt((x2-x1)^2 + (y2-y1)^2)\n\nIn n dimensions:\n\nd(A,B) = sqrt( Σ (ai - bi)^2 )",
        "part3": "🔧 *Real-Life Example*\n\nIf A=(1,2) and B=(4,6):\n\nd = sqrt((4-1)^2 + (6-2)^2) = sqrt(9+16) = 5\n\nUsed in clustering (K-Means) to group similar data points."
    }
]

lesson_index = 0
part_index = 0
lock = threading.Lock()

# ------------------ Telegram Sender ------------------
def send_telegram(text: str):
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        r = requests.post(TG_API_URL, json=payload, timeout=20)
        if r.status_code != 200:
            logging.error(f"Telegram error {r.status_code}: {r.text}")
        else:
            logging.info("Lesson part sent to Telegram.")
    except Exception:
        logging.exception("Failed to send message to Telegram")

# ------------------ Job ------------------
def send_lesson_part():
    global lesson_index, part_index
    with lock:
        lesson = lessons[lesson_index % len(lessons)]
        parts = [lesson["part1"], lesson["part2"], lesson["part3"]]

        # send current part
        msg = parts[part_index]
        logging.info(f"Sending Lesson {lesson_index+1}, Part {part_index+1}")
        send_telegram(msg)

        # move to next part
        part_index += 1
        if part_index >= 3:
            part_index = 0
            lesson_index += 1  # move to next lesson after 3 parts

# ------------------ Scheduler Thread ------------------
def scheduler_thread():
    logging.info(f"Scheduling lessons every {EVERY_MINUTES} minutes.")
    # Send first part immediately on startup
    send_lesson_part()
    schedule.every(EVERY_MINUTES).minutes.do(send_lesson_part)
    while True:
        schedule.run_pending()
        time.sleep(5)

# ------------------ Flask Keep-Alive ------------------
app = Flask(__name__)

@app.route("/")
def health():
    return "✅ AI Lessons bot is running.", 200

@app.route("/trigger")
def trigger():
    threading.Thread(target=send_lesson_part, daemon=True).start()
    return "Triggered a lesson part.", 200

def run_flask():
    logging.info(f"Starting HTTP server on port {PORT}…")
    app.run(host="0.0.0.0", port=PORT)

# ------------------ Main ------------------
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    scheduler_thread()
