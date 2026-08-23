import os
import feedparser
import requests
from feedgen.feed import FeedGenerator

# --- Config ---
FEED_URL = "https://habr.com/ru/rss/hub/artificial_intelligence/"
OPENROUTER_KEY = os.environ["OPENROUTER_KEY"]
MODEL = "qwen/qwen-2.5-72b-instruct:free"  # check openrouter.ai/models for current free options
OUTPUT_PATH = "docs/habr-ai-en.xml"
PUBLIC_FEED_URL = "https://raphaelbedani.github.io/habr-ai-digest/habr-ai-en.xml"  # update after Pages is live
MAX_ITEMS = 15


def translate(text):
    if not text:
        return ""
    r = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENROUTER_KEY}"},
        json={
            "model": MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": f"Translate the following Russian tech text to clear, concise English. Return only the translation, nothing else:\n\n{text}",
                }
            ],
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


def main():
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    source = feedparser.parse(FEED_URL)

    fg = FeedGenerator()
    fg.title("Habr AI Hub — Translated (EN)")
    fg.link(href=PUBLIC_FEED_URL, rel="self")
    fg.link(href="https://habr.com/ru/hubs/artificial_intelligence/", rel="alternate")
    fg.description("Daily auto-translated digest of Habr's Artificial Intelligence hub")
    fg.language("en")

    for entry in source.entries[:MAX_ITEMS]:
        title_en = translate(entry.get("title", ""))
        summary_en = translate(entry.get("summary", ""))

        fe = fg.add_entry()
        fe.title(title_en or entry.get("title", "Untitled"))
        fe.link(href=entry.get("link"))
        fe.description(summary_en)
        fe.guid(entry.get("link"), permalink=True)
        if entry.get("published"):
            fe.pubDate(entry.get("published"))

    fg.rss_file(OUTPUT_PATH)
    print(f"Wrote {len(source.entries[:MAX_ITEMS])} translated items to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
