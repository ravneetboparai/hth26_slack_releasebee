#!/usr/bin/env python3
"""
Fetch Slack messages from a specific time window.
Can be used as a standalone script or imported by other Python scripts.
"""

import os
import argparse
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
        self._user_cache = {}  # Cache user info to avoid repeated API calls
        self._channel_cache = {}  # Cache channel info
        self._thread_cache = {}  # Cache thread parent messages

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

            # Fetch thread replies for messages that have threads
            all_messages = []
            for msg in messages:
                # Add the parent message
                all_messages.append(msg)

                # If this message has replies, fetch them
                if msg.get("reply_count", 0) > 0 and msg.get("ts"):
                    try:
                        thread_response = self.client.conversations_replies(
                            channel=channel_id,
                            ts=msg["ts"]
                        )
                        thread_messages = thread_response.get("messages", [])
                        # Skip the first message (it's the parent, already added)
                        for thread_msg in thread_messages[1:]:
                            # Only include replies within our time window
                            msg_ts = float(thread_msg.get("ts", 0))
                            if start_timestamp <= msg_ts <= end_timestamp:
                                all_messages.append(thread_msg)
                    except SlackApiError:
                        # If we can't fetch thread replies, continue
                        pass

            # Filter out bot messages and format
            formatted_messages = []
            for msg in all_messages:
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

    def get_user_name(self, user_id):
        """
        Get user's display name from user ID.

        Args:
            user_id: Slack user ID (e.g., 'U1234567890')

        Returns:
            User's display name or user ID if not found
        """
        if not user_id:
            return "Unknown User"

        # Check cache first
        if user_id in self._user_cache:
            return self._user_cache[user_id]

        try:
            response = self.client.users_info(user=user_id)
            user = response.get("user", {})

            # Prefer display name, fall back to real name, then username
            name = (
                user.get("profile", {}).get("display_name")
                or user.get("profile", {}).get("real_name")
                or user.get("name")
                or user_id
            )

            self._user_cache[user_id] = name
            return name

        except SlackApiError as e:
            # If we can't get the name, show a warning once
            if "_user_read_warning_shown" not in self.__dict__:
                self._user_read_warning_shown = True
                error_msg = e.response.get("error", "unknown")
                if error_msg == "missing_scope":
                    print("\nWARNING: Bot is missing 'users:read' scope - showing user IDs instead of names")
                    print("To fix: Add 'users:read' scope in Slack app settings and reinstall\n")

            # Cache the ID so we don't keep trying
            self._user_cache[user_id] = user_id
            return user_id

    def get_channel_name(self, channel_id):
        """
        Get channel name from channel ID.

        Args:
            channel_id: Slack channel ID (e.g., 'C1234567890')

        Returns:
            Channel name or channel ID if not found
        """
        if not channel_id:
            return "Unknown Channel"

        # Check cache first
        if channel_id in self._channel_cache:
            return self._channel_cache[channel_id]

        try:
            response = self.client.conversations_info(channel=channel_id)
            channel = response.get("channel", {})
            name = channel.get("name") or channel_id

            self._channel_cache[channel_id] = name
            return name

        except SlackApiError:
            self._channel_cache[channel_id] = channel_id
            return channel_id

    def get_thread_parent(self, channel_id, thread_ts):
        """
        Get the parent message of a thread.

        Args:
            channel_id: Slack channel ID
            thread_ts: Thread timestamp (parent message timestamp)

        Returns:
            Dictionary with parent message info or None if not found
        """
        if not thread_ts:
            return None

        # Check cache first
        cache_key = f"{channel_id}:{thread_ts}"
        if cache_key in self._thread_cache:
            return self._thread_cache[cache_key]

        try:
            # Fetch the specific message using conversations.history with inclusive timestamps
            response = self.client.conversations_history(
                channel=channel_id,
                oldest=thread_ts,
                latest=thread_ts,
                inclusive=True,
                limit=1
            )

            messages = response.get("messages", [])
            if messages:
                parent_msg = messages[0]
                result = {
                    "text": parent_msg.get("text", ""),
                    "user": parent_msg.get("user"),
                    "timestamp": parent_msg.get("ts")
                }
                self._thread_cache[cache_key] = result
                return result

        except SlackApiError:
            pass

        # Cache None so we don't keep trying
        self._thread_cache[cache_key] = None
        return None

    def get_channel_id_by_name(self, channel_name):
        """
        Get channel ID from channel name.

        Args:
            channel_name: Channel name (with or without #)

        Returns:
            Channel ID or None if not found
        """
        # Remove # if present
        channel_name = channel_name.lstrip("#").lower()

        try:
            # Fetch all channels with pagination
            cursor = None
            all_channels = []

            while True:
                response = self.client.conversations_list(
                    types="public_channel,private_channel",
                    limit=1000,
                    cursor=cursor
                )

                channels = response.get("channels", [])
                all_channels.extend(channels)

                # Check for more pages
                cursor = response.get("response_metadata", {}).get("next_cursor")
                if not cursor:
                    break

            # Search for matching channel (case-insensitive)
            for channel in all_channels:
                if channel.get("name", "").lower() == channel_name:
                    channel_id = channel.get("id")
                    # Cache it
                    self._channel_cache[channel_id] = channel.get("name")
                    return channel_id

            # If not found, show similar channels for debugging
            print(f"\nChannel '{channel_name}' not found.")
            similar = [c.get("name") for c in all_channels if channel_name in c.get("name", "").lower()]
            if similar:
                print(f"Did you mean one of these? {', '.join(similar[:5])}")

            return None

        except SlackApiError as e:
            print(f"Error fetching channels: {e.response['error']}")
            return None


def fetch_messages_as_json(channel_id, window="24h", limit=1000):
    """
    Fetch messages and return as a formatted JSON dictionary.
    Useful for calling from other Python scripts.

    Args:
        channel_id: Slack channel ID or name
        window: Time window string (e.g., "1h", "24h", "7d")
        limit: Maximum number of messages to fetch

    Returns:
        Dictionary with formatted messages ready for JSON serialization
    """
    fetcher = SlackMessageFetcher()

    # Get channel ID if name is provided
    if not channel_id.startswith("C"):
        channel_id = fetcher.get_channel_id_by_name(channel_id)
        if not channel_id:
            raise ValueError(f"Channel not found")

    # Parse time window
    start_time, end_time = parse_time_window(window)

    # Fetch messages
    messages = fetcher.fetch_messages(channel_id, start_time, end_time, limit)
    channel_name = f"#{fetcher.get_channel_name(channel_id)}"

    # Format messages for JSON output
    formatted_messages = []
    for msg in messages:
        msg_time = datetime.fromisoformat(msg['datetime'])
        time_str = msg_time.strftime("%b %d, %Y at %I:%M:%S %p")
        user_name = fetcher.get_user_name(msg['user'])

        # Build content with thread context if applicable
        content = msg['text']
        if msg.get('thread_ts') and msg['thread_ts'] != msg['timestamp']:
            parent = fetcher.get_thread_parent(channel_id, msg['thread_ts'])
            if parent:
                parent_user = fetcher.get_user_name(parent.get('user'))
                parent_text = parent.get('text', '')
                if len(parent_text) > 60:
                    parent_text = parent_text[:60] + "..."
                content = f"{content} Reply to {parent_user}: '{parent_text}'"

        formatted_messages.append({
            "timestamp": time_str,
            "user": user_name,
            "content": content
        })

    # Build final JSON output
    return {
        "channel_name": channel_name,
        "messages": formatted_messages
    }


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
    except Exception as e:
        print(f"Error parsing time window: {e}")
        return

    # Fetch messages
    try:
        import json

        messages = fetcher.fetch_messages(channel_id, start_time, end_time, args.limit)
        channel_name = f"#{fetcher.get_channel_name(channel_id)}"

        # Format messages for JSON output
        formatted_messages = []
        for msg in messages:
            # Parse datetime
            msg_time = datetime.fromisoformat(msg['datetime'])
            time_str = msg_time.strftime("%b %d, %Y at %I:%M:%S %p")

            # Get user name
            user_name = fetcher.get_user_name(msg['user'])

            # Build content with thread context if applicable
            content = msg['text']
            if msg.get('thread_ts') and msg['thread_ts'] != msg['timestamp']:
                parent = fetcher.get_thread_parent(channel_id, msg['thread_ts'])
                if parent:
                    parent_user = fetcher.get_user_name(parent.get('user'))
                    parent_text = parent.get('text', '')
                    # Truncate parent text if too long
                    if len(parent_text) > 60:
                        parent_text = parent_text[:60] + "..."
                    content = f"{content} Reply to {parent_user}: '{parent_text}'"

            formatted_messages.append({
                "timestamp": time_str,
                "user": user_name,
                "content": content
            })

        # Build final JSON output
        output = {
            # "message_start_timestamp": start_time.strftime("%Y-%m-%d %H:%M:%S"),
            # "message_end_timestamp": end_time.strftime("%Y-%m-%d %H:%M:%S"),
            "channel_name": channel_name,
            "messages": formatted_messages
        }

        # Output JSON
        if args.output:
            with open(args.output, "w") as f:
                json.dump(output, f, indent=4)
            print(f"Saved {len(messages)} messages to {args.output}")
        else:
            print(json.dumps(output, indent=4))

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
