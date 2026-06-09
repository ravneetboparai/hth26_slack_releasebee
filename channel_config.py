"""
Channel ID configuration file.
Maps channel names to their IDs to avoid repeated API lookups.

To add new channels, either:
1. Manually add them here in the format: "channel_name": "CHANNEL_ID"
2. Run: python3 add_channel.py CHANNEL_NAME
"""

CHANNEL_IDS = {
    "rolling_release_hack_the_hive": "C0B8ANUK57F",
    "releasebee-test": "C0B9ASSE28M",
    # Add more channels here as needed
    # "general": "C1234567890",
    # "random": "C0987654321",
}


def get_channel_id(channel_name):
    """
    Get channel ID from config.

    Args:
        channel_name: Channel name (with or without #)

    Returns:
        Channel ID or None if not found
    """
    channel_name = channel_name.lstrip("#").lower()
    return CHANNEL_IDS.get(channel_name)


def add_channel(channel_name, channel_id):
    """
    Add a new channel to the config file.

    Args:
        channel_name: Channel name
        channel_id: Channel ID
    """
    import os

    channel_name = channel_name.lstrip("#").lower()

    # Read current file
    config_file = os.path.join(os.path.dirname(__file__), "channel_config.py")
    with open(config_file, "r") as f:
        lines = f.readlines()

    # Find the CHANNEL_IDS dict and add new entry
    new_lines = []
    found_dict = False
    added = False

    for line in lines:
        if "CHANNEL_IDS = {" in line:
            found_dict = True
            new_lines.append(line)
        elif found_dict and not added and "}" in line:
            # Add new entry before closing brace
            new_lines.append(f'    "{channel_name}": "{channel_id}",\n')
            new_lines.append(line)
            added = True
        else:
            new_lines.append(line)

    # Write back
    with open(config_file, "w") as f:
        f.writelines(new_lines)

    print(f"Added {channel_name} -> {channel_id} to channel_config.py")
