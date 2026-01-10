#!/usr/bin/env python3
"""监控 Claude Code 是否使用了非 Claude 模型"""
import json
import argparse
import time
from pathlib import Path

STATS_FILE = Path.home() / ".claude" / "stats-cache.json"

def get_non_claude_models():
    if not STATS_FILE.exists():
        return None, f"统计文件不存在: {STATS_FILE}"

    with open(STATS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    non_claude = {}

    for model, usage in data.get("modelUsage", {}).items():
        if "claude" not in model.lower():
            non_claude[model] = usage

    for entry in data.get("dailyModelTokens", []):
        date = entry.get("date", "unknown")
        for model, tokens in entry.get("tokensByModel", {}).items():
            if "claude" not in model.lower():
                key = f"{model} ({date})"
                non_claude[key] = {"tokens": tokens}

    return non_claude, None

def print_result(non_claude, err):
    if err:
        print(err)
        return
    if non_claude:
        print("[!] 检测到非 Claude 模型使用:")
        for model, usage in non_claude.items():
            print(f"  - {model}: {usage}")
    else:
        print("[OK] 未检测到非 Claude 模型")

def watch(interval):
    print(f"监控中... (每 {interval} 秒检查一次, Ctrl+C 退出)")
    last = None
    while True:
        non_claude, err = get_non_claude_models()
        if non_claude != last:
            print(f"\n[{time.strftime('%H:%M:%S')}]")
            print_result(non_claude, err)
            last = non_claude
        time.sleep(interval)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="监控 Claude Code 非 Claude 模型使用")
    parser.add_argument("-w", "--watch", type=int, metavar="SEC", help="持续监控，指定检查间隔秒数")
    args = parser.parse_args()

    if args.watch:
        try:
            watch(args.watch)
        except KeyboardInterrupt:
            print("\n已停止监控")
    else:
        print_result(*get_non_claude_models())
