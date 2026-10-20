"""
Example: mark a Request DONE by publishing to the `request-done` Pub/Sub topic.

The SDK no longer publishes this message — the producer (e.g. a notebook or a
worker) owns the publish. The SDK only ships `build_done_message`, the canonical
envelope builder, so producers and the consuming Cloud Function stay in sync.

Flow:
  1. Something creates a Request (e.g. POST /requests) -> status PENDING.
  2. A worker / this script does the actual work.
  3. When finished, publish a completion event to the `request-done` topic.
  4. The request-done Cloud Function (deployed in magicfeedback-prod-api via
     deploy-api.yml) consumes it and PATCHes /requests/{id} to DONE (or ERROR).

Requirements:
  - pip install google-cloud-pubsub
  - Application Default Credentials with publish rights on the topic, e.g.
    `gcloud auth application-default login` or GOOGLE_APPLICATION_CREDENTIALS
    pointing at a service-account key.

Project/topic:
  - PROD: project "magicfeedback-prod-api", topic "request-done"
  - DEV:  project "magicfeedback-dev-api",  topic "request-done"
"""

import json
import os

from google.cloud import pubsub_v1

from magicfeedback_sdk.api.requests import build_done_message

# ── Configuration ──────────────────────────────────────────────────────────────
PROJECT_ID = os.environ.get("MF_PUBSUB_PROJECT", "magicfeedback-prod-api")
TOPIC = os.environ.get("MF_REQUEST_DONE_TOPIC", "request-done")
REQUEST_ID = os.environ["MF_REQUEST_ID"]
COMPANY_ID = os.environ["MF_COMPANY_ID"]
# ──────────────────────────────────────────────────────────────────────────────


def main():
    # Build the completion envelope the request-done CF expects.
    message = build_done_message(
        REQUEST_ID,
        COMPANY_ID,
        output={"value": "…final result…"},
        sources=["<feedbackId1>", "<feedbackId2>"],  # optional
        logs="processed 2 items",                    # optional
    )

    # Publish it to the request-done topic ourselves.
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(PROJECT_ID, TOPIC)
    data = json.dumps(message).encode("utf-8")
    future = publisher.publish(topic_path, data)
    message_id = future.result()

    print(f"Published request-done to {topic_path} (messageId={message_id})")

    # The request should transition to DONE shortly. You can poll it with the SDK:
    #   from magicfeedback_sdk import MagicFeedback
    #   client = MagicFeedback(EMAIL, PASSWORD)
    #   client.requests.get_id(REQUEST_ID)  -> {"status": "DONE", "output": {...}}


if __name__ == "__main__":
    main()
