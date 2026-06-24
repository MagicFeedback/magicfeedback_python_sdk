"""
Example: Fetch yesterday's feedbacks and update their metrics.

Steps:
  1. Connect to MagicFeedback with your credentials.
  2. Build a LoopBack filter for yesterday's date range.
  3. Fetch all feedbacks created yesterday (including their metrics relation).
  4. For each feedback, modify the metrics values you need.
  5. Push the update back with feedbacks.update().
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
    """Return (start_iso, end_iso) for a day N days ago in UTC."""
    today = date.today()
    start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc) - timedelta(days=days_ago)
    end = start + timedelta(days=1) - timedelta(microseconds=1)
    return start.isoformat().replace("+00:00", "Z"), end.isoformat().replace("+00:00", "Z")


def main():
    client = MagicFeedback(EMAIL, PASSWORD)

    start, end = date_range(days_ago=1)
    print(f"Fetching feedbacks from {start} to {end}")

    feedbacks = client.feedbacks.get(
        filter={
            "where": {
                "createdAt": {"between": [start, end]}            }
        }
    )

    if not feedbacks:
        print("No feedbacks found for that date.")
        return

    print(f"Found {len(feedbacks)} feedback(s). Updating metrics...\n")

    for fb in feedbacks:
        feedback_id = fb["id"]
        existing_metrics = list(fb.get("metrics") or [])

        # Keep one "Test" entry with the new value, remove any duplicates
        new_value = random.randint(0, 100)
        updated_metrics = [m for m in existing_metrics if m.get("key") != "Test"]
        updated_metrics.append({"key": "Test", "value": new_value})

        result = client.feedbacks.update(feedback_id, {"metrics": updated_metrics, "status": "REGISTERED"})
        print(f"  [{feedback_id}] metrics updated → {updated_metrics}")



if __name__ == "__main__":
    main()
