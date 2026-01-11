#!/usr/bin/env python3
"""监控 Claude Code 是否使用了非 Claude 模型"""
import json
import argparse
import time
import subprocess
import sys
from pathlib import Path

STATS_FILE = Path.home() / ".claude" / "stats-cache.json"

def notify(title, message, webhook=None, details=None):
    """发送通知"""
    # 转义 XML 特殊字符
    def escape_xml(s):
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("'", "&apos;").replace('"', "&quot;")

    safe_title = escape_xml(title)
    safe_msg = escape_xml(message)

    # 生成详情报告文件
    report_path = ""
    if details:
        import tempfile
        import os
        report = f"ccwatch 检测报告\n{'='*40}\n时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        report += f"警告: {message}\n\n"
        report += "详细信息:\n"
        for model, usage in details.items():
            report += f"\n模型: {model}\n"
            for k, v in usage.items():
                report += f"  {k}: {v}\n"
        report += f"\n原始数据: {STATS_FILE}\n"

        # 使用完整路径避免短路径问题
        temp_dir = os.path.expandvars("%TEMP%") if sys.platform == "win32" else tempfile.gettempdir()
        report_file = Path(temp_dir) / "ccwatch_report.txt"
        report_file.write_text(report, encoding="utf-8")
        report_path = str(report_file.resolve()).replace("\\", "/")

    # Windows Toast 通知
    if sys.platform == "win32":
        try:
            from ctypes import windll
            windll.user32.MessageBeep(0x40)
        except: pass
        try:
            import tempfile as tf
            launch_path = f"file:///{report_path}" if report_path else ""
            action_xml = f'<action content="查看详情" activationType="protocol" arguments="file:///{report_path}" />' if report_path else ""
            ps_content = f'''[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
$template = @"
<toast activationType="protocol" launch="{launch_path}">
    <visual>
        <binding template="ToastText02">
            <text id="1">{safe_title}</text>
            <text id="2">{safe_msg}</text>
        </binding>
    </visual>
    <actions>
        {action_xml}
    </actions>
</toast>
"@
$xml = [Windows.Data.Xml.Dom.XmlDocument]::new()
$xml.LoadXml($template)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('ccwatch').Show([Windows.UI.Notifications.ToastNotification]::new($xml))
'''
            with tf.NamedTemporaryFile(mode='w', suffix='.ps1', delete=False, encoding='utf-8-sig') as f:
                f.write(ps_content)
                ps_file = f.name
            subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", ps_file], capture_output=True)
            import os
            os.unlink(ps_file)
        except: pass
    # macOS 通知
    elif sys.platform == "darwin":
        subprocess.run(["osascript", "-e", f'display notification "{message}" with title "{title}"'], capture_output=True)
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
    last_notify = {}
    while True:
        non_claude, err = get_non_claude_models()
        if non_claude:
            now = time.time()
            for model, usage in non_claude.items():
                tokens = usage.get("inputTokens", 0) + usage.get("outputTokens", 0) + usage.get("tokens", 0)
                if model in last_tokens and tokens > last_tokens[model]:
                    diff = tokens - last_tokens[model]
                    print(f"\n[{time.strftime('%H:%M:%S')}] [!] {model} 新增 {diff} tokens")
                    if model not in last_notify or (now - last_notify[model]) >= cooldown:
                        notify("ccwatch", f"{model} 新增 {diff} tokens", webhook, non_claude)
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
            notify("ccwatch", f"检测到 {len(non_claude)} 个非 Claude 模型", args.webhook, non_claude)
