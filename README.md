# Habr AI Digest

Automatically translates the latest articles from Habr's Artificial Intelligence hub into English with **Gemini 2.5 Flash-Lite** and publishes them through GitHub Pages.

## What it does

- Reads the latest 15 items from the Habr AI RSS feed.
- Fetches each new article's full body.
- Translates the title, summary, and full article into English with `gemini-2.5-flash-lite`.
- Preserves links, images, HTML structure, and code blocks.
- Writes each translation to `docs/articles/<article-id>.html`.
- Publishes the latest translated items to `docs/habr-ai-en.xml`.
- Reuses cached translations, so existing articles do not consume another Gemini request.
- Runs once per day at 09:00 UTC and can also be triggered manually.

## Setup

1. Create a Gemini API key in Google AI Studio.
2. In this repository, create an Actions secret named `GEMINI_API_KEY`.
3. Run **Daily Habr AI Digest** manually once from the Actions tab, or wait for the daily schedule.

Optional environment variables:

- `GEMINI_MODEL` — defaults to `gemini-2.5-flash-lite`.
- `PUBLIC_BASE_URL` — defaults to `https://kadimazoran.github.io/habr-ai-digest`.

## Output

- Landing page: `https://kadimazoran.github.io/habr-ai-digest/`
- RSS feed: `https://kadimazoran.github.io/habr-ai-digest/habr-ai-en.xml`
- Full translations: `https://kadimazoran.github.io/habr-ai-digest/articles/<article-id>.html`

The translated pages link back to the original Habr article as the source of record.
