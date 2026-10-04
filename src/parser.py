import re
import unicodedata


# ============================================================
# TEXT HELPERS
# ============================================================

def normalize_text(text):
    """Normalize Unicode and lowercase text."""
    if not text:
        return ""

    text = unicodedata.normalize("NFC", str(text))
    return text.lower().strip()


# ============================================================
# PRICE
# ============================================================

def extract_price(text):
    """
    Extract monthly rent from German or English listing text.

    Examples:
        855,20 € warm  -> 855.20
        1.200 EUR      -> 1200.0
        2.500 EUR      -> 2500.0
        1500 €         -> 1500.0
    """

    text = normalize_text(text)

    if not text:
        return None

    patterns = [
        # German thousands format:
        # 1.200 EUR / 2.500 € / 1.250,50 EUR
        # NOTE: \b only after "eur". A word boundary after "€" never
        # matches when a space follows, because "€" is not a word character.
        r"(?<![\d.])(\d{1,3}(?:\.\d{3})+(?:,\d{2})?)\s*(?:€|eur\b)",

        # Normal number:
        # 1500 EUR / 855,20 € / 1500 €
        r"(?<![\d.])(\d+(?:,\d{2})?)\s*(?:€|eur\b)",

        # Warmmiete 1.200 / Miete: 1500
        r"(?:warmmiete|miete|rent)\s*:?\s*"
        r"(\d{1,3}(?:\.\d{3})+(?:,\d{2})?)",

        r"(?:warmmiete|miete|rent)\s*:?\s*"
        r"(\d+(?:,\d{2})?)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if not match:
            continue

        raw = match.group(1)

        # German format: 1.250,50 -> 1250.50
        if "." in raw and "," in raw:
            raw = raw.replace(".", "").replace(",", ".")

        # German thousands: 1.250 -> 1250
        elif "." in raw:
            parts = raw.split(".")

            if len(parts) == 2 and len(parts[1]) == 3:
                raw = "".join(parts)

        # German decimal: 855,20 -> 855.20
        elif "," in raw:
            raw = raw.replace(",", ".")

        try:
            return float(raw)

        except ValueError:
            continue

    return None


# ============================================================
# ROOMS
# ============================================================

def extract_rooms(text):
    """Extract number of rooms from listing text."""

    text = normalize_text(text)

    if not text:
        return None

    patterns = [
        r"(\d+(?:[.,]\d+)?)\s*zimmer\b",
        r"(\d+(?:[.,]\d+)?)\s*rooms?\b",
        r"(\d+(?:[.,]\d+)?)\s*raum\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            raw = match.group(1).replace(",", ".")

            try:
                return float(raw)

            except ValueError:
                continue

    return None


# ============================================================
# SIZE
# ============================================================

def extract_size(text):
    """Extract apartment size in square meters."""

    text = normalize_text(text)

    if not text:
        return None

    patterns = [
        r"(\d+(?:[.,]\d+)?)\s*m²",
        r"(\d+(?:[.,]\d+)?)\s*qm\b",
        r"(\d+(?:[.,]\d+)?)\s*sqm\b",
        r"(\d+(?:[.,]\d+)?)\s*sq\s*m\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            raw = match.group(1).replace(",", ".")

            try:
                return float(raw)

            except ValueError:
                continue

    return None


# ============================================================
# DISTRICT
# ============================================================

BERLIN_DISTRICTS = [
    "mitte",
    "kreuzberg",
    "neukölln",
    "neukoelln",
    "friedrichshain",
    "prenzlauer berg",
    "charlottenburg",
    "wilmersdorf",
    "schöneberg",
    "schoeneberg",
    "tempelhof",
    "reinickendorf",
    "spandau",
    "lichtenberg",
    "treptow",
    "köpenick",
    "koepenick",
    "pankow",
    "steglitz",
    "zehlendorf",
    "marzahn",
    "hellersdorf",
]


def extract_district(text):
    """
    Extract a Berlin district from listing text.

    Handles Unicode consistently, including names such as
    Neukölln, Schöneberg and Köpenick.
    """

    text = normalize_text(text)

    if not text:
        return ""

    for district in BERLIN_DISTRICTS:

        if re.search(r"\b" + re.escape(district) + r"\b", text):

            # Standardize alternative spellings.
            if district == "neukoelln":
                return "neukölln"

            if district == "schoeneberg":
                return "schöneberg"

            if district == "koepenick":
                return "köpenick"

            return district

    return ""


# ============================================================
# WBS
# ============================================================

def detect_wbs(text):
    """
    Detect whether a listing requires a WBS.

    Examples:

        'Wohnung nur mit WBS'       -> True
        'WBS erforderlich'          -> True
        'WBS nötig'                 -> True
        'Normale Wohnung ohne WBS'  -> False
        'WBS nicht erforderlich'    -> False
    """

    text = normalize_text(text)

    if not text:
        return False

    # Explicit statements that WBS is NOT required.
    not_required_patterns = [
        r"\bohne\s+wbs\b",
        r"\bwbs\s+nicht\s+erforderlich\b",
        r"\bwbs\s+nicht\s+notwendig\b",
        r"\bwbs\s+nicht\s+nötig\b",
        r"\bwbs\s+not\s+required\b",
        r"\bno\s+wbs\b",
    ]

    for pattern in not_required_patterns:
        if re.search(pattern, text):
            return False

    # Statements that WBS IS required.
    required_patterns = [
        r"\bnur\s+mit\s+wbs\b",
        r"\bwbs\s+erforderlich\b",
        r"\bwbs\s+notwendig\b",
        r"\bwbs\s+nötig\b",
        r"\bwbs\s+required\b",
        r"\bwbs\s+needed\b",
    ]

    for pattern in required_patterns:
        if re.search(pattern, text):
            return True

    return False

