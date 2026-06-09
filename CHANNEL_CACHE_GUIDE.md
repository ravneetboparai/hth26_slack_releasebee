# Channel Cache Guide

This guide explains how to use the channel cache system to avoid rate limits.

## Why Use Channel Cache?

Slack rate limits API calls. Looking up channel IDs by name requires calling the Slack API, which counts toward your rate limit. By caching channel IDs locally, you can:

- ✅ Avoid rate limit errors
- ✅ Speed up script execution
- ✅ Reduce unnecessary API calls

## How It Works

1. Channel names and IDs are stored in `channel_config.py`
2. Scripts check the cache first before calling the Slack API
3. If not cached, scripts fall back to API lookup

### Add a New Channel

```bash
python3 add_channel.py general
```

This will:
1. Look up the channel ID via Slack API
2. Add it to `channel_config.py`
3. Display the result

## Manual Configuration

You can also manually edit `channel_config.py`:

```python
CHANNEL_IDS = {
    "rolling_release_hack_the_hive": "C0B8ANUK57F",
    "general": "C1234567890",
    "random": "C0987654321",
}
```

### Use Cached Channels

Once cached, just use the channel name:

```bash
python3 fetch_messages.py rolling_release_hack_the_hive --window "1h"
```

No API lookup needed! The script uses the cached ID.

## Commands

### Add a Channel
```bash
python3 add_channel.py CHANNEL_NAME
```

Looks up and caches a channel. Examples:
```bash
python3 add_channel.py general
python3 add_channel.py random
python3 add_channel.py "#engineering"  # # is optional
```

### Use a Cached Channel
```bash
python3 fetch_messages.py CHANNEL_NAME --window "1h"
```

Automatically uses cached ID if available.
