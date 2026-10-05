import requests
from urllib.parse import urljoin

HEADERS = {
    "User-Agent": "berlin-apartment-bot/1.0 (personal use)"
}

def fetch_gesobau(url):
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=20,
    )
    response.raise_for_status()

    data = response.json()

    if not isinstance(data, list):
        raise ValueError("Unexpected GESOBAU JSON format")

    entries = []

    for item in data:
        raw = item.get("raw", {})

        detail = item.get("detail", "")
        listing_url = urljoin("https://www.gesobau.de", detail)

        title = (
            raw.get("title")
            or item.get("title")
            or raw.get("adresse_string")
            or "GESOBAU Wohnung"
        )

        rent = raw.get("warmmiete_floatS")
        size = raw.get("wohnflaeche_floatS")
        rooms = raw.get("zimmer_intS")
        address = raw.get("adresse_string", "")
        location = ", ".join(raw.get("location_string", []))
        no_wbs = raw.get("noWbs_boolS")

        summary = (
            f"Warmmiete {rent} € | "
            f"{rooms} Zimmer | "
            f"{size} m² | "
            f"{address} | "
            f"{location} | "
            f"WBS: {'nein' if no_wbs else 'möglich'}"
        )

        entries.append({
            "id": str(item.get("uid") or raw.get("uid") or listing_url),
            "link": listing_url,
            "title": title,
            "summary": summary,
        })

    return entries
