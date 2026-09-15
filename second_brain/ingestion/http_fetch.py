from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx

from second_brain.ingestion.safety import inspect_source_uri
from second_brain.schemas import Source, SourceStatus

_ALLOWED_CONTENT_TYPES = {
    "application/json",
    "application/pdf",
    "application/epub+zip",
    "application/xml",
    "application/rss+xml",
    "application/atom+xml",
    "text/html",
    "text/plain",
    "text/csv",
    "text/xml",
}


@dataclass(frozen=True)
class FetchedResource:
    url: str
    content: bytes
    content_type: str
    etag: str | None
    last_modified: str | None


class SafeHttpFetcher:
    """Bounded network fetcher for explicitly approved public sources.

    Environment proxies and redirects are disabled. Hostname DNS is checked for global
    addresses before the request. Network-level egress policy is still recommended in
    production to eliminate DNS-rebinding TOCTOU risk completely.
    """

    def __init__(
        self,
        *,
        timeout_seconds: float = 12.0,
        max_bytes: int = 5 * 1024 * 1024,
    ) -> None:
        if timeout_seconds <= 0 or timeout_seconds > 120:
            raise ValueError("timeout_seconds must be within (0, 120]")
        if max_bytes < 1024 or max_bytes > 100 * 1024 * 1024:
            raise ValueError("max_bytes must be between 1 KiB and 100 MiB")
        self.timeout_seconds = timeout_seconds
        self.max_bytes = max_bytes

    def fetch(self, source: Source, url: str | None = None) -> FetchedResource:
        if source.status != SourceStatus.APPROVED or not source.approved_for_automated_fetch:
            raise PermissionError("source is not approved for automated fetch")
        if not source.canonical_uri:
            raise ValueError("automated source requires canonical_uri")

        target = url or source.canonical_uri
        self._validate_target(source, target)
        headers = {
            "Accept": ", ".join(sorted(_ALLOWED_CONTENT_TYPES)),
            "User-Agent": "SecondBrainFetcher/1.0 (+governed institutional research)",
        }
        timeout = httpx.Timeout(self.timeout_seconds)
        with httpx.Client(
            timeout=timeout,
            follow_redirects=False,
            trust_env=False,
            headers=headers,
        ) as client:
            with client.stream("GET", target) as response:
                if 300 <= response.status_code < 400:
                    raise ValueError("redirects are disabled; approve the final canonical host explicitly")
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                if content_type not in _ALLOWED_CONTENT_TYPES:
                    raise ValueError(f"content type is not approved for automated fetch: {content_type}")
                declared = response.headers.get("content-length")
                if declared:
                    try:
                        declared_size = int(declared)
                    except ValueError:
                        declared_size = -1
                    if declared_size > self.max_bytes:
                        raise ValueError("declared response size exceeds configured maximum")
                chunks: list[bytes] = []
                total = 0
                for chunk in response.iter_bytes():
                    total += len(chunk)
                    if total > self.max_bytes:
                        raise ValueError("streamed response exceeds configured maximum")
                    chunks.append(chunk)
                return FetchedResource(
                    url=str(response.url),
                    content=b"".join(chunks),
                    content_type=content_type,
                    etag=response.headers.get("etag"),
                    last_modified=response.headers.get("last-modified"),
                )

    def _validate_target(self, source: Source, target: str) -> None:
        findings = inspect_source_uri(target)
        blocking = [item for item in findings if item.severity in {"HIGH", "CRITICAL"}]
        if blocking:
            raise ValueError(
                "unsafe source URI: " + ", ".join(sorted(item.code for item in blocking))
            )
        canonical = urlsplit(source.canonical_uri or "")
        parts = urlsplit(target)
        if parts.scheme.lower() != "https":
            raise ValueError("automated external fetch requires HTTPS")
        if not canonical.hostname or not parts.hostname:
            raise ValueError("source and target hosts are required")
        allowed_hosts = {canonical.hostname.casefold()}
        configured = source.metadata.get("allowed_hosts")
        if isinstance(configured, list):
            allowed_hosts.update(
                str(item).casefold() for item in configured if isinstance(item, str) and item
            )
        target_host = parts.hostname.casefold()
        if target_host not in allowed_hosts:
            raise ValueError(f"target host is not explicitly approved: {target_host}")
        _assert_public_dns(target_host, parts.port or 443)


def _assert_public_dns(hostname: str, port: int) -> None:
    try:
        answers = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError(f"source hostname cannot be resolved: {hostname}") from exc
    addresses = {answer[4][0] for answer in answers if answer and answer[4]}
    if not addresses:
        raise ValueError(f"source hostname has no resolved addresses: {hostname}")
    for raw in addresses:
        try:
            address = ipaddress.ip_address(raw)
        except ValueError as exc:
            raise ValueError(f"invalid DNS address returned for {hostname}: {raw}") from exc
        if not address.is_global:
            raise ValueError(f"source hostname resolves to non-global address: {raw}")
