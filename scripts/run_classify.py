#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.pipeline import run_classify

result = run_classify()

print(f"\n{'='*40}")
print("Done.")
print(f"  Classified : {result['classified']}")
print(f"  Pains found: {result['pains']}")
