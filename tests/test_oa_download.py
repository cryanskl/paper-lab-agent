import asyncio

import httpx
import pytest

from app.services import oa_download
from app.services.oa_download import OADownloadError, download_oa_pdf, validate_public_oa_url


def allow_public_dns(monkeypatch):
    async def resolve_public(_hostname: str, _port: int) -> list[str]:
        return ["8.8.8.8"]

    monkeypatch.setattr(oa_download, "resolve_host_addresses", resolve_public)


def test_download_oa_pdf_accepts_public_pdf(monkeypatch):
    allow_public_dns(monkeypatch)
    payload = b"%PDF-1.7\nopen access paper"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["accept"].startswith("application/pdf")
        return httpx.Response(200, headers={"content-type": "application/pdf"}, content=payload)

    downloaded = asyncio.run(
        download_oa_pdf(
            "https://oa.example.org/paper.pdf",
            transport=httpx.MockTransport(handler),
        )
    )

    assert downloaded.content == payload
    assert downloaded.final_url == "https://oa.example.org/paper.pdf"


def test_validate_public_oa_url_rejects_private_ip():
    with pytest.raises(OADownloadError) as caught:
        asyncio.run(validate_public_oa_url("http://127.0.0.1/private.pdf"))

    assert caught.value.status_code == 409
    assert caught.value.code == "oa_pdf_url_blocked"


def test_download_oa_pdf_revalidates_redirect_target(monkeypatch):
    async def resolve_by_host(hostname: str, _port: int) -> list[str]:
        return ["127.0.0.1"] if hostname == "127.0.0.1" else ["8.8.8.8"]

    monkeypatch.setattr(oa_download, "resolve_host_addresses", resolve_by_host)

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "http://127.0.0.1/private.pdf"})

    with pytest.raises(OADownloadError) as caught:
        asyncio.run(
            download_oa_pdf(
                "https://oa.example.org/redirect",
                transport=httpx.MockTransport(handler),
            )
        )

    assert caught.value.code == "oa_pdf_url_blocked"


def test_download_oa_pdf_rejects_html_response(monkeypatch):
    allow_public_dns(monkeypatch)

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "text/html"}, content=b"<html>login</html>")

    with pytest.raises(OADownloadError) as caught:
        asyncio.run(
            download_oa_pdf(
                "https://oa.example.org/login",
                transport=httpx.MockTransport(handler),
            )
        )

    assert caught.value.status_code == 415
    assert caught.value.code == "oa_pdf_not_pdf"


def test_download_oa_pdf_rejects_oversized_response(monkeypatch):
    allow_public_dns(monkeypatch)

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/pdf", "content-length": "11"},
            content=b"%PDF-large",
        )

    with pytest.raises(OADownloadError) as caught:
        asyncio.run(
            download_oa_pdf(
                "https://oa.example.org/large.pdf",
                transport=httpx.MockTransport(handler),
                max_bytes=10,
            )
        )

    assert caught.value.status_code == 413
    assert caught.value.code == "oa_pdf_too_large"


def test_download_oa_pdf_rejects_invalid_pdf_signature(monkeypatch):
    allow_public_dns(monkeypatch)

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "application/pdf"}, content=b"not a pdf")

    with pytest.raises(OADownloadError) as caught:
        asyncio.run(
            download_oa_pdf(
                "https://oa.example.org/not-pdf",
                transport=httpx.MockTransport(handler),
            )
        )

    assert caught.value.status_code == 415
    assert caught.value.code == "oa_pdf_invalid"
