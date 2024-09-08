import json
from typing import Any, Dict, Optional

import requests
from google.auth.transport.requests import Request


class MagicFeedbackClient:
    """A Python SDK for interacting with the MagicFeedback API."""

    def __init__(self, user: str, password: str, base_url: str = "https://api.magicfeedback.io", ip_key: str = 'AIzaSyAKcR895VURSQZSN2T_RD6jX_9y5HRmH80'):

        self.base_url = base_url
        self.ip_key = ip_key

        self.api_key = self.get_api_key(user, password)
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    def get_api_key(self, user, password):
        """Obtains the API key using user and password authentication."""
        # TODO: Implement control to check if the token is still valid - Only for 1 hour
        # Call your existing function
        id_token = self.identity_login(user, password)
        return id_token

    def identity_login(self, user, password):
        """
        (Replace this function with your existing `identity_login` function)

        Performs user and password-based login using the identity toolkit API.

        Returns:
            str: The obtained ID token.
        """
        # TODO: Control in case the call is not good
        print("Logging in with user and password...")
        print("User: ", user)
        print("Password: ", password)

        options = {
            "method": "POST",
            "url": "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=" + self.ip_key,
            "headers": {
                "Content-Type": "application/javascript",
            },
            "data": json.dumps({
                "email": user,
                "password": password,
                "returnSecureToken": True
            })
        }

        response = requests.post(
            options["url"], headers=options["headers"], data=options["data"])
        data = json.loads(response.text)
        return data["idToken"]

    def _make_request(
        self, method: str, url: str, json: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Makes a request to the MagicFeedback API."""
        # TODO: Control token expiration
        response = requests.request(
            method, url, headers=self.headers, json=json)
        response.raise_for_status()  # Raise exception for non-2xx status codes
        # TODO: Control the status of the call 
        print("Status code: ", response.status_code)
        print("Response: ", response.json())

        return response.json()

    ####################################################################################
    # Feedback API Methods                                                             #
    ####################################################################################

    def create_feedback(self, feedback: Dict[str, Any]) -> Dict[str, Any]:
        """Creates a new feedback item.

        Args:
            feedback (Dict[str, Any]): The feedback data to create.

        Returns:
            Dict[str, Any]: The created feedback item.
        """
        url = f"{self.base_url}/feedbacks"

        # Ensure required fields are present
        required_fields = [
            "name", "type", "identity",
            "integrationId", "companyId",
            "productId"
        ]
        for field in required_fields:
            if field not in feedback:
                raise ValueError(f"Missing required field: {field}")

        return self._make_request("POST", url, json=feedback)

    # Add other API methods as needed
    def get_feedback(self, feedback_id: str) -> Dict[str, Any]:
        """Retrieves a specific feedback item.

        Args:
            feedback_id (str): The ID of the feedback item.

        Returns:
            Dict[str, Any]: The retrieved feedback item.
        """
        url = f"{self.base_url}/feedbacks/{feedback_id}"
        return self._make_request("GET", url)

    def update_feedback(self, feedback_id: str, feedback: Dict[str, Any]) -> Dict[str, Any]:
        """Updates a specific feedback item.

        Args:
            feedback_id (str): The ID of the feedback item.
            feedback (Dict[str, Any]): The updated feedback data.

        Returns:
            Dict[str, Any]: The updated feedback item.
        """
        url = f"{self.base_url}/feedbacks/{feedback_id}"
        return self._make_request("PUT", url, json=feedback)

    def delete_feedback(self, feedback_id: str) -> None:
        """Deletes a specific feedback item.

        Args:
            feedback_id (str): The ID of the feedback item.
        """
        url = f"{self.base_url}/feedbacks/{feedback_id}"
        self._make_request("DELETE", url)
