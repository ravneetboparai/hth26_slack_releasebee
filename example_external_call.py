#!/usr/bin/env python3
"""
Example: How to use fetch_messages from another Python script.
"""

import json
from fetch_messages import fetch_messages_as_json

# Fetch messages and get as dictionary
result = fetch_messages_as_json(
    channel_id="C0B8ANUK57F",  # or use channel name like "rolling_release_hack_the_hive"
    window="1h",
    limit=100
)

# Convert to JSON string
json_output = json.dumps(result, indent=4)
print("JSON Output:")
print(json_output)

