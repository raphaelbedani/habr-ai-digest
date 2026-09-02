import os
import time
import feedparser
import requests
from feedgen.feed import FeedGenerator
import sys
import json

# --- Config ---
FEED_URL = "https://habr.com/ru/rss/hub/artificial_intelligence/"
OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY", "")
MODEL = "z-ai/glm-5.2:free"
OUTPUT_PATH = "docs/habr-ai-en.xml"
PUBLIC_FEED_URL = "https://raphaelbedani.github.io/habr-ai-digest/habr-ai-en.xml"
MAX_ITEMS = 15
TIMEOUT = 30
MAX_RETRIES = 3
RETRY_BACKOFF = 3


def translate_item(title, summary):
    if not OPENROUTER_KEY:
        print("ERROR: OPENROUTER_KEY environment variable not set")
        sys.exit(1)

    prompt = f"""
Translate the following Habr article title and summary from Russian to English.
Keep technical terminology accurate.

Return ONLY valid JSON in this format:
{{"title": "...", "summary": "..."}}

TITLE:
{title}

SUMMARY:
{summary}
"""

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_KEY}",
                    "HTTP-Referer": "https://github.com/raphaelbedani/habr-ai-digest",
                    "X-Title": "Habr AI Digest",
                },
                json={
                    "model": MODEL,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ],
                    "temperature": 0.3,
                },
                timeout=TIMEOUT,
            )

            if r.status_code == 404:
                print(f"\nERROR 404: Model '{MODEL}' not found")
                print(f"Response: {r.text}")
                sys.exit(1)

            elif r.status_code == 402:
                print("\nERROR 402: OpenRouter rejected the request")
                print(f"Response: {r.text}")
                sys.exit(1)

            elif r.status_code in (401, 429):
                error = (
                    "Invalid API key"
                    if r.status_code == 401
                    else "Rate limited / quota exceeded"
                )

                if attempt < MAX_RETRIES:
                    wait = RETRY_BACKOFF * attempt
                    print(
                        f"\nERROR {r.status_code}: {error} "
                        f"(attempt {attempt}/{MAX_RETRIES}), "
                        f"retrying in {wait}s...",
                        end=" ",
                        flush=True,
                    )
                    time.sleep(wait)
                    continue

                print(
                    f"\nERROR {r.status_code}: {error} "
                    f"(giving up after {MAX_RETRIES} attempts)"
                )
                sys.exit(1)

            elif r.status_code == 400:
                print(f"\nERROR 400: Bad Request")
                print(f"Response: {r.text}")
                sys.exit(1)

            r.raise_for_status()

            content = r.json()["choices"][0]["message"]["content"].strip()

            # Handle models that wrap JSON in markdown fences
            if content.startswith("```"):
                content = content.strip("`")
                if content.startswith("json"):
                    content = content[4:].strip()

            result = json.loads(content)

            return (
                result.get("title", title),
                result.get("summary", summary),
            )

        except requests.exceptions.Timeout:
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF * attempt
                print(
                    f"\nERROR: API timed out after {TIMEOUT}s "
                    f"(attempt {attempt}/{MAX_RETRIES}), "
                    f"retrying in {wait}s...",
                    end=" ",
                    flush=True,
                )
                time.sleep(wait)
                continue

            print(
                f"\nERROR: API timed out after {TIMEOUT}s "
                f"(giving up after {MAX_RETRIES} attempts)"
            )
            sys.exit(1)

        except requests.exceptions.RequestException as e:
            print(f"\nERROR: API request failed: {e}")
            sys.exit(1)

        except (KeyError, IndexError, json.JSONDecodeError) as e:
            print(f"\nERROR: Failed to parse API response: {e}")
            print(f"Raw response: {r.text}")
            sys.exit(1)


def main():
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    print(f"Fetching feed from {FEED_URL}")
    source = feedparser.parse(FEED_URL)

    if not source.entries:
        print("ERROR: No entries found in feed")
        sys.exit(1)

    items = source.entries[:MAX_ITEMS]

    print(f"Found {len(source.entries)} entries, processing {len(items)}")

    fg = FeedGenerator()
    fg.title("Habr AI Hub — Translated (EN)")
    fg.link(href=PUBLIC_FEED_URL, rel="self")
    fg.link(
        href="https://habr.com/ru/hubs/artificial_intelligence/",
        rel="alternate",
    )
    fg.description(
        "Daily auto-translated digest of Habr's Artificial Intelligence hub"
    )
    fg.language("en")

    for i, entry in enumerate(items, 1):
        print(f"Translating {i}/{len(items)}...", end=" ", flush=True)

        title = entry.get("title", "")
        summary = entry.get("summary", "")

        title_en, summary_en = translate_item(title, summary)

        fe = fg.add_entry()
        fe.title(title_en or title or "Untitled")
        fe.link(href=entry.get("link"))
        fe.description(summary_en)
        fe.guid(entry.get("link"), permalink=True)

        if entry.get("published"):
            fe.pubDate(entry.get("published"))

        print("✓")

    fg.rss_file(OUTPUT_PATH)

    print(
        f"\n✅ Success: Wrote {len(items)} translated items "
        f"to {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
