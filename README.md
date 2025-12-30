# Vanish Email Client for Python

A lightweight, zero-dependency Python client for the [Vanish](https://github.com/coldpatch/vanish) temporary email service API.

## Requirements

- Python 3.10+

## Installation

Copy `vanish.py` into your project, or install from source:

```bash
pip install .
```

## Quick Start

```python
from vanish import VanishClient

# Create client (with optional API key)
client = VanishClient("https://api.vanish.host", api_key="your-key")

# Generate a temporary email address
email = client.generate_email()
print(f"Your temp email: {email}")

# Or with options
email = client.generate_email(domain="vanish.host", prefix="mytest")

# List emails in the mailbox
result = client.list_emails(email, limit=20)
print(f"Total emails: {result.total}")

for email_summary in result.data:
    print(f"  - {email_summary.subject} from {email_summary.sender}")

# Get full email details
if result.data:
    detail = client.get_email(result.data[0].id)
    print(f"HTML: {detail.html}")
    print(f"Text: {detail.text}")

    # Download attachments
    for att in detail.attachments:
        content, headers = client.get_attachment(detail.id, att.id)
        with open(att.name, "wb") as f:
            f.write(content)
```

## Polling for New Emails

Wait for an email to arrive with the built-in polling utility:

```python
# Wait up to 60 seconds for a new email
new_email = client.poll_for_emails(
    address=email,
    timeout=60,      # seconds
    interval=5,      # check every 5 seconds
    initial_count=0  # compare against this count
)

if new_email:
    print(f"New email received: {new_email.subject}")
else:
    print("No email received within timeout")
```

## API Reference

### `VanishClient(base_url, api_key=None, timeout=30)`

Create a new client instance.

| Parameter  | Type          | Description                              |
| ---------- | ------------- | ---------------------------------------- |
| `base_url` | `str`         | Base URL of the Vanish API               |
| `api_key`  | `str \| None` | Optional API key for authentication      |
| `timeout`  | `int`         | Request timeout in seconds (default: 30) |

### Methods

#### `get_domains() -> List[str]`

Returns list of available email domains.

#### `generate_email(domain=None, prefix=None) -> str`

Generate a unique temporary email address.

#### `list_emails(address, limit=20, cursor=None) -> PaginatedEmailList`

List emails for a mailbox with pagination support.

#### `get_email(email_id) -> EmailDetail`

Get full details of a specific email including attachments.

#### `get_attachment(email_id, attachment_id) -> tuple[bytes, dict]`

Download an attachment. Returns content bytes and headers.

#### `delete_email(email_id) -> bool`

Delete a specific email.

#### `delete_mailbox(address) -> int`

Delete all emails in a mailbox. Returns count of deleted emails.

#### `poll_for_emails(address, timeout=60, interval=5, initial_count=0) -> EmailSummary | None`

Poll for new emails until one arrives or timeout.

## Data Classes

### `EmailSummary`

```python
@dataclass
class EmailSummary:
    id: str
    sender: str
    subject: str
    text_preview: str
    received_at: datetime
    has_attachments: bool
```

### `EmailDetail`

```python
@dataclass
class EmailDetail:
    id: str
    sender: str
    to: List[str]
    subject: str
    html: str
    text: str
    received_at: datetime
    has_attachments: bool
    attachments: List[AttachmentMeta]
```

### `AttachmentMeta`

```python
@dataclass
class AttachmentMeta:
    id: str
    name: str
    type: str
    size: int
```

### `PaginatedEmailList`

```python
@dataclass
class PaginatedEmailList:
    data: List[EmailSummary]
    next_cursor: Optional[str]
    total: int
```

## Error Handling

```python
from vanish import VanishClient, VanishError

client = VanishClient("https://api.vanish.host")

try:
    email = client.get_email("invalid-id")
except VanishError as e:
    print(f"Error: {e}")
    print(f"Status code: {e.status_code}")
```

## License

MIT
