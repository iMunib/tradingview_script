import asyncio
import os
import sys
import json

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
import scripts.test_matrix as tm

tasks_12 = [
    # 1D In-Sample
    {"sym": "BATS:SPY", "tf": "1D", "sample": "IS"},
    {"sym": "BATS:QQQ", "tf": "1D", "sample": "IS"},
    {"sym": "BITSTAMP:BTCUSD", "tf": "1D", "sample": "IS"},
    # 1D Out-of-Sample
    {"sym": "BATS:SPY", "tf": "1D", "sample": "OOS"},
    {"sym": "BATS:QQQ", "tf": "1D", "sample": "OOS"},
    {"sym": "BITSTAMP:BTCUSD", "tf": "1D", "sample": "OOS"},
    # 1W In-Sample
    {"sym": "BATS:SPY", "tf": "1W", "sample": "IS"},
    {"sym": "BATS:QQQ", "tf": "1W", "sample": "IS"},
    {"sym": "BITSTAMP:BTCUSD", "tf": "1W", "sample": "IS"},
    # 1W Out-of-Sample
    {"sym": "BATS:SPY", "tf": "1W", "sample": "OOS"},
    {"sym": "BATS:QQQ", "tf": "1W", "sample": "OOS"},
    {"sym": "BITSTAMP:BTCUSD", "tf": "1W", "sample": "OOS"},
]

async def main():
    pine = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT_DIR, "test_strategy.pine")
    res = await tm.run_matrix(pine, tasks_12)
    with open(os.path.join(ROOT_DIR, "metrics", "test_matrix_results.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)

if __name__ == "__main__":
    asyncio.run(main())
