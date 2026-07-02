"""Thin Google API client used by Gmail and Sheets adapters."""

from __future__ import annotations

import base64
import time
from email.message import EmailMessage as MimeEmailMessage
from typing import Any, cast

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from ticket_processor.config import Settings
from ticket_processor.domain.exceptions import AuthenticationError, ExternalServiceError


class GogClient:
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    GMAIL_BASE = "https://gmail.googleapis.com/gmail/v1"
    SHEETS_BASE = "https://sheets.googleapis.com/v4"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._session = requests.Session()
        self._access_token: str | None = None
        self._token_expires_at = 0.0

    def _refresh_access_token(self) -> str:
        response = self._session.post(
            self.TOKEN_URL,
            data={
                "client_id": self._settings.gmail_client_id,
                "client_secret": self._settings.gmail_client_secret.get_secret_value(),
                "refresh_token": self._settings.gmail_refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=30,
        )
        if response.status_code != 200:
            raise AuthenticationError(
                f"Failed to refresh Google access token: {response.status_code}",
                context={"response": response.text[:500]},
            )
        payload = response.json()
        self._access_token = str(payload["access_token"])
        self._token_expires_at = time.time() + int(payload.get("expires_in", 3600)) - 60
        return self._access_token

    def _auth_headers(self) -> dict[str, str]:
        token = self._access_token
        if token is None or time.time() >= self._token_expires_at:
            token = self._refresh_access_token()
        return {"Authorization": f"Bearer {token}"}

    @retry(
        wait=wait_exponential_jitter(initial=1, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type((requests.RequestException, ExternalServiceError)),
    )
    def search_messages(self, query: str, max_results: int = 20) -> list[dict[str, Any]]:
        response = self._session.get(
            f"{self.GMAIL_BASE}/users/{self._settings.gmail_account}/messages",
            headers=self._auth_headers(),
            params={"q": query, "maxResults": str(max_results)},
            timeout=30,
        )
        self._raise_if_needed(response, "search_messages")
        payload = cast(dict[str, Any], response.json())
        return cast(list[dict[str, Any]], payload.get("messages", []))

    def get_message(self, message_id: str) -> dict[str, Any]:
        response = self._session.get(
            f"{self.GMAIL_BASE}/users/{self._settings.gmail_account}/messages/{message_id}",
            headers=self._auth_headers(),
            params={"format": "full"},
            timeout=30,
        )
        self._raise_if_needed(response, "get_message")
        return cast(dict[str, Any], response.json())

    def get_attachment(self, message_id: str, attachment_id: str) -> bytes:
        response = self._session.get(
            (
                f"{self.GMAIL_BASE}/users/{self._settings.gmail_account}/messages/"
                f"{message_id}/attachments/{attachment_id}"
            ),
            headers=self._auth_headers(),
            timeout=60,
        )
        self._raise_if_needed(response, "get_attachment")
        payload = response.json()
        return base64.urlsafe_b64decode(payload["data"])

    def add_label(self, message_id: str, label_name: str) -> None:
        label_id = self._get_or_create_label(label_name)
        response = self._session.post(
            f"{self.GMAIL_BASE}/users/{self._settings.gmail_account}/messages/{message_id}/modify",
            headers=self._auth_headers(),
            json={"addLabelIds": [label_id]},
            timeout=30,
        )
        self._raise_if_needed(response, "add_label")

    def send_reply(
        self,
        *,
        to: str,
        subject: str,
        thread_id: str,
        in_reply_to: str,
        body: str,
    ) -> None:
        message = MimeEmailMessage()
        message["To"] = to
        message["From"] = self._settings.gmail_account
        message["Subject"] = subject
        message["In-Reply-To"] = in_reply_to
        message["References"] = in_reply_to
        message.set_content(body)

        encoded = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        response = self._session.post(
            f"{self.GMAIL_BASE}/users/{self._settings.gmail_account}/messages/send",
            headers=self._auth_headers(),
            json={"raw": encoded, "threadId": thread_id},
            timeout=30,
        )
        self._raise_if_needed(response, "send_reply")

    def sheets_append(self, sheet_id: str, range_name: str, values: list[list[Any]]) -> None:
        response = self._session.post(
            f"{self.SHEETS_BASE}/spreadsheets/{sheet_id}/values/{range_name}:append",
            headers=self._auth_headers(),
            params={"valueInputOption": "USER_ENTERED", "insertDataOption": "INSERT_ROWS"},
            json={"values": values},
            timeout=30,
        )
        self._raise_if_needed(response, "sheets_append")

    def sheets_get(self, sheet_id: str, range_name: str) -> list[list[str]]:
        response = self._session.get(
            f"{self.SHEETS_BASE}/spreadsheets/{sheet_id}/values/{range_name}",
            headers=self._auth_headers(),
            timeout=30,
        )
        self._raise_if_needed(response, "sheets_get")
        payload = cast(dict[str, Any], response.json())
        return cast(list[list[str]], payload.get("values", []))

    def _get_or_create_label(self, label_name: str) -> str:
        response = self._session.get(
            f"{self.GMAIL_BASE}/users/{self._settings.gmail_account}/labels",
            headers=self._auth_headers(),
            timeout=30,
        )
        self._raise_if_needed(response, "list_labels")
        for label in response.json().get("labels", []):
            if label.get("name") == label_name:
                return str(label["id"])

        response = self._session.post(
            f"{self.GMAIL_BASE}/users/{self._settings.gmail_account}/labels",
            headers=self._auth_headers(),
            json={
                "name": label_name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            },
            timeout=30,
        )
        self._raise_if_needed(response, "create_label")
        return str(response.json()["id"])

    @staticmethod
    def _raise_if_needed(response: requests.Response, operation: str) -> None:
        if 200 <= response.status_code < 300:
            return
        if response.status_code == 401:
            raise AuthenticationError(
                f"{operation} unauthorized",
                context={"status_code": response.status_code, "body": response.text[:500]},
            )
        raise ExternalServiceError(
            f"{operation} failed",
            context={"status_code": response.status_code, "body": response.text[:500]},
        )
