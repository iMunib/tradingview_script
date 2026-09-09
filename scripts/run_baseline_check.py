import asyncio
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
import scripts.test_matrix as tm

tasks = [
    {"sym": "BATS:SPY", "tf": "1D", "sample": "OOS"},
    {"sym": "BATS:QQQ", "tf": "1D", "sample": "OOS"},
    {"sym": "BITSTAMP:BTCUSD", "tf": "1D", "sample": "OOS"},
    {"sym": "BATS:SPY", "tf": "1W", "sample": "OOS"},
    {"sym": "BATS:QQQ", "tf": "1W", "sample": "OOS"},
    {"sym": "BITSTAMP:BTCUSD", "tf": "1W", "sample": "OOS"},
]

pine = os.path.join(ROOT_DIR, "baseline_pure.pine")
asyncio.run(tm.run_matrix(pine, tasks))
