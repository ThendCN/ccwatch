#!/usr/bin/env python3
"""监控 Claude Code 是否使用了非 Claude 模型"""
import json
import argparse
import time
import subprocess
import sys
from pathlib import Path

STATS_FILE = Path.home() / ".claude" / "stats-cache.json"

def notify(title, message, webhook=None):
    """发送通知"""
    # 转义特殊字符
    safe_title = title.replace("'", "''").replace('"', '`"')
    safe_msg = message.replace("'", "''").replace('"', '`"')

    # Windows Toast 通知
    if sys.platform == "win32":
        try:
            from ctypes import windll
            windll.user32.MessageBeep(0x40)  # 播放提示音
        except: pass
        try:
            ps_cmd = f'''
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
            $xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
            $texts = $xml.GetElementsByTagName('text')
            $texts[0].AppendChild($xml.CreateTextNode('{safe_title}')) | Out-Null
            $texts[1].AppendChild($xml.CreateTextNode('{safe_msg}')) | Out-Null
            [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('ccwatch').Show([Windows.UI.Notifications.ToastNotification]::new($xml))
            '''
            subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True)
        except: pass
    # macOS 通知
    elif sys.platform == "darwin":
        subprocess.run(["osascript", "-e", f'display notification "{safe_msg}" with title "{safe_title}"'], capture_output=True)
    # Linux 通知
    else:
        subprocess.run(["notify-send", title, message], capture_output=True)

    # Webhook 通知
    if webhook:
        import urllib.request
        data = json.dumps({"text": f"{title}: {message}"}).encode()
        try:
            urllib.request.urlopen(urllib.request.Request(webhook, data, {"Content-Type": "application/json"}), timeout=5)
        except: pass

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
        return False
    if non_claude:
        print("[!] 检测到非 Claude 模型使用:")
        for model, usage in non_claude.items():
            print(f"  - {model}: {usage}")
        return True
    else:
        print("[OK] 未检测到非 Claude 模型")
        return False

def watch(interval, webhook=None, cooldown=60):
    print(f"监控中... (每 {interval} 秒检查, 通知冷却 {cooldown} 秒, Ctrl+C 退出)")
    last_tokens = {}
    last_notify = {}  # 记录上次通知时间
    while True:
        non_claude, err = get_non_claude_models()
        if non_claude:
            now = time.time()
            for model, usage in non_claude.items():
                tokens = usage.get("inputTokens", 0) + usage.get("outputTokens", 0) + usage.get("tokens", 0)
                if model in last_tokens and tokens > last_tokens[model]:
                    diff = tokens - last_tokens[model]
                    print(f"\n[{time.strftime('%H:%M:%S')}] [!] {model} 新增 {diff} tokens")
                    # 冷却检查：同一模型在冷却期内不重复通知
                    if model not in last_notify or (now - last_notify[model]) >= cooldown:
                        notify("ccwatch", f"{model} 新增 {diff} tokens", webhook)
                        last_notify[model] = now
                last_tokens[model] = tokens
        time.sleep(interval)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="监控 Claude Code 非 Claude 模型使用")
    parser.add_argument("-w", "--watch", type=int, metavar="SEC", help="持续监控，指定检查间隔秒数")
    parser.add_argument("--webhook", type=str, help="Webhook URL (Slack/Discord/企业微信等)")
    parser.add_argument("--cooldown", type=int, default=60, help="通知冷却时间(秒)，默认60")
    args = parser.parse_args()

    if args.watch:
        try:
            watch(args.watch, args.webhook, args.cooldown)
        except KeyboardInterrupt:
            print("\n已停止监控")
    else:
        non_claude, err = get_non_claude_models()
        if print_result(non_claude, err) and non_claude:
            notify("ccwatch", f"检测到 {len(non_claude)} 个非 Claude 模型", args.webhook)
