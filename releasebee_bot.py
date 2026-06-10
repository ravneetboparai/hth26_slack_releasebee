#!/usr/bin/env python3
"""
Enhanced Releasebee Bot with:
- Release tracking
- Message analytics
- Natural language processing

Usage: python releasebee_bot.py
"""

import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv

from release_tracker import ReleaseTracker, process_message_for_release
from message_analytics import MessageAnalytics
from nlp_handler import NLPHandler
from fetch_messages import fetch_messages_as_json
from channel_config import get_channel_id, CHANNEL_IDS

# Load environment variables
load_dotenv()

# Initialize the Slack app
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

# Initialize modules
release_tracker = ReleaseTracker()
nlp = NLPHandler()


def resolve_channel(channel_identifier: str, current_channel: str = None) -> str:
    """
    Resolve channel name to ID using cache first.

    Args:
        channel_identifier: Channel name or ID
        current_channel: Fallback to current channel if identifier is None

    Returns:
        Channel ID
    """
    # If no identifier provided, use current channel
    if not channel_identifier:
        return current_channel

    # If already an ID, return it
    if channel_identifier.startswith("C"):
        return channel_identifier

    # Try to get from cache first
    channel_name = channel_identifier.lstrip("#").lower()
    cached_id = get_channel_id(channel_name)

    if cached_id:
        return cached_id

    # Fall back to the identifier (will be resolved by fetch_messages_as_json)
    return channel_identifier


@app.event("message")
def handle_message_events(event, logger):
    """
    Handle all message events - monitors for releases automatically.
    """
    # Ignore bot messages
    if event.get("bot_id") or event.get("subtype") == "bot_message":
        return

    message_data = {
        "text": event.get("text", ""),
        "user": event.get("user"),
        "channel": event.get("channel"),
        "timestamp": event.get("ts"),
    }

    # Auto-detect and track releases
    release = process_message_for_release(message_data, release_tracker)

    if release:
        logger.info(f"Release detected: {release['version']}")


@app.event("app_mention")
def handle_app_mentions(event, say, logger):
    """
    Handle @releasebee mentions with NLP understanding.
    """
    text = event.get("text", "")
    user_id = event.get("user")
    channel_id = event.get("channel")

    logger.info(f"Mention from {user_id}: {text}")

    # Parse the command using NLP
    parsed = nlp.parse_command(text)
    intent = parsed["intent"]

    try:
        if intent == "fetch_messages":
            handle_fetch_messages(parsed, say, channel_id)

        elif intent == "analyze":
            handle_analyze(parsed, say, channel_id)

        elif intent == "release_info":
            handle_release_info(parsed, say)

        elif intent == "search":
            handle_search(parsed, say, channel_id)

        elif intent == "help":
            handle_help(say)

        else:
            say(
                f"Hi <@{user_id}>! I'm not sure what you want. Try:\n"
                "• `@releasebee fetch messages from #channel`\n"
                "• `@releasebee analyze last 24h`\n"
                "• `@releasebee what's the latest release?`\n"
                "• `@releasebee help`"
            )

    except Exception as e:
        logger.error(f"Error handling mention: {e}")
        say(f"Sorry, I encountered an error: {str(e)}")


def handle_fetch_messages(parsed: dict, say, current_channel: str):
    """Handle fetch messages request."""
    # Resolve channel using cache first
    channel = resolve_channel(parsed.get("channel"), current_channel)
    time_window = parsed.get("time_window", "24h")
    time_desc = parsed.get("time_description", "last 24 hours")

    say(f"Fetching messages from <#{channel}> ({time_desc})...")

    # Retry logic for network errors
    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = fetch_messages_as_json(channel, window=time_window, limit=50)
            messages = result.get("messages", [])
            channel_name = result.get("channel_name", channel)

            if not messages:
                say(f"No messages found in {channel_name} for {time_desc}")
                return

            # Show preview
            preview = f"*Found {len(messages)} messages in {channel_name}*\n\n"
            for i, msg in enumerate(messages[:5], 1):
                user = msg.get("user", "Unknown")
                content = msg.get("content", "")[:100]
                preview += f"{i}. *{user}*: {content}...\n"

            if len(messages) > 5:
                preview += f"\n_...and {len(messages) - 5} more messages_"

            say(preview)
            return  # Success

        except Exception as e:
            error_msg = str(e).lower()

            if any(x in error_msg for x in ['ssl', 'eof', 'connection', 'timeout']):
                if attempt < max_retries - 1:
                    say(f"Network issue, retrying... (attempt {attempt + 2}/{max_retries})")
                    import time
                    time.sleep(2)
                    continue
                else:
                    say(f"Network error after {max_retries} attempts. Please try again in a moment.")
            else:
                say(f"Error fetching messages: {str(e)}")
            return


def handle_analyze(parsed: dict, say, current_channel: str):
    """Handle analyze request."""
    # Resolve channel using cache first
    channel = resolve_channel(parsed.get("channel"), current_channel)
    time_window = parsed.get("time_window", "24h")
    time_desc = parsed.get("time_description", "last 24 hours")

    say(f"Analyzing messages from <#{channel}> ({time_desc})...")

    # Retry logic for network errors
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Fetch messages
            result = fetch_messages_as_json(channel, window=time_window, limit=1000)
            messages = result.get("messages", [])
            channel_name = result.get("channel_name", channel)

            if not messages:
                say(f"No messages to analyze in {channel_name}")
                return

            # Analyze
            analytics = MessageAnalytics()
            analytics.add_messages(messages)
            summary = analytics.generate_summary(channel_name)

            say(summary)
            return  # Success, exit function

        except Exception as e:
            error_msg = str(e).lower()

            # Check if it's a network/SSL error
            if any(x in error_msg for x in ['ssl', 'eof', 'connection', 'timeout']):
                if attempt < max_retries - 1:
                    say(f"Network issue, retrying... (attempt {attempt + 2}/{max_retries})")
                    import time
                    time.sleep(2)  # Wait 2 seconds before retry
                    continue
                else:
                    say(f"Network error after {max_retries} attempts. Please try again in a moment.")
            else:
                say(f"Error analyzing messages: {str(e)}")
            return


def handle_release_info(parsed: dict, say):
    """Handle release information request."""
    say("Looking up release information...")

    # Get recent releases
    recent = release_tracker.get_recent_releases(limit=5)

    if not recent:
        say("No releases tracked yet. I'll start monitoring for releases!")
        return

    # Format response
    response = "*Recent Releases:*\n\n"

    for i, release in enumerate(recent, 1):
        version = release.get("version")
        user = release.get("user")
        channel = release.get("channel")
        timestamp = release.get("timestamp", "")

        response += f"{i}. *v{version}* released by {user} in <#{channel}>\n"
        response += f"   {timestamp}\n\n"

    # Add statistics
    stats = release_tracker.get_statistics()
    response += f"\n*Total releases tracked:* {stats['total_releases']}"

    say(response)


def handle_search(parsed: dict, say, current_channel: str):
    """Handle search request."""
    query = parsed.get("search_query")
    # Resolve channel using cache first
    channel = resolve_channel(parsed.get("channel"), current_channel)
    time_window = parsed.get("time_window", "7d")

    if not query:
        say("Please specify what to search for. Example: `search for 'release'`")
        return

    say(f"Searching for '{query}' in <#{channel}>...")

    try:
        # Fetch messages
        result = fetch_messages_as_json(channel, window=time_window, limit=1000)
        messages = result.get("messages", [])

        # Search
        matches = [
            msg for msg in messages
            if query.lower() in msg.get("content", "").lower()
        ]

        if not matches:
            say(f"No messages found containing '{query}'")
            return

        # Format results
        response = f"*Found {len(matches)} messages containing '{query}':*\n\n"

        for i, msg in enumerate(matches[:10], 1):
            user = msg.get("user", "Unknown")
            content = msg.get("content", "")
            timestamp = msg.get("timestamp", "")

            # Highlight the query
            highlighted = content.replace(query, f"*{query}*")

            response += f"{i}. *{user}* - {timestamp}\n"
            response += f"   {highlighted[:150]}...\n\n"

        if len(matches) > 10:
            response += f"\n_...and {len(matches) - 10} more matches_"

        say(response)

    except Exception as e:
        say(f"Error searching: {str(e)}")


def handle_help(say):
    """Show help message."""
    # Show cached channels if available
    cached_channels = ""
    if CHANNEL_IDS:
        cached_list = ", ".join([f"#{name}" for name in list(CHANNEL_IDS.keys())[:5]])
        cached_channels = f"\n*Cached Channels:*\n{cached_list}\n"

    help_text = f"""
*🐝 Releasebee Bot - Help*

I can help you track releases, analyze messages, and search conversations!

*Commands:*

*📦 Release Tracking*
• `@releasebee what's the latest release?`
• `@releasebee show recent releases`
• I automatically detect and track releases when you mention version numbers!

*📊 Message Analytics*
• `@releasebee analyze #channel last 24h`
• `@releasebee analyze sentiment in #engineering`
• `@releasebee how active was #releases today?`

*🔍 Search Messages*
• `@releasebee search for 'bug fix' in #engineering`
• `@releasebee find 'production' last 7 days`

*💬 Fetch Messages*
• `@releasebee fetch messages from #channel`
• `@releasebee show me what happened yesterday`
• `@releasebee get messages last 2 hours`

*Time Windows:*
• 30min, 1h, 2h, 24h
• today, yesterday
• 7d, 30d

*Examples:*
• `@releasebee analyze #releases today`
• `@releasebee fetch messages from #engineering last 2h`
• `@releasebee search for 'deployment' in #devops`
{cached_channels}
_I'm watching for release announcements and will automatically track them!_ 🚀
"""
    say(help_text)


@app.command("/releasebee")
def handle_slash_command(ack, command, respond, logger):
    """
    Handle /releasebee slash command.
    Returns a short summary of the conversation.
    """
    # Acknowledge the command immediately (required within 3 seconds)
    ack()

    text = command.get("text", "").strip()
    user_id = command.get("user_id")
    channel_id = command.get("channel_id")

    logger.info(f"Slash command from {user_id}: /releasebee {text}")

    # Parse arguments
    args = text.split() if text else []

    # Check for help or no arguments
    if not args or text.lower() in ["help", "--help", "-h"]:
        respond(
            text="Usage: `/releasebee CHANNEL_NAME [TIME_WINDOW]`\n\n"
                 "Returns a short summary of the conversation.\n\n"
                 "Examples:\n"
                 "  • `/releasebee general`\n"
                 "  • `/releasebee engineering 1h`\n"
                 "  • `/releasebee rolling_release_hack_the_hive 1h`\n\n"
                 "Time windows: 5min, 30min, 1h, 24h, 7d",
            response_type="ephemeral"
        )
        return

    target_channel = args[0]
    time_window = args[1] if len(args) > 1 else "24h"

    # Resolve channel using cache
    channel = resolve_channel(target_channel, channel_id)

    try:
        # Fetch messages with retry logic
        max_retries = 3
        result = None

        for attempt in range(max_retries):
            try:
                logger.info(f"Fetching messages from {channel} for last {time_window}...")
                result = fetch_messages_as_json(channel, window=time_window, limit=100)
                break
            except Exception as e:
                error_msg = str(e).lower()
                if any(x in error_msg for x in ['ssl', 'eof', 'connection', 'timeout']):
                    if attempt < max_retries - 1:
                        logger.warning(f"Network error, retrying... (attempt {attempt + 2}/{max_retries})")
                        import time
                        time.sleep(2)
                        continue
                raise

        if not result:
            respond(
                text="Network error. Please try again in a moment.",
                response_type="ephemeral"
            )
            return

        messages = result.get("messages", [])
        channel_name = result.get("channel_name", target_channel)

        if not messages:
            respond(
                text=f"No messages found in {channel_name} for the last {time_window}",
                response_type="ephemeral"
            )
            return

        # Generate conversational summary
        summary = generate_conversation_summary(messages, channel_name, time_window)

        respond(
            text=summary,
            response_type="ephemeral"
        )

    except Exception as e:
        logger.error(f"Error handling slash command: {e}")
        respond(
            text=f"Error: {str(e)}",
            response_type="ephemeral"
        )


def generate_conversation_summary(messages: list, channel_name: str, time_window: str) -> str:
    """
    Generate a short conversational summary from messages.
    """
    from collections import Counter
    import re

    total = len(messages)

    # Get unique participants
    participants = set(msg.get("user", "Unknown") for msg in messages)

    # Extract key topics (mentioned multiple times)
    all_words = []
    for msg in messages:
        content = msg.get("content", "").lower()
        # Extract meaningful words (skip common words)
        words = re.findall(r'\b[a-z]{4,}\b', content)
        all_words.extend(words)

    # Common words to skip
    skip_words = {'that', 'this', 'with', 'from', 'have', 'been', 'were',
                  'they', 'what', 'when', 'where', 'which', 'there', 'about',
                  'just', 'will', 'your', 'also', 'some', 'more', 'than'}

    word_counts = Counter(word for word in all_words if word not in skip_words)
    top_topics = [word for word, count in word_counts.most_common(5) if count > 1]

    # Detect key activities
    activities = []
    for msg in messages:
        content = msg.get("content", "").lower()
        if any(word in content for word in ['release', 'released', 'shipped']):
            activities.append("releases")
        if any(word in content for word in ['error', 'bug', 'issue', 'problem']):
            activities.append("issues")
        if any(word in content for word in ['fix', 'fixed', 'resolved']):
            activities.append("fixes")
        if any(word in content for word in ['test', 'testing', 'tested']):
            activities.append("testing")
        if '?' in content:
            activities.append("questions")

    activity_counts = Counter(activities)

    # Build summary
    summary = f"*Summary: {channel_name}* (last {time_window})\n\n"
    summary += f"{total} messages from {len(participants)} people.\n\n"

    # Main topics
    if top_topics:
        summary += f"*Main topics:* {', '.join(top_topics[:3])}\n\n"

    # Activities
    if activity_counts:
        activity_list = [f"{count} {activity}" for activity, count in activity_counts.most_common(3)]
        summary += f"*Discussion included:* {', '.join(activity_list)}\n\n"

    # Recent highlights (last 3 messages)
    summary += f"*Recent conversation:*\n"
    for msg in messages[-3:]:
        user = msg.get("user", "Unknown")
        content = msg.get("content", "")
        # Truncate if too long
        if len(content) > 80:
            content = content[:80] + "..."
        summary += f"• {user}: {content}\n"

    return summary


def main():
    """Start the Slack bot."""
    app_token = os.environ.get("SLACK_APP_TOKEN")

    if not app_token:
        raise ValueError("SLACK_APP_TOKEN environment variable is required")

    print("=" * 60)
    print("🐝 Releasebee Bot Starting...")
    print("=" * 60)
    print("Features:")
    print("  ✅ Release tracking (automatic)")
    print("  ✅ Message analytics")
    print("  ✅ Natural language understanding")
    print("  ✅ Search functionality")
    print("  ✅ Channel ID caching (reduces API calls)")
    print()
    print(f"Cached channels: {len(CHANNEL_IDS)}")
    if CHANNEL_IDS:
        for name in list(CHANNEL_IDS.keys())[:5]:
            print(f"  • {name}")
        if len(CHANNEL_IDS) > 5:
            print(f"  ... and {len(CHANNEL_IDS) - 5} more")
    print("=" * 60)
    print()

    # Start the bot
    handler = SocketModeHandler(app, app_token)
    print("⚡️ Releasebee is running!")
    print("Monitoring for releases and mentions...")
    print()
    handler.start()


if __name__ == "__main__":
    main()
