import re
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

URL = "https://www.wbm.de/wohnungen-berlin/angebote/"
HEADERS = {"User-Agent": "berlin-apartment-bot/1.0 (personal use)"}


def _num(value):
    try:
        return float(str(value).replace(".", "").replace(",", "."))
    except ValueError:
        return None


def _card(a):
    node, best = a, None
    for _ in range(12):
        node = node.parent
        if node is None:
            break
        n = node.get_text(" ").count("Warmmiete")
        if n == 1:
            best = node
        elif n > 1:
            break
    return best


def _parse_page(soup, base, min_rooms, max_rooms, max_rent):
    found = {}
    for a in soup.find_all("a", href=True):
        if "/wohnungen-berlin/angebote/details/" not in a["href"]:
            continue
        link = urljoin(base, a["href"]).split("#")[0]
        if link in found:
            continue
        card = _card(a)
        if card is None:
            continue
        text = " ".join(card.stripped_strings)

        def grab(p):
            m = re.search(p, text, re.S)
            return m.group(1).strip() if m else ""

        rent_txt = grab(r"([\d.]+,\d{2})\s*€\s*Warmmiete")
        size_txt = grab(r"([\d.,]+)\s*m²\s*Größe")
        rooms_txt = grab(r"Größe\s+(\d+(?:,\d)?)\s+Zimmer")
        plz = grab(r"(\d{5}) Berlin")
        rent, rooms = _num(rent_txt), _num(rooms_txt)

        if rent is not None and max_rent and rent > max_rent:
            continue
        if rooms is not None and not (min_rooms <= rooms <= max_rooms):
            continue

        title = (card.find("h2") or a).get_text(" ", strip=True)[:90] or link
        district = grab(r"^(\S+)\s")
        extras = [w for w in ("Neubau", "barrierearm", "Aufzug", "Balkon")
                  if w in text]
        summary = (
            f"{title} | {plz} {district} Warmmiete {rent_txt} € | "
            f"{rooms_txt} Zimmer | {size_txt} m² | {', '.join(extras)}"
        )
        found[link] = {"id": link, "link": link,
                       "title": title, "summary": summary}
    return found


def fetch_wbm(url=URL, min_rooms=1, max_rooms=3, max_rent=1500):
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    return list(_parse_page(soup, url, min_rooms, max_rooms, max_rent).values())
