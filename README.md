# Berlin Apartment Alert Bot

A Python bot that watches Berlin apartment listing RSS feeds, filters them against my requirements, scores the matches, and sends instant alerts to Telegram.

![Python](https://img.shields.io/badge/python-3.12-blue)
![Tests](https://img.shields.io/badge/tests-unittest-green)

## Why

Good apartments in Berlin disappear within hours. This bot checks the feeds automatically and only notifies me about listings that fit my budget, size, district and WBS situation, so I can respond first.

## How it works

1. **Fetch**: reads the RSS feeds of apartment listing sites.
2. **Parse**: extracts price, rooms, size, district and WBS requirement from the German or English listing text (`src/parser.py`).
3. **Filter**: rejects listings that are too expensive, too small, outside the target districts, require a WBS, or contain excluded keywords like WG or Zwischenmiete (`src/filters.py`).
4. **Score**: ranks the remaining listings by how well they match (`calculate_score`).
5. **Notify**: sends new matches to Telegram and remembers them in `seen_listings.json`, so nothing is sent twice.

## Project structure

```
berlin-apartment-bot/
├── main.py            # runs the bot
├── get_chat_id.py     # helper to find your Telegram chat ID
├── src/
│   ├── parser.py      # price / rooms / size / district / WBS extraction
│   └── filters.py     # requirement checks
├── tests/             # unit tests
├── requirements.txt
├── .env.example       # copy to .env and fill in
└── test_feed.xml      # sample feed for testing
```

## Setup

```bash
git clone https://github.com/logan0808/Berlin-apartment-bot.git
cd Berlin-apartment-bot
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Open `.env` and fill in the values listed in `.env.example` (your Telegram bot token and chat ID). Use `get_chat_id.py` to find your chat ID.

## Run

```bash
python main.py
```

## Tests

```bash
python -m unittest discover
```

The tests cover the parser (German price formats, rooms, size, districts, WBS detection), the filters and the scoring.

## Security

Never commit `.env`. It is listed in `.gitignore` and holds your Telegram token.

## Tech

Python 3.12, RSS parsing, regular expressions, Telegram Bot API, unittest.

## Roadmap

- Add more listing sources
- Run on a schedule (cron or a small server)
- Tune scoring weights
