from __future__ import annotations

import ipaddress
import socket
import time
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

import httpx

from app.models.knowledge_source import KnowledgeSource, SourceAccessMode, SourceStatus
from app.services.information_security import validate_public_source_uri

MAX_SOURCE_BYTES = 5 * 1024 * 1024
SOURCE_TIMEOUT_SECONDS = 12.0
ALLOWED_CONTENT_TYPES = {
    "application/json",
    "application/pdf",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/xml",
    "text/csv",
    "text/html",
    "text/plain",
    "text/xml",
}


@dataclass(frozen=True)
class FetchResult:
    status_code: int
    content_type: str | None
    content: bytes
    elapsed_ms: int
    final_url: str


def _assert_public_host(hostname: str) -> None:
    try:
        addresses = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError("source hostname cannot be resolved") from exc
    if not addresses:
        raise ValueError("source hostname did not resolve to an address")

    for address in addresses:
        raw_ip = address[4][0]
        try:
            ip = ipaddress.ip_address(raw_ip)
        except ValueError as exc:
            raise ValueError("source resolved to an invalid address") from exc
        if not ip.is_global:
            raise ValueError("source resolved to a non-public network address")


def _host_allowed(source: KnowledgeSource, url: str) -> None:
    base = urlsplit(source.base_uri)
    target = urlsplit(url)
    if target.scheme != "https":
        raise ValueError("automated source fetch requires https")
    if not base.hostname or not target.hostname:
        raise ValueError("source URL is missing a hostname")
    base_host = base.hostname.lower().rstrip(".")
    target_host = target.hostname.lower().rstrip(".")
    if target_host != base_host and not target_host.endswith(f".{base_host}"):
        raise ValueError("source fetch cannot leave the approved source domain")
    _assert_public_host(target_host)


def _validate_fetch_source(source: KnowledgeSource) -> None:
    validate_public_source_uri(source.base_uri)
    if source.status != SourceStatus.approved.value:
        raise ValueError("source is not approved")
    if not source.approved_for_fetch:
        raise ValueError("source is not approved for automated fetch")
    if source.access_mode != SourceAccessMode.public.value:
        raise ValueError("automated fetch is limited to public sources without credentials")
    _host_allowed(source, source.base_uri)


def fetch_source(
    source: KnowledgeSource,
    *,
    relative_or_absolute_url: str | None = None,
    transport: httpx.BaseTransport | None = None,
) -> FetchResult:
    _validate_fetch_source(source)
    target = urljoin(source.base_uri, relative_or_absolute_url or source.base_uri)
    validate_public_source_uri(target)
    _host_allowed(source, target)

    started = time.monotonic()
    with httpx.Client(
        timeout=SOURCE_TIMEOUT_SECONDS,
        follow_redirects=False,
        transport=transport,
        headers={"User-Agent": "second-brain-source-health/1.0"},
    ) as client:
        with client.stream("GET", target) as response:
            response.raise_for_status()
            content_type = response.headers.get("content-type")
            media_type = content_type.split(";", 1)[0].strip().lower() if content_type else None
            if media_type not in ALLOWED_CONTENT_TYPES:
                raise ValueError("source returned a disallowed content type")

            declared_length = response.headers.get("content-length")
            if declared_length:
                try:
                    if int(declared_length) > MAX_SOURCE_BYTES:
                        raise ValueError("source response exceeds maximum allowed size")
                except ValueError as exc:
                    if "exceeds" in str(exc):
                        raise

            chunks: list[bytes] = []
            size = 0
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > MAX_SOURCE_BYTES:
                    raise ValueError("source response exceeds maximum allowed size")
                chunks.append(chunk)

            elapsed_ms = max(0, int((time.monotonic() - started) * 1000))
            return FetchResult(
                status_code=response.status_code,
                content_type=media_type,
                content=b"".join(chunks),
                elapsed_ms=elapsed_ms,
                final_url=str(response.url),
            )
