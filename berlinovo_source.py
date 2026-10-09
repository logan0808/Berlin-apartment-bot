import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

URL = "https://www.berlinovo.de/de/wohnungen/suche"

HEADERS = {
    "User-Agent": "berlin-apartment-bot/1.0 (personal use)"
}


def _num(value):
    if not value:
        return None

    s = str(value).strip()

    if "," in s:
        s = s.replace(".", "").replace(",", ".")

    try:
        return float(s)
    except ValueError:
        return None


def fetch_berlinovo(
    url=URL,
    min_rooms=1,
    max_rooms=3,
    max_rent=1500,
):
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=20,
    )
    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    entries = {}

    for link_tag in soup.find_all("a", href=True):

        href = link_tag["href"]

        # Only real apartment detail pages.
        if "/wohnung-id/" not in href:
            continue

        link = urljoin(url, href).split("#")[0]

        if link in entries:
            continue

        # Walk up to find the listing container.
        node = link_tag
        card = None

        for _ in range(8):
            node = node.parent

            if node is None:
                break

            text = " ".join(node.stripped_strings)

            if "Warmmiete" in text and "Zimmer" in text:
                card = node
                break

        if card is None:
            continue

        text = " ".join(card.stripped_strings)

        rent_match = re.search(
            r"Warmmiete\s+([\d.]+,\d{2})\s*€",
            text,
        )

        rooms_match = re.search(
            r"Zimmer\s+([\d.,]+)",
            text,
        )

        if not rent_match or not rooms_match:
            continue

        rent = _num(rent_match.group(1))
        rooms = _num(rooms_match.group(1))

        if rent is None or rooms is None:
            continue

        if rooms < min_rooms or rooms > max_rooms:
            continue

        if rent > max_rent:
            continue

        title = re.sub(
            r"\\s+",
            " ",
            link_tag.get_text(" ", strip=True),
        ).strip()

        # Skip image-only links; the text link to the same apartment follows.
        if not title or title.lower() == "mehr":
            continue

        title = re.sub(
            r'^\\s*\\{"type":"Point","coordinates":\\[[^]]+\\]\\}\\s*',
            "",
            title,
        )
        title = re.sub(
            r"^\\s*Etagenwohnung\\s*\\d*\\s*",
            "",
            title,
            flags=re.IGNORECASE,
        ).strip()

        if not title:
            continue

        address_match = re.search(
            r"([A-Za-zÄÖÜäöüß.\- ]+\s+\d+[A-Za-z]?)\s+"
            r"\d{5}\s+Berlin",
            text,
        )

        address = (
            address_match.group(1).strip()
            if address_match
            else ""
        )

        rent_txt = f"{rent:.2f}".replace(".", ",")
        rooms_txt = f"{rooms:g}"

        summary = (
            f"{address} | "
            f"Warmmiete {rent_txt} € | "
            f"{rooms_txt} Zimmer"
        )

        entries[link] = {
            "id": link,
            "link": link,
            "title": title[:90],
            "summary": summary,
        }

    return list(entries.values())


if __name__ == "__main__":
    entries = fetch_berlinovo()

    print("BERLINOVO:", len(entries))

    for entry in entries[:5]:
        print(entry)
