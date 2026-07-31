from __future__ import annotations

import asyncio
import ipaddress
import socket
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin, urlsplit

import httpx


MAX_OA_PDF_BYTES = 100 * 1024 * 1024
MAX_OA_REDIRECTS = 3
PDF_MEDIA_TYPES = {
    "application/pdf",
    "application/x-pdf",
    "application/octet-stream",
    "application/force-download",
    "binary/octet-stream",
}
REDIRECT_STATUSES = {301, 302, 303, 307, 308}


@dataclass(frozen=True)
class OAPdfDownload:
    content: bytes
    final_url: str


class OADownloadError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


async def resolve_host_addresses(hostname: str, port: int) -> list[str]:
    try:
        records = await asyncio.to_thread(
            socket.getaddrinfo,
            hostname,
            port,
            type=socket.SOCK_STREAM,
        )
    except OSError as exc:
        raise OADownloadError(
            502,
            "oa_pdf_host_unreachable",
            "Open-access PDF host could not be resolved",
        ) from exc
    return list(dict.fromkeys(record[4][0] for record in records))


def is_public_address(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value.split("%", 1)[0])
    except ValueError:
        return False
    return address.is_global


async def validate_public_oa_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        raise OADownloadError(409, "oa_pdf_url_invalid", "Open-access PDF URL is invalid") from exc
    hostname = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme.lower() not in {"http", "https"} or not hostname:
        raise OADownloadError(409, "oa_pdf_url_invalid", "Open-access PDF URL must use HTTP(S)")
    if parsed.username is not None or parsed.password is not None:
        raise OADownloadError(409, "oa_pdf_url_blocked", "Open-access PDF URL must not contain credentials")
    if (
        hostname == "localhost"
        or hostname.endswith(".localhost")
        or hostname.endswith(".local")
        or hostname == "example.test"
        or hostname.endswith(".example.test")
    ):
        raise OADownloadError(409, "oa_pdf_url_blocked", "Open-access PDF URL is not a public download host")
    addresses = await resolve_host_addresses(
        hostname,
        port or (443 if parsed.scheme.lower() == "https" else 80),
    )
    if not addresses or any(not is_public_address(address) for address in addresses):
        raise OADownloadError(409, "oa_pdf_url_blocked", "Open-access PDF URL resolved to a non-public address")
    return parsed.geturl()


async def download_oa_pdf(
    url: str,
    *,
    transport: Any = None,
    user_agent: str = "paper-lab-agent/0.1",
    timeout_seconds: float = 30.0,
    max_bytes: int = MAX_OA_PDF_BYTES,
    max_redirects: int = MAX_OA_REDIRECTS,
) -> OAPdfDownload:
    current_url = str(url or "").strip()
    if not current_url:
        raise OADownloadError(409, "oa_pdf_unavailable", "Paper has no open-access PDF URL")
    safe_user_agent = str(user_agent or "").replace("\r", " ").replace("\n", " ").strip()[:512]
    headers = {
        "Accept": "application/pdf,application/octet-stream;q=0.9",
        "User-Agent": safe_user_agent or "paper-lab-agent/0.1",
    }
    try:
        async with httpx.AsyncClient(
            follow_redirects=False,
            timeout=timeout_seconds,
            transport=transport,
            trust_env=False,
        ) as client:
            for redirect_index in range(max_redirects + 1):
                current_url = await validate_public_oa_url(current_url)
                async with client.stream("GET", current_url, headers=headers) as response:
                    if response.status_code in REDIRECT_STATUSES:
                        location = response.headers.get("location")
                        if not location:
                            raise OADownloadError(
                                502,
                                "oa_pdf_redirect_invalid",
                                "Open-access PDF source returned a redirect without a location",
                            )
                        if redirect_index >= max_redirects:
                            raise OADownloadError(
                                502,
                                "oa_pdf_redirect_limit",
                                "Open-access PDF source exceeded the redirect limit",
                            )
                        current_url = urljoin(current_url, location)
                        continue
                    if response.status_code in {401, 403}:
                        raise OADownloadError(
                            409,
                            "oa_pdf_access_denied",
                            "Open-access PDF source requires authorization",
                        )
                    if response.status_code != 200:
                        raise OADownloadError(
                            502,
                            "oa_pdf_fetch_failed",
                            f"Open-access PDF source returned HTTP {response.status_code}",
                        )
                    content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                    if content_type and content_type not in PDF_MEDIA_TYPES:
                        raise OADownloadError(
                            415,
                            "oa_pdf_not_pdf",
                            f"Open-access source returned {content_type} instead of PDF",
                        )
                    content_length = response.headers.get("content-length")
                    if content_length:
                        try:
                            declared_size = int(content_length)
                        except ValueError:
                            declared_size = 0
                        if declared_size > max_bytes:
                            raise OADownloadError(
                                413,
                                "oa_pdf_too_large",
                                "Open-access PDF exceeds the 100 MiB download limit",
                            )
                    content = bytearray()
                    async for chunk in response.aiter_bytes():
                        content.extend(chunk)
                        if len(content) > max_bytes:
                            raise OADownloadError(
                                413,
                                "oa_pdf_too_large",
                                "Open-access PDF exceeds the 100 MiB download limit",
                            )
                    payload = bytes(content)
                    if b"%PDF-" not in payload[:1024]:
                        raise OADownloadError(
                            415,
                            "oa_pdf_invalid",
                            "Open-access source did not return a valid PDF file",
                        )
                    return OAPdfDownload(content=payload, final_url=current_url)
    except OADownloadError:
        raise
    except httpx.TimeoutException as exc:
        raise OADownloadError(504, "oa_pdf_timeout", "Open-access PDF download timed out") from exc
    except httpx.HTTPError as exc:
        raise OADownloadError(502, "oa_pdf_fetch_failed", "Open-access PDF download failed") from exc
    raise OADownloadError(502, "oa_pdf_fetch_failed", "Open-access PDF download failed")
