---
name: serverchan-push
description: Send ServerChan/Server酱 notifications from Codex workflows using the sctapi.ftqq.com send endpoint. Use when the user asks to push, notify, alert, test ServerChan, send Server酱 messages, or add abnormal-condition notifications to monitors/automations; supports one-off pushes and automation error alerts with title/desp content.
---

# ServerChan Push

## Quick Start

Use `scripts/serverchan_push.py` for deterministic sends. Prefer POST for non-trivial messages.

```powershell
python .codex\skills\serverchan-push\scripts\serverchan_push.py `
  --title "Antigravity 训练异常" `
  --desp "进程已退出，请检查日志。" `
  --sendkey $env:SERVERCHAN_SENDKEY
```

If the send key is already configured:

```powershell
$env:SERVERCHAN_SENDKEY = "SCT..."
python .codex\skills\serverchan-push\scripts\serverchan_push.py --title "测试" --desp "通道可用"
```

Use `--dry-run` to validate what would be sent without calling the API.

## Workflow

1. Get the send key from the user, an existing secret, or `SERVERCHAN_SENDKEY`.
2. Keep the key out of committed files, logs, and normal chat output.
3. Build a short title and a useful `desp` body with the reason, evidence, and next action.
4. Send with the bundled script, or use the same POST shape directly if a script is inconvenient.
5. Treat `code: 0` or `data.error: SUCCESS` as success. Surface non-zero codes as a failed push.

## Automation Alerts

For monitors, push only when a condition is abnormal or user-noteworthy. Avoid sending normal heartbeat progress unless the user explicitly asks.

Good alert body fields:

- Abnormal reason
- Latest timestamp or status line
- Process/resource state
- Relevant log path or short excerpt
- Suggested next check

Example abnormal alert:

```powershell
python .codex\skills\serverchan-push\scripts\serverchan_push.py `
  --title "Antigravity 训练异常" `
  --desp "round 5 超过 20 分钟无新进度。最新日志: Started 300 games with models。建议检查 katago.exe 和 GPU。"
```

## Direct API Shape

Endpoint:

```text
https://sctapi.ftqq.com/<sendkey>.send
```

Parameters:

- `title`: Required. Keep concise.
- `desp`: Optional but recommended. Use Markdown/plain text.

Chinese and long content are safest with POST form fields. For one-line curl examples, URL encode Chinese values.

