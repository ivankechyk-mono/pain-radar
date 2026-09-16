import hashlib
import re
import time
import httpx
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import json

BANKS = [
    ("privatbank", "ПриватБанк"),
    ("pumb",       "ПУМБ"),
    ("a-bank",     "А-Банк"),
    ("oschadbank", "Ощадбанк"),
    ("ukrsibbank", "УкрСиббанк"),
    ("aval",       "Райффайзен Банк Аваль"),
    ("sensebank",  "Sense Bank"),
]

MINFIN_BASE = "https://minfin.com.ua"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "uk-UA,uk;q=0.9",
}
SINCE_DATE = datetime(2026, 1, 1, tzinfo=timezone.utc)
MAX_PAGES  = 10
SLEEP      = 1.2


def _hash(source: str, text: str) -> str:
    return hashlib.sha256(f"{source}:{text[:500]}".encode()).hexdigest()


def _get(url: str) -> httpx.Response | None:
    try:
        r = httpx.get(url, headers=HEADERS, timeout=15, follow_redirects=True)
        r.raise_for_status()
        return r
    except Exception as e:
        print(f"  HTTP error {url}: {e}")
        return None


def _extract_jsonld_reviews(soup: BeautifulSoup) -> list[dict]:
    """Extract review objects from JSON-LD embedded in page."""
    reviews = []
    for sc in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(sc.string or "")
        except Exception:
            continue
        # reviews can be at root or inside 'about'
        candidates = []
        if isinstance(data, dict):
            candidates.append(data)
            if isinstance(data.get("about"), dict):
                candidates.append(data["about"])
        for obj in candidates:
            items = obj.get("review", [])
            if isinstance(items, list):
                reviews.extend(items)
    return reviews


MONTHS_UA = {
    "січня": 1, "лютого": 2, "березня": 3, "квітня": 4, "травня": 5,
    "червня": 6, "липня": 7, "серпня": 8, "вересня": 9, "жовтня": 10,
    "листопада": 11, "грудня": 12,
}

def _parse_ua_date(text: str) -> str | None:
    m = re.search(r"(\d{1,2})\s+(\w+)\s+(2\d{3})", text)
    if not m:
        return None
    day, month_ua, year = m.group(1), m.group(2).lower(), m.group(3)
    month = MONTHS_UA.get(month_ua)
    if not month:
        return None
    return datetime(int(year), month, int(day), tzinfo=timezone.utc).isoformat()


def _review_ids_with_dates(soup: BeautifulSoup, bank_slug: str) -> dict[int, str | None]:
    """Return {review_id: published_at_iso} from a listing page."""
    pattern = re.compile(rf"/ua/company/{re.escape(bank_slug)}/review/(\d+)/?$")
    result: dict[int, str | None] = {}
    for a in soup.find_all("a", href=True):
        m = pattern.match(a["href"])
        if not m:
            continue
        rid = int(m.group(1))
        if rid in result:
            continue
        # climb up to find date in parent container
        pub_dt = None
        el = a
        for _ in range(5):
            el = el.parent
            if el is None:
                break
            pub_dt = _parse_ua_date(el.get_text(" ", strip=True))
            if pub_dt:
                break
        result[rid] = pub_dt
    return result


def _text_from_review_page(url: str) -> tuple[str, str | None, str | None]:
    """Return (body, title, published_at_iso) from an individual review page."""
    r = _get(url)
    if not r:
        return "", None, None
    soup = BeautifulSoup(r.text, "html.parser")

    title_el = soup.find("h1")
    title = title_el.get_text(strip=True) if title_el else None

    # minfin renders review text in div.CColumn or div.text.b-mrg
    for selector in ("div.CColumn", "div.text.b-mrg", "div[class*='review-text']",
                     "section.review__text", "div.review-body"):
        el = soup.select_one(selector)
        if el:
            body = el.get_text(separator="\n", strip=True)
            if len(body) > 50:
                return body, title, None

    # fallback: pick longest text block that isn't copyright/nav
    SKIP = ("copyright", "menu", "nav", "footer", "header", "banner", "sidebar")
    best_txt, best_len = "", 0
    for el in soup.find_all(["p", "div"]):
        cls = " ".join(el.get("class", []))
        if any(s in cls.lower() for s in SKIP):
            continue
        txt = el.get_text(separator="\n", strip=True)
        if best_len < len(txt) < 4000 and len(el.find_all()) < 8:
            best_txt, best_len = txt, len(txt)
    return best_txt, title, None


def _scrape_bank(bank_slug: str, max_pages: int = MAX_PAGES) -> list[dict]:
    source = f"minfin_{bank_slug}"
    messages = []
    seen_ids: set[int] = set()

    for page in range(1, max_pages + 1):
        if page == 1:
            list_url = f"{MINFIN_BASE}/ua/company/{bank_slug}/review/"
        else:
            list_url = f"{MINFIN_BASE}/ua/company/{bank_slug}/review/{page}/"
        r = _get(list_url)
        if not r:
            break
        soup = BeautifulSoup(r.text, "html.parser")

        # get IDs + dates from listing page
        id_dates = _review_ids_with_dates(soup, bank_slug)
        new_ids = [i for i in sorted(id_dates, reverse=True) if i not in seen_ids]
        if not new_ids:
            break
        seen_ids.update(new_ids)

        # also grab 5 reviews from JSON-LD (no extra request needed)
        jsonld_reviews = _extract_jsonld_reviews(soup)
        jsonld_by_body: dict[str, dict] = {}
        for rv in jsonld_reviews:
            body = (rv.get("reviewBody") or "").strip()
            if body:
                jsonld_by_body[body[:100]] = rv

        # fetch each review page
        for rid in new_ids:
            review_url = f"{MINFIN_BASE}/ua/company/{bank_slug}/review/{rid}/"
            body, title, _ = _text_from_review_page(review_url)
            pub_dt = id_dates.get(rid)  # date from listing page

            # if we got nothing from individual page, check JSON-LD match
            if not body:
                for key, rv in jsonld_by_body.items():
                    body = (rv.get("reviewBody") or "").strip()
                    title = title or rv.get("name")
                    break

            if len(body) < 50:
                time.sleep(0.3)
                continue

            messages.append({
                "source":       source,
                "source_url":   review_url,
                "content_hash": _hash(source, body),
                "title":        title,
                "body":         body[:8000],
                "author":       None,
                "published_at": pub_dt,
            })
            time.sleep(0.4)

        print(f"  minfin/{bank_slug} p{page}: +{len(new_ids)} ids → {len(messages)} total", flush=True)
        time.sleep(SLEEP)

        # stop if all reviews on page are older than SINCE_DATE
        dated = [m for m in messages if m["published_at"]]
        if dated:
            oldest_on_page = min(
                (m["published_at"] for m in messages[-len(new_ids):] if m["published_at"]),
                default=None,
            )
            if oldest_on_page and oldest_on_page < SINCE_DATE.isoformat():
                break

    # filter by date (keep undated ones too — we have no pub_dt for many)
    filtered = [
        m for m in messages
        if not m["published_at"] or m["published_at"] >= SINCE_DATE.isoformat()
    ]
    return filtered


def collect_minfin(max_pages: int = MAX_PAGES) -> list[dict]:
    all_messages = []
    for bank_slug, _ in BANKS:
        msgs = _scrape_bank(bank_slug, max_pages)
        all_messages.extend(msgs)
        print(f"  minfin/{bank_slug}: {len(msgs)} reviews collected", flush=True)
    return all_messages
