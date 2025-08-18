import os
import time
import schedule
import random
import asyncio
from telegram import Bot
from groq import Groq


# # === Keys ===
# BOT_TOKEN = "7988613015:AAHRZC9BSl68CiD6pqb91bH88h3n3x7xxeo"
# CHAT_ID = "1931699367"
# GROQ_API_KEY = "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"

BOT_TOKEN = os.environ["7988613015:AAHRZC9BSl68CiD6pqb91bH88h3n3x7xxeo"]
CHAT_ID = os.environ["1931699367"]              # keep it as a string
GROQ_API_KEY = os.environ["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"]

bot = Bot(token=BOT_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

# === Categories ===
categories = {
    "news": "🌐 Share a trending AI topic or news item with source link.",
    "lesson": "📘 Explain a short AI concept in simple terms for beginners.",
    "idea": "💡 Suggest a creative AI idea or use case.",
    "tool": "🔧 Introduce a new AI technology or tool with a link.",
    "research": "📄 Summarize a recent AI research paper with source link."
}

# === Generate content using Groq ===
def generate_content(category):
    prompt = f"Generate an engaging and simple message for category: {categories[category]}"
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",   # can also use "llama-3.1-70b-versatile"
        messages=[
            {"role": "system", "content": "You are an AI news and learning assistant. Use friendly tone, clear explanations, and always include a source link if possible."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=200,
        temperature=0.8
    )
    return response.choices[0].message.content.strip()

# === Send update ===
async def send_update():
    category = random.choice(list(categories.keys()))
    message = generate_content(category)
    await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="Markdown")
    print(f"✅ Sent ({category}): {message}")

def job():
    asyncio.run(send_update())

schedule.every(3).hours.do(job)

print("🤖 Bot started... sending AI updates every 3 hours.")
job()  # send one immediately

while True:
    schedule.run_pending()
    time.sleep(60)
