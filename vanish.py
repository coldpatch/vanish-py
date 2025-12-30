"""
Vanish Email API Client - Python Library
A simple, lightweight client for the Vanish temporary email service.
"""

import json
import urllib.request
import urllib.parse
import urllib.error
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime


@dataclass
class AttachmentMeta:
    """Metadata for an email attachment."""
    id: str
    name: str
    type: str
    size: int


@dataclass
class EmailSummary:
    """Summary of an email in the mailbox list."""
    id: str
    sender: str
    subject: str
    text_preview: str
    received_at: datetime
    has_attachments: bool


@dataclass
class EmailDetail:
    """Full email details with attachments."""
    id: str
    sender: str
    to: List[str]
    subject: str
    html: str
    text: str
    received_at: datetime
    has_attachments: bool
    attachments: List[AttachmentMeta]


@dataclass
class PaginatedEmailList:
    """Paginated list of emails."""
    data: List[EmailSummary]
    next_cursor: Optional[str]
    total: int


class VanishError(Exception):
    """Base exception for Vanish API errors."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class VanishClient:
    """
    Client for interacting with the Vanish Email API.
    
    Example:
        client = VanishClient("https://api.vanish.host", api_key="your-key")
        
        # Generate a temporary email
        email = client.generate_email()
        
        # List emails in the mailbox
        emails = client.list_emails(email)
        
        # Get a specific email
        detail = client.get_email(emails.data[0].id)
    """
    
    def __init__(self, base_url: str, api_key: Optional[str] = None, timeout: int = 30):
        """
        Initialize the Vanish client.
        
        Args:
            base_url: Base URL of the Vanish API (e.g., "https://api.vanish.host")
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
    
    def _request(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        body: Optional[dict] = None,
        raw_response: bool = False
    ):
        """Make an HTTP request to the API."""
        url = f"{self.base_url}{path}"
        
        if params:
            query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
            if query:
                url = f"{url}?{query}"
        
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        data = json.dumps(body).encode("utf-8") if body else None
        
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                if raw_response:
                    return resp.read(), resp.headers
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                error_body = json.loads(e.read().decode("utf-8"))
                message = error_body.get("error", str(e))
            except (json.JSONDecodeError, UnicodeDecodeError):
                message = str(e)
            raise VanishError(message, e.code) from e
        except urllib.error.URLError as e:
            raise VanishError(f"Connection error: {e.reason}") from e
    
    def get_domains(self) -> List[str]:
        """
        Get list of available email domains.
        
        Returns:
            List of domain strings
        """
        resp = self._request("GET", "/domains")
        return resp["domains"]
    
    def generate_email(
        self,
        domain: Optional[str] = None,
        prefix: Optional[str] = None
    ) -> str:
        """
        Generate a unique temporary email address.
        
        Args:
            domain: Optional specific domain to use
            prefix: Optional prefix for the email address
            
        Returns:
            Generated email address string
        """
        body = {}
        if domain:
            body["domain"] = domain
        if prefix:
            body["prefix"] = prefix
            
        resp = self._request("POST", "/mailbox", body=body if body else None)
        return resp["email"]
    
    def list_emails(
        self,
        address: str,
        limit: int = 20,
        cursor: Optional[str] = None
    ) -> PaginatedEmailList:
        """
        List emails for a mailbox address.
        
        Args:
            address: Email address to list emails for
            limit: Maximum number of emails to return (1-100)
            cursor: Pagination cursor for next page
            
        Returns:
            Paginated list of email summaries
        """
        encoded_address = urllib.parse.quote(address, safe="")
        resp = self._request(
            "GET",
            f"/mailbox/{encoded_address}",
            params={"limit": limit, "cursor": cursor}
        )
        
        emails = [
            EmailSummary(
                id=e["id"],
                sender=e["from"],
                subject=e["subject"],
                text_preview=e["textPreview"],
                received_at=datetime.fromisoformat(e["receivedAt"].replace("Z", "+00:00")),
                has_attachments=e["hasAttachments"]
            )
            for e in resp["data"]
        ]
        
        return PaginatedEmailList(
            data=emails,
            next_cursor=resp.get("nextCursor"),
            total=resp["total"]
        )
    
    def get_email(self, email_id: str) -> EmailDetail:
        """
        Get full details of a specific email.
        
        Args:
            email_id: UUID of the email
            
        Returns:
            Email details with attachments
        """
        resp = self._request("GET", f"/email/{email_id}")
        
        attachments = [
            AttachmentMeta(
                id=a["id"],
                name=a["name"],
                type=a["type"],
                size=a["size"]
            )
            for a in resp.get("attachments", [])
        ]
        
        return EmailDetail(
            id=resp["id"],
            sender=resp["from"],
            to=resp["to"],
            subject=resp["subject"],
            html=resp["html"],
            text=resp["text"],
            received_at=datetime.fromisoformat(resp["receivedAt"].replace("Z", "+00:00")),
            has_attachments=resp["hasAttachments"],
            attachments=attachments
        )
    
    def get_attachment(self, email_id: str, attachment_id: str) -> tuple[bytes, dict]:
        """
        Download an attachment.
        
        Args:
            email_id: UUID of the email
            attachment_id: UUID of the attachment
            
        Returns:
            Tuple of (content bytes, headers dict)
        """
        content, headers = self._request(
            "GET",
            f"/email/{email_id}/attachments/{attachment_id}",
            raw_response=True
        )
        return content, dict(headers)
    
    def delete_email(self, email_id: str) -> bool:
        """
        Delete a specific email.
        
        Args:
            email_id: UUID of the email to delete
            
        Returns:
            True if successful
        """
        resp = self._request("DELETE", f"/email/{email_id}")
        return resp.get("success", False)
    
    def delete_mailbox(self, address: str) -> int:
        """
        Delete all emails in a mailbox.
        
        Args:
            address: Email address to delete all emails for
            
        Returns:
            Number of emails deleted
        """
        encoded_address = urllib.parse.quote(address, safe="")
        resp = self._request("DELETE", f"/mailbox/{encoded_address}")
        return resp.get("deleted", 0)
    
    def poll_for_emails(
        self,
        address: str,
        timeout: int = 60,
        interval: int = 5,
        initial_count: int = 0
    ) -> Optional[EmailSummary]:
        """
        Poll for new emails until one arrives or timeout.
        
        Args:
            address: Email address to poll
            timeout: Maximum time to wait in seconds
            interval: Check interval in seconds
            initial_count: Initial email count to compare against
            
        Returns:
            First new email if found, None if timeout
        """
        import time
        start = time.time()
        
        while time.time() - start < timeout:
            result = self.list_emails(address, limit=1)
            if result.total > initial_count and result.data:
                return result.data[0]
            time.sleep(interval)
        
        return None


# Convenience function for quick usage
def create_client(base_url: str, api_key: Optional[str] = None) -> VanishClient:
    """Create a Vanish client with the given configuration."""
    return VanishClient(base_url, api_key)
