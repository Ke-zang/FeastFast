"""Single source of truth for in-memory data shared across pages.

Both the customer reservation flow and the admin reservation page import
BOOKINGS from here, so they always see the same list object regardless of
which entry-point file was run.
"""
import json
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bookings.json")

BOOKINGS = []


def load_bookings():
    """Load bookings from disk into BOOKINGS (idempotent)."""
    global BOOKINGS
    try:
        with open(DB_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, list):
            BOOKINGS[:] = data
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return BOOKINGS


def save_bookings():
    """Persist the current BOOKINGS list to disk."""
    try:
        with open(DB_PATH, "w", encoding="utf-8") as fh:
            json.dump(BOOKINGS, fh, indent=2)
    except OSError:
        pass


# Load once when the module is first imported.
load_bookings()