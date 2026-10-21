"""Спільна логіка collect+classify для CLI-скриптів (scripts/run_*.py) та кнопки в dashboard.py."""
import time
from datetime import datetime

from src.collectors.rss_collector import collect_rss
from src.collectors.telegram_public_collector import collect_telegram_public
from src.collectors.forum_collector import collect_buhgalter911
from src.collectors.facebook_collector import collect_facebook
from src.collectors.minfin_collector import collect_minfin
from src.db.client import insert_raw, get_unclassified_by_source, insert_classified, mark_classified
from src.classifier.pain_classifier import classify_one

def _collect_telegram_chats():
    # Імпорт ліниво: модуль читає TG_API_ID/TG_API_HASH на імпорті і потребує
    # файл сесії Telethon. Якщо їх нема — хай падає тут, а не на старті.
    from src.collectors.telegram_chat_collector import collect_telegram_chats
    return collect_telegram_chats()


COLLECTORS = [
    ("RSS (dtkt.ua)", collect_rss),
    ("Telegram public channels", collect_telegram_public),
    ("Telegram chats (buhgalteri_kiev)", _collect_telegram_chats),
    ("Forum buhgalter911.com", lambda: collect_buhgalter911(topics_per_forum=10)),
    ("Facebook groups", lambda: collect_facebook(max_posts_per_group=50)),
    ("Minfin.com.ua — відгуки на банки-конкуренти", lambda: collect_minfin(max_pages=10)),
]

CLASSIFY_SOURCES = [
    "tg_bu911", "tg_golovbukh", "tg_buhi1c",
    "buh911_audit_fines", "buh911_reporting", "buh911_bank_cash", "buh911_911_help",
    "tg_Zrobleno_buhgalter", "tg_UAtaxesYou", "dtkt_news",
    "minfin_privatbank", "minfin_pumb", "minfin_a-bank", "minfin_oschadbank",
    "minfin_ukrsibbank", "minfin_aval", "minfin_sensebank",
]

PER_SOURCE = 200
PAUSE_EVERY = 20
PAUSE_SECONDS = 2


def run_collect() -> dict:
    """Запускає всі колектори, пише в raw_messages. Повертає {назва: inserted} + failed."""
    result = {"inserted": {}, "failed": []}
    for name, collect in COLLECTORS:
        try:
            msgs = collect()
            result["inserted"][name] = insert_raw(msgs)
        except Exception as e:
            result["failed"].append(f"{name}: {type(e).__name__}: {e}")
    return result


def run_classify(since: datetime | None = None, per_source: int = PER_SOURCE) -> dict:
    """Класифікує необроблені raw_messages (опціонально лише новіші за `since`)."""
    total_classified = 0
    total_pains = 0
    llm_calls = 0

    for source in CLASSIFY_SOURCES:
        messages = get_unclassified_by_source(source, limit=per_source, since=since)
        if not messages:
            continue

        results, failed_ids = [], []
        for msg in messages:
            text = (msg.get("title") or "") + "\n" + (msg.get("body") or "")
            try:
                result = classify_one(msg["id"], text)
                result.pop("_tokens_in", None)
                result.pop("_tokens_out", None)
                results.append(result)
                llm_calls += 1
                if llm_calls % PAUSE_EVERY == 0:
                    time.sleep(PAUSE_SECONDS)
            except Exception:
                failed_ids.append(str(msg["id"]))

        if results:
            pains = [r for r in results if r.get("is_pain")]
            insert_classified(results)
            mark_classified([r["raw_message_id"] for r in results])
            total_classified += len(results)
            total_pains += len(pains)
        if failed_ids:
            mark_classified(failed_ids)

    return {"classified": total_classified, "pains": total_pains}
