import hashlib
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

SCRAPECREATORS_BASE = "https://api.scrapecreators.com/v1"

GROUPS = [
    "https://www.facebook.com/groups/372509172809688/",   # Бухгалтери України
    "https://www.facebook.com/groups/189668319953739/",   # ДЕБЕТ ЗЛІВА
    # Клуб бухгалтерів Дт-Кт (ClubOfAccountants) — закрита для API,
    # posts endpoint повертає [] попри публічну назву групи
]


def _hash(source: str, text: str) -> str:
    return hashlib.sha256(f"{source}:{text[:500]}".encode()).hexdigest()


def _get_headers() -> dict:
    return {"x-api-key": os.environ["SCRAPECREATORS_API_KEY"]}


def _fetch_group_posts(group_url: str, max_posts: int = 50) -> list[dict]:
    headers = _get_headers()
    posts = []
    cursor = None

    while len(posts) < max_posts:
        params = {"url": group_url, "sort_by": "CHRONOLOGICAL"}
        if cursor:
            params["cursor"] = cursor

        r = httpx.get(
            f"{SCRAPECREATORS_BASE}/facebook/group/posts",
            headers=headers,
            params=params,
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()

        batch = data.get("posts") or data.get("data") or []
        if not batch:
            break

        for post in batch:
            text = post.get("text") or post.get("message") or post.get("story") or ""
            if len(text) < 40:
                continue
            source = f"fb_{group_url.rstrip('/').split('/')[-1]}"
            posts.append({
                "source": source,
                "source_url": post.get("url") or post.get("post_url"),
                "content_hash": _hash(source, text),
                "title": None,
                "body": text[:8000],
                "author": post.get("author_name") or post.get("username"),
                "published_at": post.get("created_at") or post.get("timestamp"),
            })

        cursor = data.get("cursor") or data.get("next_cursor")
        if not cursor:
            break

    return posts


def collect_facebook(max_posts_per_group: int = 50) -> list[dict]:
    api_key = os.environ.get("SCRAPECREATORS_API_KEY")
    if not api_key:
        print("  Facebook: SCRAPECREATORS_API_KEY не вказано — пропускаємо")
        return []

    all_messages = []
    for group_url in GROUPS:
        group_id = group_url.rstrip("/").split("/")[-1]
        try:
            posts = _fetch_group_posts(group_url, max_posts=max_posts_per_group)
            all_messages.extend(posts)
            print(f"  fb/{group_id}: {len(posts)} posts")
        except Exception as e:
            print(f"  fb/{group_id}: ERROR — {e}")

    return all_messages
