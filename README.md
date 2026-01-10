# ccwatch

监控 Claude Code 是否使用了非 Claude 模型。

## 背景

当使用第三方 API 代理服务时，请求可能被路由到其他模型（如 glm-4.7）而非 Claude。此工具通过读取 Claude Code 的统计缓存文件来检测这种情况。

## 安装

```bash
git clone https://github.com/ThendCN/ccwatch.git
cd ccwatch
```

无需额外依赖，仅使用 Python 标准库。

## 使用

单次检查：
```bash
python ccwatch.py
```

持续监控（每 5 秒检查一次）：
```bash
python ccwatch.py -w 5
```

带 Webhook 通知：
```bash
python ccwatch.py -w 5 --webhook "https://hooks.slack.com/services/xxx"
```

自定义通知冷却时间（默认 60 秒，防止频繁打扰）：
```bash
python ccwatch.py -w 5 --cooldown 300  # 5分钟内同一模型只通知一次
```

Windows 下如遇中文乱码：
```cmd
set PYTHONIOENCODING=utf-8 && python ccwatch.py
```

## 参数

| 参数 | 说明 |
|------|------|
| `-w, --watch SEC` | 持续监控，指定检查间隔秒数 |
| `--webhook URL` | Webhook 通知地址 |
| `--cooldown SEC` | 通知冷却时间，默认 60 秒 |

## 通知方式

- **Windows**: Toast 通知 + 系统提示音
- **macOS**: 系统通知中心
- **Linux**: notify-send
- **Webhook**: 支持 Slack/Discord/企业微信等

## 输出示例

```
[!] 检测到非 Claude 模型使用:
  - glm-4.7: {'inputTokens': 6433510, 'outputTokens': 41357, ...}
  - glm-4.7 (2026-01-06): {'tokens': 6118268}
```

## 原理

读取 `~/.claude/stats-cache.json`，检查 `modelUsage` 和 `dailyModelTokens` 中是否存在模型名称不包含 "claude" 的记录。

## License

MIT
