# Fetch Messages Guide

This guide explains how to fetch Slack messages from a specific time window. The script can be used as a command-line tool or imported into other Python scripts.

## Installation

```bash
cd /home/ravneet-kaur/code/slack-bot
source .slack_bot_venv/bin/activate
pip install -r requirements.txt
```

## Command Line Usage

The script outputs messages in **JSON format**.

### Basic Usage

Fetch messages from the last 24 hours (default):
```bash
python3 fetch_messages.py C1234567890
```

Fetch messages from the last hour:
```bash
python3 fetch_messages.py C1234567890 --window "1h"
```

Fetch messages from the last 7 days:
```bash
python3 fetch_messages.py C1234567890 --window "7d"
```

### Using Channel Name

Fetch by channel name instead of ID:
```bash
python3 fetch_messages.py rolling_release_hack_the_hive --window "24h"
```

### Time Window Formats

| Format | Description | Example |
|--------|-------------|---------|
| `1h` | Last 1 hour | `--window "1h"` |
| `24h` | Last 24 hours | `--window "24h"` |
| `7d` | Last 7 days | `--window "7d"` |
| `30m` | Last 30 minutes | `--window "30m"` |
| `2024-06-01` | Entire day | `--window "2024-06-01"` |
| `2024-06-01 10:00 to 2024-06-09 12:00` | Specific range | `--window "2024-06-01 10:00 to 2024-06-09 12:00"` |

### Save to File

Save output to a JSON file:
```bash
python3 fetch_messages.py C1234567890 --window "24h" --output messages.json
```

### Limit Number of Messages

Fetch maximum 100 messages:
```bash
python3 fetch_messages.py C1234567890 --window "7d" --limit 100
```

## Output Format

The script outputs JSON in the following format:

```json
{
    "channel_name": "#rolling_release_hack_the_hive",
    "messages": [
        {
            "timestamp": "Jun 09, 2026 at 01:48:04 PM",
            "user": "Nurin",
            "content": "This one ^ Reply to Ravneet: 'can you reply to this test thread'"
        },
        {
            "timestamp": "Jun 09, 2026 at 02:12:48 PM",
            "user": "Ravneet",
            "content": "can you reply to this test thread"
        }
    ]
}
```

### Output Fields

- **channel_name**: The name of the Slack channel (with # prefix)
- **messages**: Array of message objects
  - **timestamp**: Human-readable timestamp (e.g., "Jun 09, 2026 at 01:48:04 PM")
  - **user**: Display name of the user who sent the message
  - **content**: Message text. For thread replies, includes context like "Reply to [User]: '[parent message]'"

## Use from Python Scripts

You can import and use the functionality in your own Python code.

### Method 1: Use `fetch_messages_as_json()` (Recommended)

```python
from fetch_messages import fetch_messages_as_json

# Get messages as a Python dictionary
result = fetch_messages_as_json(
    channel_id="C0B8ANUK57F",  # or use channel name
    window="1h",
    limit=1000
)

# Access the data
print(f"Channel: {result['channel_name']}")
print(f"Found {len(result['messages'])} messages")

# Iterate through messages
for msg in result["messages"]:
    print(f"[{msg['timestamp']}] {msg['user']}: {msg['content']}")

# Convert to JSON string
import json
json_string = json.dumps(result, indent=4)
```

### Method 2: Use `SlackMessageFetcher` Class

For more control, use the class directly:

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

# Process raw messages
for msg in messages:
    user_name = fetcher.get_user_name(msg['user'])
    print(f"{user_name}: {msg['text']}")
```

### Method 3: Parse Time Windows

Use the helper function to parse time window strings:

```python
from fetch_messages import SlackMessageFetcher, parse_time_window

fetcher = SlackMessageFetcher()

# Parse time window from string
start, end = parse_time_window("24h")
messages = fetcher.fetch_messages("C1234567890", start, end)
```

## Finding Channel IDs

### Option 1: Use the find_channel.py script

```bash
python3 find_channel.py rolling_release
```

Output:
```
Found: #rolling_release_hack_the_hive
ID: C0B8ANUK57F

Usage: python3 fetch_messages.py C0B8ANUK57F --window "1h"
```

### Option 2: Use list_channels.py script

```bash
python3 list_channels.py
```

This shows all channels the bot can access with their IDs.

### Option 3: From Slack UI

1. Right-click the channel in Slack
2. Select "View channel details"
3. Scroll to bottom - Channel ID is shown

## Features

- ✅ **Fetches all messages** including thread replies
- ✅ **Thread context** - Shows what message a reply is responding to
- ✅ **User names** - Displays real names instead of user IDs (requires `users:read` scope)
- ✅ **Channel names** - Shows channel names instead of IDs
- ✅ **JSON output** - Easy to parse and integrate with other tools
- ✅ **Flexible time windows** - Relative (1h, 7d) or absolute dates
- ✅ **Works with public and private channels** (requires appropriate scopes)
- ✅ **Can be imported** - Use as a library in your own Python scripts

## Required Slack Scopes

Your bot needs these scopes:

### For Public Channels:
- `channels:history` - View messages in public channels
- `channels:read` - View basic info about public channels

### For Private Channels:
- `groups:history` - View messages in private channels
- `groups:read` - View basic info about private channels

### For User Names:
- `users:read` - View user information (to show names instead of IDs)

### For Bot Functionality:
- `chat:write` - Send messages (if using bot.py)
- `app_mentions:read` - Respond to mentions

## Examples

### Example 1: Fetch Recent Messages

```bash
python3 fetch_messages.py C0B8ANUK57F --window "1h"
```

### Example 2: Export to JSON File

```bash
python3 fetch_messages.py rolling_release_hack_the_hive --window "24h" --output daily_messages.json
```

### Example 3: Get Messages from Specific Date

```bash
python3 fetch_messages.py C0B8ANUK57F --window "2024-06-09"
```

### Example 4: Use in Python Script

```python
from fetch_messages import fetch_messages_as_json
import json

# Fetch messages
result = fetch_messages_as_json("C0B8ANUK57F", window="24h")

# Filter for error messages
error_messages = [
    msg for msg in result["messages"]
    if "error" in msg["content"].lower()
]

print(f"Found {len(error_messages)} error messages")

# Save filtered results
with open("errors.json", "w") as f:
    json.dump({"messages": error_messages}, f, indent=4)
```

### Example 5: Process Messages in Real-time

```python
from fetch_messages import fetch_messages_as_json

# Fetch messages every hour
import time

while True:
    result = fetch_messages_as_json("C0B8ANUK57F", window="1h")

    # Process new messages
    for msg in result["messages"]:
        if "urgent" in msg["content"].lower():
            print(f"URGENT: {msg['user']}: {msg['content']}")

    # Wait 1 hour
    time.sleep(3600)
```

## Troubleshooting

### No messages returned?
- Check that bot is invited to the channel (`/invite @BotName`)
- Verify the time window contains messages
- Ensure channel ID is correct

### Permission errors?
- Make sure you have `channels:history` scope (public channels)
- Make sure you have `groups:history` scope (private channels)
- Reinstall app after adding scopes

### Rate limits?
- Slack allows ~1 request per second for conversations.history
- Script automatically handles pagination
- For large fetches, the script may take time but will complete

### User IDs instead of names?
- Add `users:read` scope to your bot
- Reinstall the app after adding the scope

### Channel not found by name?
- Use `python3 find_channel.py CHANNEL_NAME` to search
- Or use the channel ID directly: `python3 fetch_messages.py C1234567890`
- Channel names are case-insensitive

## API Reference

### `fetch_messages_as_json(channel_id, window="24h", limit=1000)`

Fetch messages and return as a formatted JSON dictionary.

**Parameters:**
- `channel_id` (str): Slack channel ID or channel name
- `window` (str): Time window (e.g., "1h", "24h", "7d")
- `limit` (int): Maximum number of messages to fetch

**Returns:**
- Dictionary with `channel_name` and `messages` array

**Raises:**
- `ValueError`: If channel not found

### `SlackMessageFetcher` Class

#### `__init__(bot_token=None)`
Initialize fetcher with optional bot token.

#### `fetch_messages(channel_id, start_time=None, end_time=None, limit=1000)`
Fetch raw messages from a channel within a time window.

**Returns:** List of message dictionaries with raw Slack data

#### `get_user_name(user_id)`
Get user's display name from user ID.

#### `get_channel_name(channel_id)`
Get channel name from channel ID.

#### `get_channel_id_by_name(channel_name)`
Get channel ID from channel name.

#### `get_thread_parent(channel_id, thread_ts)`
Get the parent message of a thread.

### `parse_time_window(window_str)`

Parse time window string into start and end datetime objects.

**Parameters:**
- `window_str` (str): Time window (e.g., "1h", "24h", "2024-06-01")

**Returns:**
- Tuple of (start_datetime, end_datetime)

## Comparison: Real-time vs Historical

| Feature | bot.py (Real-time) | fetch_messages.py (Historical) |
|---------|-------------------|-------------------------------|
| Use case | Monitor live messages | Fetch past messages |
| Requires | Socket Mode running 24/7 | Run on-demand |
| Time range | Only new messages | Any time window |
| Performance | Continuous connection | Query when needed |
| Output | Real-time events | JSON format |
| Best for | Live monitoring, alerts | Analysis, reporting, backfill |

## Integration Examples

### Integrate with a Web Service

```python
from flask import Flask, jsonify
from fetch_messages import fetch_messages_as_json

app = Flask(__name__)

@app.route('/messages/<channel_id>')
def get_messages(channel_id):
    window = request.args.get('window', '24h')
    result = fetch_messages_as_json(channel_id, window=window)
    return jsonify(result)

if __name__ == '__main__':
    app.run(port=5000)
```

### Scheduled Fetching (Cron Job)

Create a script `scheduled_fetch.py`:

```python
#!/usr/bin/env python3
from fetch_messages import fetch_messages_as_json
from datetime import datetime
import json

result = fetch_messages_as_json("C0B8ANUK57F", window="1h")

filename = f"messages_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
with open(filename, "w") as f:
    json.dump(result, f, indent=4)

print(f"Saved {len(result['messages'])} messages to {filename}")
```

Add to crontab:
```bash
# Run every hour
0 * * * * cd /home/ravneet-kaur/code/slack-bot && source .slack_bot_venv/bin/activate && python3 scheduled_fetch.py
```

## Need Help?

If you get stuck:
1. Check the Slack API docs: https://api.slack.com/docs
2. View your app's settings: https://api.slack.com/apps
3. Check script output for error messages
4. Verify all required scopes are added
5. Ensure bot is invited to the channel

## Security Notes

- Never commit your `.env` file to version control (it's in `.gitignore`)
- Never share your tokens publicly
- Rotate tokens if they're ever exposed
- Tokens can be regenerated from the Slack API dashboard if needed
