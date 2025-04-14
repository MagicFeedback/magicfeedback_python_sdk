import json

import requests


class AuthManager:
    def __init__(self, ip_key: str, logger):
        self.ip_key = ip_key
        self.logger = logger

    def get_api_key(self, user, password):
        return self.identity_login(user, password)

    def identity_login(self, user, password):
        self.logger.info("Logging in with user: %s", user)

        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={self.ip_key}"
        headers = {"Content-Type": "application/json"}
        payload = json.dumps({
            "email": user,
            "password": password,
            "returnSecureToken": True
        })

        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status()
        data = response.json()
        return data["idToken"]
