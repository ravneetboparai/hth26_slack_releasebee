#!/usr/bin/env python3
"""
Slack Bot that monitors messages in a channel and feeds them to a Python service.
Uses Socket Mode for real-time message monitoring without needing a public endpoint.
"""

import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize the Slack app
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))


def process_message(message_data):
    """
    Process the incoming message - customize this function to feed data to your service.

    Args:
        message_data: Dictionary containing message information
    """
    print(f"\n{'='*60}")
    print(f"New message received:")
    print(f"  Channel: {message_data['channel']}")
    print(f"  User: {message_data['user']}")
    print(f"  Text: {message_data['text']}")
    print(f"  Timestamp: {message_data['timestamp']}")
    print(f"{'='*60}\n")

    # TODO: Add your service integration here
    # Example: send_to_your_service(message_data)


@app.event("message")
def handle_message_events(event, say, logger):
    """
    Handle all message events in channels the bot is added to.
    """
    # Ignore bot messages to prevent loops
    if event.get("bot_id"):
        return

    # Extract message data
    message_data = {
        "text": event.get("text", ""),
        "user": event.get("user"),
        "channel": event.get("channel"),
        "timestamp": event.get("ts"),
        "thread_ts": event.get("thread_ts"),
        "channel_type": event.get("channel_type"),
    }

    # Process the message
    try:
        process_message(message_data)
    except Exception as e:
        logger.error(f"Error processing message: {e}")


@app.event("app_mention")
def handle_app_mentions(event, say, logger):
    """
    Handle when the bot is mentioned in a message.
    """
    user = event["user"]
    say(f"Hi <@{user}>! I'm monitoring messages in this channel.")


# Optional: Handle direct messages
@app.event("im_message")
def handle_dm(event, say):
    """
    Handle direct messages to the bot.
    """
    say("I'm monitoring channel messages and feeding them to a Python service!")


def main():
    """
    Start the Slack bot using Socket Mode.
    """
    # Get the Socket Mode app token
    app_token = os.environ.get("SLACK_APP_TOKEN")

    if not app_token:
        raise ValueError("SLACK_APP_TOKEN environment variable is required")

    # Start the bot
    handler = SocketModeHandler(app, app_token)
    print("⚡️ Slack bot is running!")
    print("Monitoring messages in channels where the bot is added...")
    handler.start()


if __name__ == "__main__":
    main()
