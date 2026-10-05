"""
Berlin Apartment Alert Bot
==========================

Features:
- Multiple RSS/Atom feeds
- 1-3 room filtering
- Maximum rent filtering
- Minimum size filtering
- District filtering
- Preferred district scoring
- WBS filtering
- Excluded keywords
- German rent parsing
- Match scoring
- SQLite database
- Duplicate protection
- Telegram alerts
- Telegram commands

Telegram commands:
    /start
    /help
    /latest
    /settings
    /stats
    /pause
    /resume

Run:
    python3 main.py

Stop:
    Ctrl+C
"""

import os
import re
import time
import html
import sqlite3
import logging
import hashlib

import requests
import feedparser
from dotenv import load_dotenv


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

RSS_FEEDS = [
    url.strip()
    for url in os.getenv("RSS_FEEDS", "").split(",")
    if url.strip()
]

POLL_INTERVAL_SECONDS = int(
    os.getenv("POLL_INTERVAL_SECONDS", "300")
)

DB_FILE = os.getenv(
    "DB_FILE",
    "listings.db"
)

MIN_ROOMS = float(
    os.getenv("MIN_ROOMS", "1")
)

MAX_ROOMS = float(
    os.getenv("MAX_ROOMS", "3")
)

MAX_RENT = float(
    os.getenv("MAX_RENT", "1500")
)

MIN_SIZE = float(
    os.getenv("MIN_SIZE", "0")
)

DISTRICTS = {
    item.strip().lower()
    for item in os.getenv("DISTRICTS", "").split(",")
    if item.strip()
}

PREFERRED_DISTRICTS = {
    item.strip().lower()
    for item in os.getenv("PREFERRED_DISTRICTS", "").split(",")
    if item.strip()
}

WBS_REQUIREMENT = os.getenv(
    "WBS",
    "any"
).lower().strip()

EXCLUDE_KEYWORDS = {
    item.strip().lower()
    for item in os.getenv(
        "EXCLUDE_KEYWORDS",
        "wg,wg-zimmer,wohngemeinschaft,zwischenmiete"
    ).split(",")
    if item.strip()
}

BASELINE_ON_START = (
    os.getenv(
        "BASELINE_ON_START",
        "false"
    ).lower()
    == "true"
)


# ============================================================
# RUNTIME STATE
# ============================================================

PAUSED = False
TELEGRAM_OFFSET = 0


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

log = logging.getLogger("apartment_bot")


# ============================================================
# BERLIN DISTRICTS
# ============================================================

BERLIN_DISTRICTS = {
    "mitte",
    "friedrichshain",
    "kreuzberg",
    "pankow",
    "prenzlauer berg",
    "charlottenburg",
    "wilmersdorf",
    "spandau",
    "steglitz",
    "zehlendorf",
    "tempelhof",
    "schöneberg",
    "neukölln",
    "treptow",
    "köpenick",
    "lichtenberg",
    "reinickendorf",
    "marzahn",
    "hellersdorf",
    "weißensee",
    "moabit",
    "tiergarten",
    "wedding",
    "gesundbrunnen",
    "schmargendorf",
    "grunewald",
    "dahlem",
    "adlershof",
    "britz",
    "rudow",
    "buckow",
    "oberschöneweide",
    "niederschöneweide",
    "baumschulenweg",
    "biesdorf",
}


# ============================================================
# DATABASE
# ============================================================

def get_connection():
    return sqlite3.connect(DB_FILE)


def init_database():
    """
    Create the listings table.

    Also performs a small migration if an older database
    does not yet contain the 'matched' column.
    """

    with get_connection() as conn:

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS listings (
                id TEXT PRIMARY KEY,
                title TEXT,
                price REAL,
                rooms REAL,
                size REAL,
                district TEXT,
                url TEXT,
                published_at TEXT,
                first_seen_at TEXT,
                match_score REAL,
                matched INTEGER DEFAULT 0
            )
            """
        )

        # Check existing columns.
        columns = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(listings)"
            ).fetchall()
        }

        # Add matched column to older databases.
        if "matched" not in columns:

            conn.execute(
                """
                ALTER TABLE listings
                ADD COLUMN matched INTEGER DEFAULT 0
                """
            )

            log.info(
                "Database migrated: added matched column."
            )

        conn.commit()


def listing_exists(listing_id):

    with get_connection() as conn:

        cursor = conn.execute(
            """
            SELECT 1
            FROM listings
            WHERE id = ?
            LIMIT 1
            """,
            (listing_id,)
        )

        return cursor.fetchone() is not None


def save_listing(
    listing_id,
    title,
    price,
    rooms,
    size,
    district,
    url,
    published_at,
    match_score,
    matched
):

    with get_connection() as conn:

        conn.execute(
            """
            INSERT OR IGNORE INTO listings (
                id,
                title,
                price,
                rooms,
                size,
                district,
                url,
                published_at,
                first_seen_at,
                match_score,
                matched
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?,
                datetime('now'), ?, ?
            )
            """,
            (
                listing_id,
                title,
                price,
                rooms,
                size,
                district,
                url,
                published_at,
                match_score,
                matched
            )
        )

        conn.commit()


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(value):

    if not value:
        return ""

    value = html.unescape(
        str(value)
    )

    value = re.sub(
        r"<[^>]+>",
        " ",
        value
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


# ============================================================
# PRICE PARSER
# ============================================================

def extract_price(text):
    """
    Extract monthly rent from common German/English formats.

    Examples:
        855,20 €   -> 855.20
        1.200 €    -> 1200.0
        1.200 EUR  -> 1200.0
        2.500 EUR  -> 2500.0
        1500 EUR   -> 1500.0
    """

    text = text.lower()

    patterns = [

        # German thousands format:
        # 1.200 €
        # 2.500 EUR
        # 1.250,50 €
        r"(?<![\d.])"
        r"(\d{1,3}(?:\.\d{3})+(?:,\d{2})?)"
        r"\s*(?:€|eur)",

        # Normal format:
        # 1200 EUR
        # 1500 €
        # 855,20 €
        r"(?<![\d.])"
        r"(\d+(?:,\d{2})?)"
        r"\s*(?:€|eur)",

        # Explicit rent wording:
        r"(?:warmmiete|rent|miete)"
        r"\s*:?\s*"
        r"(\d{1,3}(?:\.\d{3})+(?:,\d{2})?)",

        r"(?:warmmiete|rent|miete)"
        r"\s*:?\s*"
        r"(\d+(?:,\d{2})?)",
    ]

    for pattern in patterns:

        match = re.search(pattern, text)

        if not match:
            continue

        raw = match.group(1)

        # 1.250,50 -> 1250.50
        if "." in raw and "," in raw:
            raw = raw.replace(".", "").replace(",", ".")

        # 1.250 -> 1250
        elif "." in raw:
            parts = raw.split(".")

            if len(parts) == 2 and len(parts[1]) == 3:
                raw = "".join(parts)

        # 855,20 -> 855.20
        elif "," in raw:
            raw = raw.replace(",", ".")

        try:
            return float(raw)

        except ValueError:
            continue

    return None


# ============================================================
# ROOM PARSER
# ============================================================

def extract_rooms(text):

    text = text.lower()

    patterns = [
        r"(\d+(?:[.,]\d+)?)\s*[-]?\s*zimmer\b",
        r"(\d+(?:[.,]\d+)?)\s*rooms?\b",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text
        )

        if match:

            raw = (
                match.group(1)
                .replace(",", ".")
            )

            try:
                return float(raw)

            except ValueError:
                pass

    return None


# ============================================================
# SIZE PARSER
# ============================================================

def extract_size(text):

    text = text.lower()

    pattern = (
        r"(\d+(?:[.,]\d+)?)"
        r"\s*(?:m²|m2|qm|sqm)\b"
    )

    match = re.search(
        pattern,
        text
    )

    if not match:
        return None

    raw = (
        match.group(1)
        .replace(",", ".")
    )

    try:
        return float(raw)

    except ValueError:
        return None


# ============================================================
# DISTRICT PARSER
# ============================================================

def extract_district(text):

    text = text.lower()

    for district in BERLIN_DISTRICTS:

        if district in text:
            return district

    return ""


# ============================================================
# WBS DETECTION
# ============================================================

def detect_wbs(text):
    """
    Detect whether a listing requires a WBS.

    Important:
        "nur mit WBS" -> True
        "mit WBS" -> True
        "ohne WBS" -> False
        "kein WBS" -> False
    """

    text = text.lower()

    # Explicit negative wording must be checked first.
    negative_patterns = [
        r"ohne\s+wbs",
        r"kein\s+wbs",
        r"keinen\s+wbs",
        r"nicht\s+erforderlich.*wbs",
        r"wbs\s+nicht\s+erforderlich",
    ]

    for pattern in negative_patterns:

        if re.search(pattern, text):
            return False

    # Explicit positive WBS wording.
    positive_patterns = [
        r"nur\s+mit\s+wbs",
        r"mit\s+wbs",
        r"wbs\s+erforderlich",
        r"wbs\s+pflicht",
        r"wohnungsberechtigungsschein",
    ]

    for pattern in positive_patterns:

        if re.search(pattern, text):
            return True

    return False


# ============================================================
# FILTERING
# ============================================================

def matches_requirements(
    title,
    summary,
    price,
    rooms,
    size,
    district,
    wbs_required
):

    text = (
        f"{title} {summary}"
        .lower()
    )

    # Excluded keywords
    for keyword in EXCLUDE_KEYWORDS:

        if keyword in text:

            return False, (
                f"excluded keyword: {keyword}"
            )

    # Rooms
    if rooms is not None:

        if rooms < MIN_ROOMS:

            return False, (
                f"too few rooms: {rooms}"
            )

        if rooms > MAX_ROOMS:

            return False, (
                f"too many rooms: {rooms}"
            )

    # Rent
    if price is not None:

        if price > MAX_RENT:

            return False, (
                f"rent too high: €{price:.2f}"
            )

    # Size
    if MIN_SIZE > 0:

        if size is not None:

            if size < MIN_SIZE:

                return False, (
                    f"too small: {size:.1f} m²"
                )

    # District
    if DISTRICTS:

        if not district:

            return False, (
                "district not identified"
            )

        if district.lower() not in DISTRICTS:

            return False, (
                f"district not wanted: {district}"
            )

    # WBS
    if WBS_REQUIREMENT == "yes":

        if not wbs_required:

            return False, (
                "WBS required"
            )

    elif WBS_REQUIREMENT == "no":

        if wbs_required:

            return False, (
                "WBS listing excluded"
            )

    return True, "matches requirements"


# ============================================================
# MATCH SCORE
# ============================================================

def calculate_score(
    price,
    rooms,
    size,
    district,
    wbs_required
):

    score = 0

    # Budget: 30 points

    if price is None:

        score += 15

    else:

        percentage = (
            price / MAX_RENT
            if MAX_RENT > 0
            else 1
        )

        if percentage <= 0.80:
            score += 30

        elif percentage <= 0.90:
            score += 25

        elif percentage <= 1.00:
            score += 20

    # Rooms: 25 points

    if rooms is None:

        score += 12

    elif MIN_ROOMS <= rooms <= MAX_ROOMS:

        score += 25

    # Size: 20 points

    if MIN_SIZE <= 0:

        score += 20

    elif size is None:

        score += 10

    elif size >= MIN_SIZE:

        score += 20

    # District: 15 points

    if PREFERRED_DISTRICTS:

        if (
            district
            and district.lower()
            in PREFERRED_DISTRICTS
        ):

            score += 15

        else:

            score += 5

    else:

        score += 15

    # WBS: 10 points

    if WBS_REQUIREMENT == "any":

        score += 10

    elif WBS_REQUIREMENT == "yes":

        if wbs_required:
            score += 10

    elif WBS_REQUIREMENT == "no":

        if not wbs_required:
            score += 10

    return min(
        int(score),
        100
    )


# ============================================================
# LISTING ID
# ============================================================

def get_listing_id(entry):

    possible_ids = [
        entry.get("id"),
        entry.get("guid"),
        entry.get("link"),
    ]

    for value in possible_ids:

        if value:
            return str(value).strip()

    title = clean_text(
        entry.get("title", "")
    )

    summary = clean_text(
        entry.get("summary", "")
    )

    raw = (
        f"{title}|{summary}"
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


# ============================================================
# TELEGRAM API
# ============================================================

def telegram_api(
    method,
    data=None,
    params=None,
):
    url = (
        f"https://api.telegram.org/"
        f"bot{BOT_TOKEN}/{method}"
    )

    for attempt in range(3):
        try:
            response = requests.post(
                url,
                data=data or {},
                params=params or {},
                timeout=10,
            )

            if response.status_code == 429:
                try:
                    retry_after = response.json().get(
                        "parameters", {}
                    ).get("retry_after", 5)
                except ValueError:
                    retry_after = 5

                log.warning(
                    "Telegram rate limit reached. "
                    "Retrying in %s seconds.",
                    retry_after,
                )

                time.sleep(retry_after)
                continue

            if not response.ok:
                log.error(
                    "Telegram API error: %s",
                    response.text,
                )
                return None

            return response.json()

        except requests.RequestException as error:
            log.error(
                "Telegram request failed: %s",
                error,
            )
            return None

    log.error(
        "Telegram API failed after %s attempts.",
        3,
    )
    return None


def send_simple_message(text):

    return telegram_api(
        "sendMessage",
        data={
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
        }
    )


# ============================================================
# APARTMENT ALERT
# ============================================================

def send_telegram_alert(
    title,
    summary,
    link,
    price,
    rooms,
    size,
    district,
    wbs_required,
    score
):

    safe_title = html.escape(
        title
    )

    safe_summary = html.escape(
        summary[:500]
    )

    if link:

        safe_link = html.escape(
            link,
            quote=True
        )

        link_html = (
            f'<a href="{safe_link}">'
            f"Open listing"
            f"</a>"
        )

    else:

        link_html = (
            "No listing link"
        )

    price_text = (
        f"€{price:,.2f}"
        if price is not None
        else "Not found"
    )

    rooms_text = (
        f"{rooms:g}"
        if rooms is not None
        else "Not found"
    )

    size_text = (
        f"{size:.1f} m²"
        if size is not None
        else "Not found"
    )

    district_text = (
        district.title()
        if district
        else "Not detected"
    )

    wbs_text = (
        "🔖 WBS required"
        if wbs_required
        else "✅ No WBS required"
    )

    message = (
        f"🏠 <b>{safe_title}</b>\n\n"
        f"💰 <b>Rent:</b> {price_text}\n"
        f"🛏 <b>Rooms:</b> {rooms_text}\n"
        f"📐 <b>Size:</b> {size_text}\n"
        f"📍 <b>District:</b> {district_text}\n"
        f"📄 <b>WBS:</b> {wbs_text}\n"
        f"⭐ <b>Match:</b> {score}/100\n\n"
        f"{safe_summary}\n\n"
        f"🔗 {link_html}"
    )

    result = telegram_api(
        "sendMessage",
        data={
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }
    )

    if result is not None:
        time.sleep(3)

    return result is not None


# ============================================================
# LATEST LISTINGS
# ============================================================

def get_latest_listings(limit=5):

    with get_connection() as conn:

        cursor = conn.execute(
            """
            SELECT
                title,
                price,
                rooms,
                size,
                district,
                url,
                match_score,
                matched
            FROM listings
            ORDER BY rowid DESC
            LIMIT ?
            """,
            (limit,)
        )

        return cursor.fetchall()


def format_latest():

    listings = get_latest_listings(5)

    if not listings:

        return (
            "🏠 <b>Latest listings</b>\n\n"
            "No listings stored yet."
        )

    message = (
        "🏠 <b>Latest tracked listings</b>\n\n"
    )

    for index, listing in enumerate(
        listings,
        start=1
    ):

        (
            title,
            price,
            rooms,
            size,
            district,
            url,
            score,
            matched
        ) = listing

        price_text = (
            f"€{price:,.2f}"
            if price is not None
            else "?"
        )

        rooms_text = (
            f"{rooms:g}"
            if rooms is not None
            else "?"
        )

        status = (
            "✅ Match"
            if matched
            else "❌ Filtered"
        )

        message += (
            f"<b>{index}. "
            f"{html.escape(title)}</b>\n"
            f"💰 {price_text} | "
            f"🛏 {rooms_text} rooms\n"
            f"⭐ {score:.0f}/100 | "
            f"{status}\n"
        )

        if url:

            safe_url = html.escape(
                url,
                quote=True
            )

            message += (
                f'🔗 <a href="{safe_url}">'
                f"Open</a>\n"
            )

        message += "\n"

    return message


# ============================================================
# SETTINGS
# ============================================================

def format_settings():

    districts = (
        ", ".join(
            sorted(DISTRICTS)
        )
        if DISTRICTS
        else "All"
    )

    preferred = (
        ", ".join(
            sorted(PREFERRED_DISTRICTS)
        )
        if PREFERRED_DISTRICTS
        else "None"
    )

    excluded = ", ".join(
        sorted(EXCLUDE_KEYWORDS)
    )

    status = (
        "⏸ PAUSED"
        if PAUSED
        else "🟢 RUNNING"
    )

    return (
        "🏠 <b>Apartment Bot Settings</b>\n\n"
        f"Status: {status}\n"
        f"Rooms: {MIN_ROOMS:g}–{MAX_ROOMS:g}\n"
        f"Max rent: €{MAX_RENT:,.2f}\n"
        f"Min size: {MIN_SIZE:g} m²\n"
        f"Districts: {html.escape(districts)}\n"
        f"Preferred: {html.escape(preferred)}\n"
        f"WBS: {html.escape(WBS_REQUIREMENT)}\n"
        f"Excluded: {html.escape(excluded)}\n"
        f"Feeds: {len(RSS_FEEDS)}\n"
        f"Check interval: {POLL_INTERVAL_SECONDS}s"
    )


# ============================================================
# STATISTICS
# ============================================================

def get_stats():

    with get_connection() as conn:

        total = conn.execute(
            """
            SELECT COUNT(*)
            FROM listings
            """
        ).fetchone()[0]

        matching = conn.execute(
            """
            SELECT COUNT(*)
            FROM listings
            WHERE matched = 1
            """
        ).fetchone()[0]

        average_score = conn.execute(
            """
            SELECT AVG(match_score)
            FROM listings
            WHERE matched = 1
            """
        ).fetchone()[0]

    average_text = (
        f"{average_score:.1f}"
        if average_score is not None
        else "0"
    )

    status = (
        "⏸ Paused"
        if PAUSED
        else "🟢 Running"
    )

    return (
        "📊 <b>Apartment Bot Statistics</b>\n\n"
        f"Status: {status}\n"
        f"Listings tracked: {total}\n"
        f"Matching listings: {matching}\n"
        f"Average match score: "
        f"{average_text}/100\n"
        f"Feeds monitored: {len(RSS_FEEDS)}"
    )


# ============================================================
# TELEGRAM COMMANDS
# ============================================================

def handle_command(command):

    global PAUSED

    command = command.strip().lower()

    # Remove @botname if Telegram adds it.
    command = command.split("@")[0]

    if command in (
        "/start",
        "/help"
    ):

        send_simple_message(
            "🏠 <b>Berlin Apartment Alert Bot</b>\n\n"
            "I monitor apartment feeds and send "
            "matching listings.\n\n"
            "<b>Commands:</b>\n"
            "/latest — newest tracked listings\n"
            "/settings — current search settings\n"
            "/stats — bot statistics\n"
            "/pause — pause alerts\n"
            "/resume — resume alerts\n"
            "/help — show this menu"
        )

    elif command == "/latest":

        send_simple_message(
            format_latest()
        )

    elif command == "/settings":

        send_simple_message(
            format_settings()
        )

    elif command == "/stats":

        send_simple_message(
            get_stats()
        )

    elif command == "/pause":

        PAUSED = True

        send_simple_message(
            "⏸ <b>Alerts paused.</b>\n\n"
            "The bot will continue checking listings, "
            "but matching listings will not be sent "
            "to Telegram."
        )

        log.info(
            "Alerts paused from Telegram."
        )

    elif command == "/resume":

        PAUSED = False

        send_simple_message(
            "▶️ <b>Alerts resumed.</b>\n\n"
            "New matching listings will be sent again."
        )

        log.info(
            "Alerts resumed from Telegram."
        )

    else:

        send_simple_message(
            "❓ Unknown command.\n\n"
            "Use /help to see the available commands."
        )


# ============================================================
# TELEGRAM UPDATE CHECK
# ============================================================

def check_telegram_commands():

    global TELEGRAM_OFFSET

    params = {
        "offset": TELEGRAM_OFFSET + 1,
        "timeout": 1,
        "allowed_updates": ["message"],
    }

    result = telegram_api(
        "getUpdates",
        params=params
    )

    if not result:

        return

    for update in result.get(
        "result",
        []
    ):

        TELEGRAM_OFFSET = update[
            "update_id"
        ]

        message = update.get(
            "message"
        )

        if not message:
            continue

        chat = message.get(
            "chat",
            {}
        )

        chat_id = str(
            chat.get(
                "id",
                ""
            )
        )

        # Only respond to the configured chat.
        if chat_id != str(CHAT_ID):
            continue

        text = message.get(
            "text",
            ""
        ).strip()

        if not text.startswith("/"):
            continue

        command = text.split()[0]

        handle_command(
            command
        )


# ============================================================
# PROCESS FEED
# ============================================================

def process_feed(
    feed_url,
    baseline=False
):
    log.info(
        "Checking feed: %s",
        feed_url
    )

    try:
        if "degewo.de/immosuche" in feed_url:
            from degewo_source import fetch_degewo
            entries = fetch_degewo(feed_url, max_pages=10, delay=2)
            feed = None

        elif "gewobag.de/" in feed_url:
            from gewobag_source import fetch_gewobag
            entries = fetch_gewobag(feed_url, max_pages=6, delay=2)
            feed = None

        else:
            feed = feedparser.parse(feed_url)
            entries = feed.entries

    except Exception as error:
        log.error(
            "Could not parse feed %s: %s",
            feed_url,
            error
        )
        return 0, 0

    if (
        feed is not None
        and getattr(feed, "bozo", 0)
        and not entries
    ):
        log.warning(
            "Feed returned no entries: %s",
            feed_url
        )
        return 0, 0

    log.info(
        "Feed returned %d listing(s).",
        len(entries)
    )

    new_count = 0
    alert_count = 0

    for entry in entries:

        listing_id = get_listing_id(
            entry
        )

        # SQLite is our duplicate protection.
        if listing_exists(
            listing_id
        ):
            continue

        title = clean_text(
            entry.get(
                "title",
                "New apartment listing"
            )
        )

        summary = clean_text(
            entry.get(
                "summary",
                entry.get(
                    "description",
                    ""
                )
            )
        )

        link = clean_text(
            entry.get(
                "link",
                ""
            )
        )

        published_at = clean_text(
            entry.get(
                "published",
                entry.get(
                    "updated",
                    ""
                )
            )
        )

        combined_text = (
            f"{title} {summary}"
        )

        price = extract_price(
            combined_text
        )

        rooms = extract_rooms(
            combined_text
        )

        size = extract_size(
            combined_text
        )

        district = extract_district(
            combined_text
        )

        wbs_required = detect_wbs(
            combined_text
        )

        matches, reason = (
            matches_requirements(
                title=title,
                summary=summary,
                price=price,
                rooms=rooms,
                size=size,
                district=district,
                wbs_required=wbs_required
            )
        )

        score = calculate_score(
            price=price,
            rooms=rooms,
            size=size,
            district=district,
            wbs_required=wbs_required
        )

        # Store every listing, including filtered listings.
        save_listing(
            listing_id=listing_id,
            title=title,
            price=price,
            rooms=rooms,
            size=size,
            district=district,
            url=link,
            published_at=published_at,
            match_score=score,
            matched=int(matches)
        )

        new_count += 1

        # First-run baseline:
        # store listings but don't send alerts.
        if baseline:

            log.info(
                "Baselined: %s",
                title
            )

            continue

        if not matches:

            log.info(
                "Filtered out: %s | %s",
                title,
                reason
            )

            continue

        if PAUSED:

            log.info(
                "Alert paused: %s",
                title
            )

            continue

        sent = send_telegram_alert(
            title=title,
            summary=summary,
            link=link,
            price=price,
            rooms=rooms,
            size=size,
            district=district,
            wbs_required=wbs_required,
            score=score
        )

        if sent:

            alert_count += 1

            log.info(
                "Alert sent: %s | score=%s/100",
                title,
                score
            )

    return new_count, alert_count


# ============================================================
# MAIN
# ============================================================

def main():

    # --------------------------------------------------------
    # Validate configuration
    # --------------------------------------------------------

    if not BOT_TOKEN:

        raise SystemExit(
            "Missing TELEGRAM_BOT_TOKEN "
            "in .env"
        )

    if not CHAT_ID:

        raise SystemExit(
            "Missing TELEGRAM_CHAT_ID "
            "in .env"
        )

    if not RSS_FEEDS:

        raise SystemExit(
            "Missing RSS_FEEDS "
            "in .env"
        )

    # --------------------------------------------------------
    # Database
    # --------------------------------------------------------

    init_database()

    # --------------------------------------------------------
    # Startup information
    # --------------------------------------------------------

    log.info(
        "Bot started. %d feed(s), every %ss.",
        len(RSS_FEEDS),
        POLL_INTERVAL_SECONDS
    )

    log.info(
        "Rooms: %.1f - %.1f | "
        "Max rent: €%.2f | "
        "Min size: %.1f m²",
        MIN_ROOMS,
        MAX_ROOMS,
        MAX_RENT,
        MIN_SIZE
    )

    log.info(
        "Districts: %s",
        ", ".join(
            sorted(DISTRICTS)
        )
        if DISTRICTS
        else "all"
    )

    log.info(
        "Preferred districts: %s",
        ", ".join(
            sorted(PREFERRED_DISTRICTS)
        )
        if PREFERRED_DISTRICTS
        else "none"
    )

    log.info(
        "WBS requirement: %s",
        WBS_REQUIREMENT
    )

    log.info(
        "Excluded keywords: %s",
        ", ".join(
            sorted(EXCLUDE_KEYWORDS)
        )
    )

    # --------------------------------------------------------
    # Optional baseline
    # --------------------------------------------------------

    if BASELINE_ON_START:

        log.info(
            "BASELINE_ON_START=true — "
            "current listings will be stored "
            "without alerts."
        )

        total_baselined = 0

        for feed_url in RSS_FEEDS:

            new_count, _ = process_feed(
                feed_url,
                baseline=True
            )

            total_baselined += new_count

        log.info(
            "Baseline complete: %d listing(s).",
            total_baselined
        )

    # --------------------------------------------------------
    # Startup Telegram message
    # --------------------------------------------------------

    send_simple_message(
        "🟢 <b>Apartment Bot started.</b>\n\n"
        "Use /help to see available commands."
    )

    # --------------------------------------------------------
    # Main loop
    # --------------------------------------------------------

    while True:

        # Check Telegram commands.
        check_telegram_commands()

        total_new = 0
        total_alerts = 0

        # Check all configured feeds.
        for feed_url in RSS_FEEDS:

            new_count, alert_count = (
                process_feed(
                    feed_url,
                    baseline=False
                )
            )

            total_new += new_count
            total_alerts += alert_count

        log.info(
            "Cycle complete: %d new listing(s), "
            "%d alert(s).",
            total_new,
            total_alerts
        )

        # Keep checking Telegram while waiting.
        for _ in range(
            POLL_INTERVAL_SECONDS
        ):

            check_telegram_commands()

            time.sleep(1)


# ============================================================
# START PROGRAM
# ============================================================

if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        log.info(
            "Bot stopped by user."
        )
