"""
Utility functions for parsing times and splitting event strings.

Provides:
    parse_time: Convert a time string (H:MM:SS, MM:SS, or decimal)
        to numeric seconds.
    split_event: Split an event string like '50m Freestyle' into
        distance and style.
"""

import pandas as pd
import re


def parse_time(t):
    """
    Convert a time string to a float of total seconds.

    Accepts:
        - "H:MM:SS"
        - "MM:SS"
        - Decimal number (e.g. "2.5")
        - Strips trailing 'M' if present

    Args:
        t (str): Time string.

    Returns:
        float: The total time in seconds.
    """
    t = t.strip().rstrip("M")
    parts = t.split(":")
    if len(parts) == 3:
        # Format: hours:minutes:seconds
        hours, minutes, seconds = parts
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    elif len(parts) == 2:
        # Format: minutes:seconds
        minutes, seconds = parts
        return int(minutes) * 60 + float(seconds)
    else:
        # Otherwise, assume decimal
        return float(t)


def split_event(event):
    """
    Split an event string (e.g. '100m Butterfly') into distance and style.

    Args:
        event (str): An event descriptor.

    Returns:
        pandas.Series: A series with keys 'distance' (int or None)
        and 'style' (str or None).
    """
    event = event.strip()
    match = re.match(r"(\d+)m\s*(.*)", event)
    if match:
        distance = int(match.group(1))
        style = match.group(2).strip()
        return pd.Series({"distance": int(distance), "style": style})
    else:
        return pd.Series({"distance": None, "style": None})
