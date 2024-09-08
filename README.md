# MagicFeedback SDK

**A Python SDK for interacting with the MagicFeedback API**

**Installation**

Bash

```
pip install MagicFeeedback

```

Use code [with caution.](/faq#coding)

**Usage**

Python

```
from your_package import MagicFeedbackClient

# Create a MagicFeedbackClient instance
client = MagicFeedbackClient('email', 'password')

# Create a new feedback item
feedback_data = {
    "name": "Test Feedback",
    "type": "DOCUMENT",
    # ... other required fields
}
response = client.create_feedback(feedback_data)

# Print the response
print(response)

```

**API Reference**

- **`create_feedback(feedback)`:** Creates a new feedback item.
- **`get_feedback(feedback_id)`:** Retrieves a specific feedback item.
- **`update_feedback(feedback_id, feedback)`:** Updates a specific feedback item.
- **`delete_feedback(feedback_id)`:** Deletes a specific feedback item.

**Additional Information**

- **Authentication:** The SDK requires an user / password for authentication. You can obtain from the MagicFeedback platform.
- **Error Handling:** The SDK handles common API errors and raises appropriate exceptions.
- **Customizations:** You can customize the SDK to fit your specific needs by extending the `MagicFeedbackClient` class or creating additional helper functions.

**License**

This project is licensed under the MIT License.

**Contact**

For any questions or support, please contact farias@magicfeedback.io.
