import hashlib
import httpx
from bs4 import BeautifulSoup

BASE_URL = "https://buhgalter911.com/forum"

# Розділи де живуть реальні болі бухгалтерів
FORUMS = [
    (2,  "911_help"),       # 911 — Невідкладна бухгалтерська допомога
    (6,  "bank_cash"),      # Банк, каса, підзвіт
    (9,  "audit_fines"),    # Перевірки, штрафи
    (1,  "accounting"),     # Загальні питання бухгалтерського обліку
    (4,  "reporting"),      # Фінансова звітність
]

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}


def _hash(source: str, text: str) -> str:
    return hashlib.sha256(f"{source}:{text[:500]}".encode()).hexdigest()


def _get_topic_urls(forum_id: int, pages: int = 2) -> list[str]:
    urls = []
    for page in range(pages):
        start = page * 25
        params = f"?f={forum_id}" + (f"&start={start}" if start else "")
        r = httpx.get(f"{BASE_URL}/viewforum.php{params}", timeout=10,
                      follow_redirects=True, headers=HEADERS)
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.select("a.topictitle"):
            href = a.get("href", "").lstrip("./")
            if href:
                urls.append(f"{BASE_URL}/{href}")
    return urls


def _parse_topic(url: str, source_name: str) -> list[dict]:
    r = httpx.get(url, timeout=10, follow_redirects=True, headers=HEADERS)
    soup = BeautifulSoup(r.text, "html.parser")

    # заголовок теми
    title_el = soup.select_one("h2.topic-title, h1, title")
    title = title_el.get_text(strip=True) if title_el else ""

    messages = []
    for post_el in soup.select("div.content"):
        text = post_el.get_text(separator="\n", strip=True)
        if len(text) < 40:
            continue
        messages.append({
            "source": source_name,
            "source_url": url,
            "content_hash": _hash(source_name, text),
            "title": title,
            "body": text[:8000],
            "author": None,
            "published_at": None,
        })
    return messages


def collect_buhgalter911(topics_per_forum: int = 30) -> list[dict]:
    all_messages = []
    for forum_id, source_name in FORUMS:
        try:
            topic_urls = _get_topic_urls(forum_id, pages=3)[:topics_per_forum]
            forum_msgs = []
            for url in topic_urls:
                try:
                    msgs = _parse_topic(url, f"buh911_{source_name}")
                    forum_msgs.extend(msgs)
                except Exception as e:
                    print(f"    topic error {url}: {e}")
            all_messages.extend(forum_msgs)
            print(f"  buh911/{source_name}: {len(topic_urls)} topics, {len(forum_msgs)} posts")
        except Exception as e:
            print(f"  buh911/{source_name}: ERROR — {e}")
    return all_messages
