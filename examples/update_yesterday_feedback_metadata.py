"""
Example: Fetch feedbacks from a given date and add a metadata entry.

The metadata field follows the structure:
  [{"key": "some-key", "value": ["string-value"]}, ...]
"""

import os
import random
from datetime import date, timedelta, timezone, datetime

from dotenv import load_dotenv
from magicfeedback_sdk import MagicFeedback

load_dotenv()

# ── Configuration ──────────────────────────────────────────────────────────────
EMAIL = os.environ["MF_EMAIL"]
PASSWORD = os.environ["MF_PASSWORD"]
# ──────────────────────────────────────────────────────────────────────────────


def date_range(days_ago: int = 1):
    today = date.today()
    start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc) - timedelta(days=days_ago)
    end = start + timedelta(days=1) - timedelta(microseconds=1)
    return start.isoformat().replace("+00:00", "Z"), end.isoformat().replace("+00:00", "Z")


def main():
    client = MagicFeedback(EMAIL, PASSWORD)

    # Change days_ago=2 for testing; switch back to 1 for production
    start, end = date_range(days_ago=2)
    print(f"Fetching feedbacks from {start} to {end}")

    feedbacks = client.feedbacks.get(
        filter={
            "where": {
                "createdAt": {"between": [start, end]}
            }
        }
    )

    if not feedbacks:
        print("No feedbacks found for that date.")
        return

    print(f"Found {len(feedbacks)} feedback(s). Updating metadata...\n")

    for fb in feedbacks:
        feedback_id = fb["id"]
        existing_metadata = list(fb.get("metadata") or [])

        # Keep one "Test" entry with the new value, remove any duplicates
        new_value = [str(random.randint(0, 100))]
        updated_metadata = [m for m in existing_metadata if m.get("key") != "Test"]
        updated_metadata.append({"key": "Test", "value": new_value})

        result = client.feedbacks.update(feedback_id, {"metadata": updated_metadata, "status": "REGISTERED"})
        print(f"  [{feedback_id}] metadata 'Test' added → {new_entry['value']}")


if __name__ == "__main__":
    main()
