"""
filters.py - rent / rooms / district filters for the apartment bot.

Configure in .env (all optional, empty = filter off):
    MAX_RENT=1500
    MIN_ROOMS=2
    DISTRICTS=mitte,kreuzberg,friedrichshain,neukölln

Rule of thumb: if a value can't be found in the listing text,
the listing is let through, so you never miss one because of
missing info.
"""

import os
import re

MAX_RENT = float(os.getenv("MAX_RENT") or 0) or None
MIN_ROOMS = float(os.getenv("MIN_ROOMS") or 0) or None
DISTRICTS = [
    d.strip().lower()
    for d in os.getenv("DISTRICTS", "").split(",")
    if d.strip()
]

RENT_RE = re.compile(r"(\d[\d.,]*)\s*(?:€|eur\b|euro\b)", re.IGNORECASE)
ROOMS_RE = re.compile(
    r"(\d+(?:[.,]\d)?)\s*[- ]?\s*(?:zimmer|zi\b|room)", re.IGNORECASE
)


def parse_number(raw):
    """'1.450' -> 1450, '1.450,50' -> 1450.5, '2,5' -> 2.5."""
    s = raw.strip().rstrip(".,")
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+", s):
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return None


def find_rent(text):
    m = RENT_RE.search(text)
    return parse_number(m.group(1)) if m else None


def find_rooms(text):
    m = ROOMS_RE.search(text)
    return parse_number(m.group(1)) if m else None


def passes_filters(text):
    """Return True if the listing text passes all active filters."""
    if MAX_RENT:
        rent = find_rent(text)
        if rent is not None and rent > MAX_RENT:
            return False

    if MIN_ROOMS:
        rooms = find_rooms(text)
        if rooms is not None and rooms < MIN_ROOMS:
            return False

    if DISTRICTS:
        low = text.lower()
        if not any(d in low for d in DISTRICTS):
            return False

    return True


if __name__ == "__main__":
    # Quick self-test: python3 filters.py
    sample = "3 Zimmer Wohnung in Berlin Mitte. 75 sqm. 1.450 EUR warm."
    print("rent :", find_rent(sample))
    print("rooms:", find_rooms(sample))
    print("passes:", passes_filters(sample))

