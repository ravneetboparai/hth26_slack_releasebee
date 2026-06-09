#!/usr/bin/env python3
"""
Fetch Slack messages from a specific time window.
Can be used as a standalone script or imported by other Python scripts.
"""

import os
from datetime import datetime, timedelta
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class SlackMessageFetcher:
    """Fetch messages from Slack channels within a specified time window."""

    def __init__(self, bot_token=None):
        """
        Initialize the Slack message fetcher.

        Args:
            bot_token: Slack bot token (xoxb-...). If None, reads from SLACK_BOT_TOKEN env var.
        """
        self.token = bot_token or os.environ.get("SLACK_BOT_TOKEN")
        if not self.token:
            raise ValueError("SLACK_BOT_TOKEN is required")

        self.client = WebClient(token=self.token)

    def fetch_messages(self, channel_id, start_time=None, end_time=None, limit=1000):
        """
        Fetch messages from a channel within a time window.

        Args:
            channel_id: Slack channel ID (e.g., 'C1234567890')
            start_time: Start of time window (datetime object or Unix timestamp)
                       If None, fetches from 24 hours ago
            end_time: End of time window (datetime object or Unix timestamp)
                     If None, uses current time
            limit: Maximum number of messages to fetch (default 1000)

        Returns:
            List of message dictionaries
        """
        # Convert datetime to Unix timestamp if needed
        if start_time is None:
            start_time = datetime.now() - timedelta(hours=24)

        if isinstance(start_time, datetime):
            start_timestamp = start_time.timestamp()
        else:
            start_timestamp = float(start_time)

        if end_time is None:
            end_time = datetime.now()

        if isinstance(end_time, datetime):
            end_timestamp = end_time.timestamp()
        else:
            end_timestamp = float(end_time)

        messages = []
        cursor = None

        try:
            while True:
                # Fetch messages using conversations.history
                response = self.client.conversations_history(
                    channel=channel_id,
                    oldest=str(start_timestamp),
                    latest=str(end_timestamp),
                    limit=min(limit - len(messages), 1000),  # Slack max is 1000 per call
                    cursor=cursor
                )

                if not response["ok"]:
                    raise SlackApiError(f"API error: {response.get('error')}", response)

                # Add messages to list
                batch_messages = response.get("messages", [])
                messages.extend(batch_messages)

                # Check if we have more messages to fetch
                cursor = response.get("response_metadata", {}).get("next_cursor")
                if not cursor or len(messages) >= limit:
                    break

            # Filter out bot messages and format
            formatted_messages = []
            for msg in messages:
                # Skip bot messages
                if msg.get("bot_id"):
                    continue

                formatted_msg = {
                    "text": msg.get("text", ""),
                    "user": msg.get("user"),
                    "channel": channel_id,
                    "timestamp": msg.get("ts"),
                    "thread_ts": msg.get("thread_ts"),
                    "type": msg.get("type"),
                    "subtype": msg.get("subtype"),
                    "datetime": datetime.fromtimestamp(float(msg.get("ts"))).isoformat(),
                }
                formatted_messages.append(formatted_msg)

            # Sort by timestamp (oldest first)
            formatted_messages.sort(key=lambda x: float(x["timestamp"]))

            return formatted_messages

        except SlackApiError as e:
            print(f"Error fetching messages: {e.response['error']}")
            raise

    def get_channel_id_by_name(self, channel_name):
        """
        Get channel ID from channel name.

        Args:
            channel_name: Channel name (with or without #)

        Returns:
            Channel ID or None if not found
        """
        # Remove # if present
        channel_name = channel_name.lstrip("#")

        try:
            # Fetch all channels
            response = self.client.conversations_list(
                types="public_channel,private_channel",
                limit=1000
            )

            for channel in response.get("channels", []):
                if channel.get("name") == channel_name:
                    return channel.get("id")

            return None

        except SlackApiError as e:
            print(f"Error fetching channels: {e.response['error']}")
            return None


def parse_time_window(window_str):
    """
    Parse time window string into start and end datetime objects.

    Supported formats:
    - "1h" - last 1 hour
    - "24h" - last 24 hours
    - "7d" - last 7 days
    - "2023-01-01 10:00 to 2023-01-01 12:00" - specific range
    - "2023-01-01" - entire day

    Args:
        window_str: Time window string

    Returns:
        Tuple of (start_datetime, end_datetime)
    """
    now = datetime.now()

    # Parse relative time (e.g., "1h", "24h", "7d")
    if window_str.endswith("h"):
        hours = int(window_str[:-1])
        return now - timedelta(hours=hours), now
    elif window_str.endswith("d"):
        days = int(window_str[:-1])
        return now - timedelta(days=days), now
    elif window_str.endswith("m"):
        minutes = int(window_str[:-1])
        return now - timedelta(minutes=minutes), now

    # Parse range (e.g., "2023-01-01 10:00 to 2023-01-01 12:00")
    elif " to " in window_str:
        start_str, end_str = window_str.split(" to ")
        start_time = datetime.fromisoformat(start_str.strip())
        end_time = datetime.fromisoformat(end_str.strip())
        return start_time, end_time

    # Parse single date (entire day)
    else:
        date = datetime.fromisoformat(window_str.strip())
        start_time = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        return start_time, end_time


def main():
    """Command-line interface for fetching messages."""
    import argparse

    parser = argparse.ArgumentParser(description="Fetch Slack messages from a time window")
    parser.add_argument("channel", help="Channel ID or name (e.g., C1234567890 or #general)")
    parser.add_argument(
        "--window",
        default="24h",
        help='Time window (e.g., "1h", "24h", "7d", "2023-01-01", "2023-01-01 10:00 to 2023-01-01 12:00")',
    )
    parser.add_argument("--limit", type=int, default=1000, help="Maximum number of messages to fetch")
    parser.add_argument("--output", help="Output JSON file (optional)")

    args = parser.parse_args()

    # Initialize fetcher
    fetcher = SlackMessageFetcher()

    # Get channel ID if name is provided
    channel_id = args.channel
    if not channel_id.startswith("C"):
        print(f"Looking up channel ID for '{args.channel}'...")
        channel_id = fetcher.get_channel_id_by_name(args.channel)
        if not channel_id:
            print(f"Error: Channel '{args.channel}' not found")
            return
        print(f"Found channel ID: {channel_id}")

    # Parse time window
    try:
        start_time, end_time = parse_time_window(args.window)
        print(f"\nFetching messages from:")
        print(f"  Start: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  End:   {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        print(f"Error parsing time window: {e}")
        return

    # Fetch messages
    try:
        messages = fetcher.fetch_messages(channel_id, start_time, end_time, args.limit)
        print(f"\nFetched {len(messages)} messages\n")

        # Display messages
        for msg in messages:
            print("=" * 60)
            print(f"Time: {msg['datetime']}")
            print(f"User: {msg['user']}")
            print(f"Text: {msg['text']}")
            print("=" * 60)
            print()

        # Save to file if requested
        if args.output:
            import json

            with open(args.output, "w") as f:
                json.dump(messages, f, indent=2)
            print(f"\n✅ Saved {len(messages)} messages to {args.output}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
