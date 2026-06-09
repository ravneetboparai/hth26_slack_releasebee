#!/usr/bin/env python3
"""
Example script showing how to use SlackMessageFetcher from another Python script.
"""

from datetime import datetime, timedelta
from fetch_messages import SlackMessageFetcher

# Initialize the fetcher
fetcher = SlackMessageFetcher()

# Example 1: Fetch messages from the last hour
print("Example 1: Last hour")
print("-" * 60)
channel_id = "C1234567890"  # Replace with your channel ID
messages = fetcher.fetch_messages(
    channel_id=channel_id,
    start_time=datetime.now() - timedelta(hours=1),
    end_time=datetime.now()
)
print(f"Found {len(messages)} messages in the last hour\n")

# Example 2: Fetch messages from a specific date range
print("Example 2: Specific date range")
print("-" * 60)
start = datetime(2024, 6, 1, 9, 0)  # June 1, 2024 at 9:00 AM
end = datetime(2024, 6, 1, 17, 0)   # June 1, 2024 at 5:00 PM
messages = fetcher.fetch_messages(
    channel_id=channel_id,
    start_time=start,
    end_time=end
)
print(f"Found {len(messages)} messages between {start} and {end}\n")

# Example 3: Get channel ID by name
print("Example 3: Get channel by name")
print("-" * 60)
channel_id = fetcher.get_channel_id_by_name("general")
if channel_id:
    print(f"Channel #general has ID: {channel_id}")
    messages = fetcher.fetch_messages(
        channel_id=channel_id,
        start_time=datetime.now() - timedelta(days=7)
    )
    print(f"Found {len(messages)} messages in the last 7 days\n")

# Example 4: Process messages
print("Example 4: Process messages")
print("-" * 60)
messages = fetcher.fetch_messages(
    channel_id=channel_id,
    start_time=datetime.now() - timedelta(hours=24)
)

for msg in messages:
    # Your custom processing logic here
    text = msg["text"]
    user = msg["user"]
    timestamp = msg["datetime"]

    # Example: Filter messages containing certain keywords
    if "error" in text.lower() or "bug" in text.lower():
        print(f"[{timestamp}] {user}: {text}")

print("\nProcessing complete!")
