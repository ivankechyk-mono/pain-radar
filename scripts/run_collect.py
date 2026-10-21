#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.pipeline import run_collect

result = run_collect()

for name, count in result["inserted"].items():
    print(f"\n=== {name} ===\nInserted: {count}")
for failure in result["failed"]:
    print(f"FAILED: {failure}")

print("\nDone.")
if result["failed"]:
    print(f"Збій у колекторах: {len(result['failed'])}")

# Червоний статус лише якщо не спрацював жоден колектор — тоді запуск був марний
# і БД не отримала активності. Окремі збої (Telegram-чати без сесії у хмарі) — очікувані.
if not result["inserted"]:
    sys.exit(1)
