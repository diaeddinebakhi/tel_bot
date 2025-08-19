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
EVERY_MINUTES = int(os.environ.get("EVERY_MINUTES", "60"))  # default 3 hours
PORT = int(os.environ.get("PORT", "5000"))      # Render provides $PORT

TG_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

# ------------------ Lessons ------------------
# You can add as many lessons as you want here
lessons = [
    {
        "part1": """📘 *Introduction: Cosine Similarity*

Cosine similarity is a fundamental concept in machine learning and natural language processing.  
It measures how similar two vectors are based on the *angle* between them, while ignoring their length (magnitude).  

💡 Intuition:  
Imagine two arrows starting from the same point. If they point in exactly the same direction, they are *very similar* (cosine = 1). If they are perpendicular, they are completely unrelated (cosine = 0). If they point in opposite directions, they are negatively related (cosine = -1).

This makes cosine similarity especially useful when comparing text embeddings, because documents can have different lengths, but still have very similar meanings.""",

        "part2": """📐 *Math Behind Cosine Similarity*

The formula for cosine similarity between two vectors **A** and **B** is:

cos(θ) = (A · B) / (||A|| ||B||)

Where:
- **A · B** is the dot product of A and B  
- **||A||** is the magnitude (length) of A  
- **||B||** is the magnitude of B  
- **θ** is the angle between the vectors  

👉 Properties:
- cos(θ) = 1 → Vectors are identical in direction  
- cos(θ) = 0 → Vectors are orthogonal (no similarity)  
- cos(θ) = -1 → Vectors are opposite  

Unlike Euclidean distance, cosine similarity doesn’t care about how *long* the vectors are, just whether they point in a similar direction. That’s why it’s so powerful in text comparison!""",

        "part3": """🌍 *Example & Real-Life Application*

Let’s compare two short documents:

Doc1: "I love machine learning and artificial intelligence."  
Doc2: "Artificial intelligence and machine learning are amazing fields."

Even though the exact words differ slightly, the *meaning* is nearly the same.  
When we represent both documents as word embeddings (high-dimensional vectors) and compute cosine similarity, the result will be very close to **1.0**, meaning they are highly similar.

🔧 Real-World Applications:
- **Search Engines:** Ranking documents by similarity to a query.  
- **Chatbots:** Matching user questions to stored FAQ answers.  
- **Recommendation Systems:** Suggesting items similar to what you like.  
- **Plagiarism Detection:** Identifying text with overlapping meaning, not just exact wording.  

✅ Cosine similarity is the backbone of modern *semantic search* and RAG (Retrieval-Augmented Generation) systems."""
    },
    {
        "part1": """📘 *Introduction: Euclidean Distance*

Euclidean distance is the most basic and intuitive measure of distance.  
It represents the straight-line distance between two points in space.  

Think of how you would measure the distance between two points on a piece of paper using a ruler. That’s exactly what Euclidean distance does.""",

        "part2": """📐 *Math Behind Euclidean Distance*

For two points A(x1, y1) and B(x2, y2) in 2D space, the distance is:

d(A,B) = sqrt((x2 - x1)^2 + (y2 - y1)^2)

In n-dimensional space, the formula generalizes to:

d(A,B) = sqrt( Σ (ai - bi)^2 ), where i runs from 1 to n.

👉 Intuition:  
It’s like applying the Pythagorean theorem in higher dimensions.  
This is why Euclidean distance is often called "L2 norm" in machine learning.""",

        "part3": """🌍 *Example & Real-Life Application*

Example: A = (1,2), B = (4,6)  
d = sqrt((4-1)^2 + (6-2)^2) = sqrt(9 + 16) = sqrt(25) = 5

Real-World Applications:
- **Clustering (K-Means):** Assigning data points to the nearest cluster center.  
- **Nearest Neighbors Search:** Finding the closest data points in classification/regression.  
- **Computer Vision:** Comparing image feature vectors.  

✅ Euclidean distance is simple yet extremely powerful in geometry, machine learning, and data analysis."""
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
