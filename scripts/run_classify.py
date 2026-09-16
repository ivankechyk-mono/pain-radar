#!/usr/bin/env python3
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.db.client import get_unclassified_by_source, insert_classified, mark_classified
from src.classifier.pain_classifier import classify_one

PER_SOURCE   = 200
PAUSE_EVERY  = 20
PAUSE_SECONDS = 2

SOURCES = [
    "tg_bu911",
    "tg_golovbukh",
    "tg_buhi1c",
    "buh911_audit_fines",
    "buh911_reporting",
    "buh911_bank_cash",
    "buh911_911_help",
    "tg_Zrobleno_buhgalter",
    "tg_UAtaxesYou",
    "dtkt_news",
    # minfin competitor reviews
    "minfin_privatbank",
    "minfin_pumb",
    "minfin_a-bank",
    "minfin_oschadbank",
    "minfin_ukrsibbank",
    "minfin_aval",
    "minfin_sensebank",
]

total_classified = 0
total_pains      = 0
total_tokens_in  = 0
total_tokens_out = 0
llm_calls        = 0


def classify_batch(messages: list[dict]) -> tuple[list, list]:
    global llm_calls, total_tokens_in, total_tokens_out
    results, failed_ids = [], []
    for msg in messages:
        text = (msg.get("title") or "") + "\n" + (msg.get("body") or "")
        try:
            result = classify_one(msg["id"], text)
            tokens_in  = result.pop("_tokens_in",  0)
            tokens_out = result.pop("_tokens_out", 0)
            results.append(result)
            total_tokens_in  += tokens_in
            total_tokens_out += tokens_out
            llm_calls += 1
            print(f"  #{llm_calls} {msg['source']} | pain={result.get('is_pain')} cat={result.get('pain_category')}", flush=True)
            if llm_calls % PAUSE_EVERY == 0:
                print(f"  --- pause {PAUSE_SECONDS}s | tokens total={total_tokens_in+total_tokens_out:,} ---", flush=True)
                time.sleep(PAUSE_SECONDS)
        except Exception as e:
            print(f"  skip {msg['id']}: {e}", flush=True)
            failed_ids.append(str(msg["id"]))
    return results, failed_ids


for source in SOURCES:
    messages = get_unclassified_by_source(source, limit=PER_SOURCE)
    if not messages:
        print(f"\n[{source}] nothing to classify — skip", flush=True)
        continue

    print(f"\n=== {source}: {len(messages)} messages ===", flush=True)
    results, failed_ids = classify_batch(messages)

    if results:
        pains = [r for r in results if r.get("is_pain")]
        insert_classified(results)
        mark_classified([r["raw_message_id"] for r in results])
        total_classified += len(results)
        total_pains      += len(pains)
        print(f"  → pains: {len(pains)}/{len(results)} | total: {total_pains}/{total_classified}", flush=True)

    if failed_ids:
        mark_classified(failed_ids)

print(f"\n{'='*40}")
print(f"Done.")
print(f"  Classified : {total_classified}")
print(f"  Pains found: {total_pains}")
print(f"  Tokens in  : {total_tokens_in:,}")
print(f"  Tokens out : {total_tokens_out:,}")
print(f"  Tokens total: {total_tokens_in + total_tokens_out:,}")
