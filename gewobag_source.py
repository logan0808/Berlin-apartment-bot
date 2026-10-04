import re, time
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "berlin-apartment-bot/1.0 (personal use)"}

def _card(a):
    node, best = a, None
    for _ in range(12):
        node = node.parent
        if node is None:
            break
        n = node.get_text(" ").count("Gesamtmiete")
        if n == 1:
            best = node
        elif n > 1:
            break
    return best

def _parse_page(soup, base):
    found = {}
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/fuer-mietinteressentinnen/mietangebote/" not in href:
            continue
        if "Mietangebot" not in a.get_text():
            continue
        link = urljoin(base, href).split("#")[0]
        if link in found:
            continue
        card = _card(a)
        if card is None:
            continue
        text = " ".join(card.stripped_strings)

        def grab(p):
            m = re.search(p, text, re.S)
            return m.group(1).strip() if m else ""

        bezirk = grab(r"Bezirk\s+(.+?)\s+Adresse")
        adresse = grab(r"Adresse\s+(.+?)\s+Fläche")
        rooms = grab(r"(\d+(?:,\d)?)\s*Zimmer\s*\|")
        size = grab(r"Zimmer\s*\|\s*([\d.,]+)\s*m²")
        rent = grab(r"Gesamtmiete\s+(?:ab\s+)?([\d.]+,\d{2})")
        frei = grab(r"Frei ab\s+(\S+)")
        extras = grab(r"besondere Eigenschaften\s+(.+?)\s+Mietangebot")
        wbs = "WBS erforderlich" if "WBS erforderlich" in text else ""
        summary = (
            f"{adresse} | {bezirk} {wbs} {extras} Warmmiete {rent} € | "
            f"{rooms} Zimmer | {size} m² | frei ab {frei}"
        )
        found[link] = {"id": link, "link": link,
                       "title": adresse[:90] or link, "summary": summary}
    return found

def fetch_gewobag(url, max_pages=6, delay=2):
    entries, seen, queue = {}, set(), [url]
    while queue and len(seen) < max_pages:
        page = queue.pop(0)
        if page in seen:
            continue
        seen.add(page)
        resp = requests.get(page, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        entries.update(_parse_page(soup, page))
        for a in soup.find_all("a", href=True):
            if "/suche/wohnung/page/" in a["href"]:
                queue.append(urljoin(page, a["href"]).split("#")[0])
        time.sleep(delay)
    return list(entries.values())
