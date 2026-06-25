from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Optional

import httpx


def retry_after_delay(response: httpx.Response) -> Optional[float]:
    retry_after = response.headers.get("Retry-After")
    if not retry_after:
        return None
    retry_after = retry_after.strip()
    if not retry_after:
        return None
    try:
        return max(float(retry_after), 0.0)
    except ValueError:
        return retry_after_http_date_delay(retry_after, response)


def retry_after_http_date_delay(value: str, response: httpx.Response) -> Optional[float]:
    retry_at = parse_http_date(value)
    if retry_at is None:
        return None
    reference = parse_http_date(response.headers.get("Date")) or datetime.now(timezone.utc)
    return max((retry_at - reference).total_seconds(), 0.0)


def parse_http_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError, OverflowError):
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
