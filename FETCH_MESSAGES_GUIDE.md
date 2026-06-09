# Fetch Messages Guide

This guide explains how to fetch Slack messages from a specific time window instead of real-time monitoring.

## Installation

```bash
cd /home/ravneet-kaur/code/slack-bot
source .slack_bot_venv/bin/activate
pip install -r requirements.txt
```

## Usage

### Method 1: Command Line

Fetch messages from the last 24 hours:
```bash
python fetch_messages.py C1234567890 --window "24h"
```

Fetch messages from the last hour:
```bash
python fetch_messages.py C1234567890 --window "1h"
```

Fetch messages from the last 7 days:
```bash
python fetch_messages.py C1234567890 --window "7d"
```

Fetch messages by channel name instead of ID:
```bash
python fetch_messages.py "#general" --window "24h"
```

Fetch messages from a specific date:
```bash
python fetch_messages.py C1234567890 --window "2024-06-01"
```

Fetch messages from a specific time range:
```bash
python fetch_messages.py C1234567890 --window "2024-06-01 09:00 to 2024-06-01 17:00"
```

Save messages to a JSON file:
```bash
python fetch_messages.py C1234567890 --window "24h" --output messages.json
```

### Method 2: Import in Another Python Script

```python
from fetch_messages import SlackMessageFetcher
from datetime import datetime, timedelta

# Initialize fetcher
fetcher = SlackMessageFetcher()

# Fetch messages from last hour
messages = fetcher.fetch_messages(
    channel_id="C1234567890",
    start_time=datetime.now() - timedelta(hours=1),
    end_time=datetime.now()
)

# Process messages
for msg in messages:
    print(f"{msg['user']}: {msg['text']}")
```

### Method 3: Using the Helper Function

```python
from fetch_messages import SlackMessageFetcher, parse_time_window

fetcher = SlackMessageFetcher()

# Parse time window from string
start, end = parse_time_window("24h")
messages = fetcher.fetch_messages("C1234567890", start, end)
```

## Time Window Formats

| Format | Description | Example |
|--------|-------------|---------|
| `1h` | Last 1 hour | `--window "1h"` |
| `24h` | Last 24 hours | `--window "24h"` |
| `7d` | Last 7 days | `--window "7d"` |
| `30m` | Last 30 minutes | `--window "30m"` |
| `2024-06-01` | Entire day | `--window "2024-06-01"` |
| `2024-06-01 10:00` | From specific time to now | `--window "2024-06-01 10:00 to 2024-06-09 12:00"` |

## Get Channel ID

If you don't know your channel ID:

**Option 1: Use channel name**
```bash
python fetch_messages.py "#your-channel-name" --window "1h"
```

**Option 2: From Python**
```python
fetcher = SlackMessageFetcher()
channel_id = fetcher.get_channel_id_by_name("general")
print(channel_id)  # C1234567890
```

**Option 3: From Slack UI**
1. Right-click the channel in Slack
2. Select "View channel details"
3. Scroll to bottom - Channel ID is shown

## Message Data Structure

Each message contains:
```python
{
    "text": "Message content",
    "user": "U1234567890",
    "channel": "C1234567890",
    "timestamp": "1234567890.123456",
    "thread_ts": "1234567890.123456",  # If in a thread
    "type": "message",
    "subtype": None,
    "datetime": "2024-06-09T10:30:45"  # Human-readable timestamp
}
```

## Examples

### Example 1: Monitor Error Messages
```python
from fetch_messages import SlackMessageFetcher
from datetime import datetime, timedelta

fetcher = SlackMessageFetcher()
messages = fetcher.fetch_messages(
    channel_id="C1234567890",
    start_time=datetime.now() - timedelta(hours=1)
)

# Find error messages
for msg in messages:
    if "error" in msg["text"].lower():
        print(f"[ERROR] {msg['datetime']}: {msg['text']}")
```

### Example 2: Export Messages to CSV
```python
import csv
from fetch_messages import SlackMessageFetcher
from datetime import datetime, timedelta

fetcher = SlackMessageFetcher()
messages = fetcher.fetch_messages(
    channel_id="C1234567890",
    start_time=datetime.now() - timedelta(days=7)
)

# Write to CSV
with open("messages.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["datetime", "user", "text"])
    writer.writeheader()
    for msg in messages:
        writer.writerow({
            "datetime": msg["datetime"],
            "user": msg["user"],
            "text": msg["text"]
        })
```

### Example 3: Scheduled Fetching (Cron Job)
Create a script that runs every hour to fetch recent messages:

```python
#!/usr/bin/env python3
# scheduled_fetch.py

from fetch_messages import SlackMessageFetcher
from datetime import datetime, timedelta
import json

fetcher = SlackMessageFetcher()

# Fetch messages from last hour
messages = fetcher.fetch_messages(
    channel_id="C1234567890",
    start_time=datetime.now() - timedelta(hours=1)
)

# Save with timestamp
filename = f"messages_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
with open(filename, "w") as f:
    json.dump(messages, f, indent=2)

print(f"Saved {len(messages)} messages to {filename}")
```

Add to crontab:
```bash
# Run every hour
0 * * * * cd /home/ravneet-kaur/code/slack-bot && source .slack_bot_venv/bin/activate && python scheduled_fetch.py
```

## Comparison: Real-time vs Historical

| Feature | bot.py (Real-time) | fetch_messages.py (Historical) |
|---------|-------------------|-------------------------------|
| Use case | Monitor live messages | Fetch past messages |
| Requires | Socket Mode running 24/7 | Run on-demand |
| Time range | Only new messages | Any time window |
| Performance | Continuous connection | Query when needed |
| Best for | Live monitoring, alerts | Analysis, reporting, backfill |

## Troubleshooting

**No messages returned?**
- Check that bot is invited to the channel
- Verify the time window contains messages
- Ensure channel ID is correct

**Permission errors?**
- Make sure you have `channels:history` scope (public channels)
- Make sure you have `groups:history` scope (private channels)
- Reinstall app after adding scopes

**Rate limits?**
- Slack allows ~1 request per second for conversations.history
- Script automatically handles pagination
- For large fetches, consider adding delays between requests
