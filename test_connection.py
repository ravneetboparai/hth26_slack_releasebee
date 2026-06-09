#!/usr/bin/env python3
"""
Test script to verify Slack bot connection and configuration.
"""

import os
from dotenv import load_dotenv
from slack_bolt import App

# Load environment variables
load_dotenv()

bot_token = os.environ.get("SLACK_BOT_TOKEN")
app_token = os.environ.get("SLACK_APP_TOKEN")

print("="*60)
print("Slack Bot Connection Test")
print("="*60)

# Check if tokens exist
if not bot_token:
    print("❌ SLACK_BOT_TOKEN not found in .env file")
    exit(1)
if not app_token:
    print("❌ SLACK_APP_TOKEN not found in .env file")
    exit(1)

print("✅ Bot token found (starts with: {})".format(bot_token[:10]))
print("✅ App token found (starts with: {})".format(app_token[:10]))

# Initialize app
try:
    app = App(token=bot_token)
    print("✅ Slack app initialized successfully")
except Exception as e:
    print(f"❌ Failed to initialize app: {e}")
    exit(1)

# Test auth
try:
    response = app.client.auth_test()
    print("\n" + "="*60)
    print("Bot Information:")
    print("="*60)
    print(f"✅ Bot User ID: {response['user_id']}")
    print(f"✅ Bot Name: {response['user']}")
    print(f"✅ Team: {response['team']}")
    print(f"✅ Team ID: {response['team_id']}")
except Exception as e:
    print(f"❌ Authentication failed: {e}")
    exit(1)

# List scopes
try:
    response = app.client.api_call("auth.test")
    print("\n" + "="*60)
    print("Checking Scopes:")
    print("="*60)

    # Try to get conversations list to test permissions
    try:
        channels = app.client.conversations_list(types="public_channel,private_channel")
        channel_list = channels.get('channels', [])

        public_count = sum(1 for c in channel_list if not c.get('is_private'))
        private_count = sum(1 for c in channel_list if c.get('is_private'))

        print(f"✅ Can see {public_count} public channels")
        print(f"✅ Can see {private_count} private channels")

        if private_count == 0:
            print("\n⚠️  WARNING: Bot can't see any private channels!")
            print("   If you're trying to monitor a private channel, you need:")
            print("   - Scopes: groups:history, groups:read")
            print("   - Event: message.groups")
            print("   - Reinstall the app after adding scopes")

    except Exception as e:
        print(f"⚠️  Limited permissions: {e}")
        print("   This might be normal, but check if you have the scopes you need")

except Exception as e:
    print(f"⚠️  Could not check all permissions: {e}")

print("\n" + "="*60)
print("Connection Test Complete")
print("="*60)
print("\nNext Steps:")
print("1. Make sure bot is invited to the channel (/invite @BotName)")
print("2. For PRIVATE channels: add groups:history, groups:read scopes")
print("3. For PRIVATE channels: add message.groups event subscription")
print("4. Reinstall app after adding new scopes")
print("5. Run: python bot.py")
