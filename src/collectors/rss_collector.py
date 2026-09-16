import hashlib
import httpx
import feedparser
from datetime import datetime, timezone
from tenacity import retry, stop_after_attempt, wait_exponential

RSS_SOURCES = [
    {"name": "dtkt_news", "url": "https://news.dtkt.ua/rss"},
]

JINA_BASE = "https://r.jina.ai/"


def _hash(source: str, text: str) -> str:
    return hashlib.sha256(f"{source}:{text[:500]}".encode()).hexdigest()


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _fetch_full_text(url: str) -> str:
    resp = httpx.get(JINA_BASE + url, timeout=30, headers={"Accept": "text/plain"})
    resp.raise_for_status()
    return resp.text


def collect_rss() -> list[dict]:
    messages = []
    for source in RSS_SOURCES:
        feed = feedparser.parse(source["url"])
        for entry in feed.entries:
            url = entry.get("link", "")
            title = entry.get("title", "")
            published = entry.get("published_parsed")
            pub_dt = (
                datetime(*published[:6], tzinfo=timezone.utc).isoformat()
                if published
                else None
            )
            try:
                body = _fetch_full_text(url)
            except Exception:
                body = entry.get("summary", "")

            if len(body) < 50:
                continue

            messages.append({
                "source": source["name"],
                "source_url": url,
                "content_hash": _hash(source["name"], body),
                "title": title,
                "body": body[:8000],
                "author": entry.get("author"),
                "published_at": pub_dt,
            })
    return messages
