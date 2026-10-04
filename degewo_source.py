import re, time
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "berlin-apartment-bot/1.0 (personal use)"}

def _card(a):
    node = a
    for _ in range(8):
        node = node.parent
        if node is None:
            return None
        if "Warmmiete" in node.get_text():
            return node

def _parse_page(soup, base):
    found = {}
    for a in soup.find_all("a", href=True):
        if "/immosuche/details/" not in a["href"]:
            continue
        link = urljoin(base, a["href"])
        if link in found:
            continue
        card = _card(a)
        if card is None:
            continue
        text = " ".join(card.stripped_strings)
        head, _, tail = text.partition("Warmmiete")
        price = re.search(r"([\d.]+,\d{2})\s*€", head)
        rooms = re.search(r"(\d+(?:,\d)?)\s+Zimmer", tail)
        size = re.search(r"([\d.,]+)\s*m²", tail)
        free = re.search(r"m²\s+(\S+)", tail)
        title = a.get_text(strip=True) or text[:60]
        summary = (
            f"{head.replace(title, '', 1).strip()} Warmmiete "
            f"{price.group(1) if price else ''} € | "
            f"{rooms.group(1) if rooms else ''} Zimmer | "
            f"{size.group(1) if size else ''} m² | "
            f"frei ab {free.group(1) if free else ''}"
        )
        found[link] = {
            "id": link,
            "link": link,
            "title": title,
            "summary": summary,
        }
    return found

def fetch_degewo(url, max_pages=3, delay=2):
    entries, seen_pages, queue = {}, set(), [url]
    while queue and len(seen_pages) < max_pages:
        page = queue.pop(0)
        if page in seen_pages:
            continue
        seen_pages.add(page)
        resp = requests.get(page, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        entries.update(_parse_page(soup, page))
        for a in soup.find_all("a", href=True):
            if "immobilie%5Bpage%5D" in a["href"]:
                queue.append(urljoin(page, a["href"]).split("#")[0])
        time.sleep(delay)
    return list(entries.values())

def parse_source(url):
    from types import SimpleNamespace
    if "degewo.de/immosuche" in url:
        return SimpleNamespace(entries=fetch_degewo(url, max_pages=10), bozo=0)
    if "gewobag.de/fuer-mietinteressentinnen/suche" in url:
        from gewobag_source import fetch_gewobag
        return SimpleNamespace(entries=fetch_gewobag(url, max_pages=6), bozo=0)
    import feedparser
    return feedparser.parse(url)
