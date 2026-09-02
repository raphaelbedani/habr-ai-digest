import os
import time
import feedparser
import requests
from feedgen.feed import FeedGenerator
import sys

# --- Config ---
FEED_URL = "https://habr.com/ru/rss/hub/artificial_intelligence/"
OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY", "")
MODEL = "z-ai/glm-5.2:free"  # Reliable and cost-effective
OUTPUT_PATH = "docs/habr-ai-en.xml"
PUBLIC_FEED_URL = "https://raphaelbedani.github.io/habr-ai-digest/habr-ai-en.xml"
MAX_ITEMS = 15
TIMEOUT = 30  # Shorter timeout for faster model
MAX_RETRIES = 3
RETRY_BACKOFF = 3  # seconds, multiplied by attempt number


def translate(text):
    if not text or len(text.strip()) == 0:
        return ""

    if not OPENROUTER_KEY:
        print("ERROR: OPENROUTER_KEY environment variable not set")
        sys.exit(1)

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_KEY}",
                    "HTTP-Referer": "https://github.com/raphaelbedani/habr-ai-digest",
                    "X-Title": "Habr AI Digest"
                },
                json={
                    "model": MODEL,
                    "messages": [
                        {
                            "role": "user",
                            "content": f"Translate to English (keep technical terms):\n\n{text}",
                        }
                    ],
                    "temperature": 0.3,
                },
                timeout=TIMEOUT,
            )

            if r.status_code == 404:
                print(f"ERROR 404: Model '{MODEL}' not found or endpoint issue")
                print(f"Response: {r.text}")
                sys.exit(1)
            elif r.status_code in (401, 429):
                last_error = f"ERROR {r.status_code}: {'Invalid API key' if r.status_code == 401 else 'Rate limited - quota exceeded'}"
                if attempt < MAX_RETRIES:
                    wait = RETRY_BACKOFF * attempt
                    print(f"\n{last_error} (attempt {attempt}/{MAX_RETRIES}), retrying in {wait}s...", end=" ", flush=True)
                    time.sleep(wait)
                    continue
                print(f"\n{last_error} (giving up after {MAX_RETRIES} attempts)")
                sys.exit(1)
            elif r.status_code == 400:
                print(f"ERROR 400: Bad Request - {r.text}")
                sys.exit(1)

            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()

        except requests.exceptions.Timeout:
            last_error = f"ERROR: API request timed out after {TIMEOUT}s"
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF * attempt
                print(f"\n{last_error} (attempt {attempt}/{MAX_RETRIES}), retrying in {wait}s...", end=" ", flush=True)
                time.sleep(wait)
                continue
            print(f"\n{last_error} (giving up after {MAX_RETRIES} attempts)")
            sys.exit(1)
        except requests.exceptions.RequestException as e:
            print(f"ERROR: API request failed: {e}")
            sys.exit(1)
        except (KeyError, IndexError) as e:
            print(f"ERROR: Failed to parse API response: {e}")
            sys.exit(1)


def main():
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    print(f"Fetching feed from {FEED_URL}")
    source = feedparser.parse(FEED_URL)
    
    if not source.entries:
        print("ERROR: No entries found in feed")
        sys.exit(1)

    print(f"Found {len(source.entries)} entries, processing {MAX_ITEMS}")
    
    fg = FeedGenerator()
    fg.title("Habr AI Hub — Translated (EN)")
    fg.link(href=PUBLIC_FEED_URL, rel="self")
    fg.link(href="https://habr.com/ru/hubs/artificial_intelligence/", rel="alternate")
    fg.description("Daily auto-translated digest of Habr's Artificial Intelligence hub")
    fg.language("en")

    for i, entry in enumerate(source.entries[:MAX_ITEMS], 1):
        print(f"Translating {i}/{MAX_ITEMS}...", end=" ", flush=True)
        
        title_en = translate(entry.get("title", ""))
        summary_en = translate(entry.get("summary", ""))

        fe = fg.add_entry()
        fe.title(title_en or entry.get("title", "Untitled"))
        fe.link(href=entry.get("link"))
        fe.description(summary_en)
        fe.guid(entry.get("link"), permalink=True)
        if entry.get("published"):
            fe.pubDate(entry.get("published"))
        
        print("✓")

    fg.rss_file(OUTPUT_PATH)
    print(f"\n✅ Success: Wrote {len(source.entries[:MAX_ITEMS])} translated items to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
