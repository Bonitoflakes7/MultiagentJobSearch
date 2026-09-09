"""Safe integration contracts and permitted source adapters."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
import re
import time
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from ..domain.jobs import JobInput, JobRecord, normalize_job


@dataclass(frozen=True)
class SourceItem:
    source_item_id: str
    source_name: str
    input: JobInput


class JobSourceAdapter(Protocol):
    source_name: str

    def fetch(self) -> tuple[SourceItem, ...]:
        """Return permitted source data without changing application state."""


@dataclass(frozen=True)
class SourcePolicy:
    """Network guardrails required by every live adapter."""

    allowed_hosts: tuple[str, ...]
    timeout_seconds: float = 8.0
    max_attempts: int = 2
    max_bytes: int = 1_000_000
    max_items: int = 25
    user_agent: str = "JobSearchIntelligence/0.1 (permitted-source-reader)"
    terms_reviewed: bool = False

    def validate(self) -> None:
        if not self.allowed_hosts:
            raise ValueError("live source policy requires an explicit host allowlist")
        if self.timeout_seconds <= 0 or self.max_attempts < 1 or self.max_bytes < 1 or self.max_items < 1:
            raise ValueError("live source policy limits must be positive")
        if not self.terms_reviewed:
            raise PermissionError("source terms must be reviewed before live fetching")


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self.skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"} and self.skip_depth:
            self.skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            cleaned = re.sub(r"\s+", " ", data).strip()
            if cleaned:
                self.parts.append(cleaned)


class LiveHttpClient:
    """Bounded HTTP reader; it never follows an unapproved host."""

    def __init__(self, policy: SourcePolicy):
        policy.validate()
        self.policy = policy

    def _allowed(self, url: str) -> bool:
        host = (urlparse(url).hostname or "").casefold()
        return any(host == allowed.casefold() or host.endswith("." + allowed.casefold()) for allowed in self.policy.allowed_hosts)

    def read(self, url: str) -> tuple[str, str]:
        if not self._allowed(url):
            raise PermissionError(f"host is not allowlisted: {urlparse(url).hostname or '(missing)'}")
        request = Request(url, headers={"User-Agent": self.policy.user_agent, "Accept": "text/html,application/rss+xml,application/atom+xml,application/xml"})
        last_error: Exception | None = None
        for attempt in range(self.policy.max_attempts):
            try:
                with urlopen(request, timeout=self.policy.timeout_seconds) as response:
                    final_url = response.geturl()
                    if not self._allowed(final_url):
                        raise PermissionError(f"redirected to a host that is not allowlisted: {urlparse(final_url).hostname or '(missing)'}")
                    content_type = response.headers.get_content_type()
                    body = response.read(self.policy.max_bytes + 1)
                if len(body) > self.policy.max_bytes:
                    raise ValueError("source response exceeded the configured byte limit")
                return body.decode("utf-8", errors="replace"), content_type
            except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
                last_error = exc
                if attempt + 1 < self.policy.max_attempts:
                    time.sleep(0.05 * (attempt + 1))
        raise RuntimeError(f"source fetch failed after {self.policy.max_attempts} attempts") from last_error


class CompanyCareerPageAdapter:
    """Fetch one explicitly permitted career page as a source record."""

    source_name = "company_career_page"

    def __init__(self, url: str, policy: SourcePolicy, client: LiveHttpClient | None = None):
        self.url = url
        self.client = client or LiveHttpClient(policy)
        self.errors: list[str] = []

    def fetch(self) -> tuple[SourceItem, ...]:
        try:
            body, _content_type = self.client.read(self.url)
            parser = _TextExtractor()
            parser.feed(body)
            text = "\n".join(parser.parts)
            if not text:
                return ()
            source_id = "career-" + sha256(self.url.encode("utf-8")).hexdigest()[:20]
            return (SourceItem(source_id, self.source_name, JobInput("url", text, self.url, self.source_name)),)
        except Exception as exc:
            self.errors.append(f"{type(exc).__name__}: {exc}")
            return ()


class RssFeedAdapter:
    """Read bounded RSS/Atom entries from an explicitly permitted feed."""

    source_name = "rss_feed"

    def __init__(self, url: str, policy: SourcePolicy, client: LiveHttpClient | None = None):
        self.url = url
        self.client = client or LiveHttpClient(policy)
        self.errors: list[str] = []

    def fetch(self) -> tuple[SourceItem, ...]:
        try:
            body, _content_type = self.client.read(self.url)
            root = ElementTree.fromstring(body)
            entries = list(root.findall(".//item")) or list(root.findall(".//{http://www.w3.org/2005/Atom}entry"))
            items: list[SourceItem] = []
            for entry in entries[: self.client.policy.max_items]:
                title = self._child_text(entry, "title") or self._child_text(entry, "{http://www.w3.org/2005/Atom}title")
                description = self._child_text(entry, "description") or self._child_text(entry, "{http://www.w3.org/2005/Atom}summary")
                link = self._child_text(entry, "link") or self._atom_link(entry)
                published = self._child_text(entry, "pubDate") or self._child_text(entry, "{http://www.w3.org/2005/Atom}published")
                if not title and not description:
                    continue
                absolute_link = urljoin(self.url, link or self.url)
                raw = "\n".join(filter(None, (f"Title: {title}" if title else "", f"Posted: {published}" if published else "", description or "")))
                source_id = "feed-" + sha256(absolute_link.encode("utf-8")).hexdigest()[:20]
                items.append(SourceItem(source_id, self.source_name, JobInput("url", raw, absolute_link, self.source_name)))
            return tuple(items)
        except Exception as exc:
            self.errors.append(f"{type(exc).__name__}: {exc}")
            return ()

    @staticmethod
    def _child_text(element: ElementTree.Element, tag: str) -> str | None:
        child = element.find(tag)
        return (child.text or "").strip() if child is not None and child.text else None

    @staticmethod
    def _atom_link(element: ElementTree.Element) -> str | None:
        for link in element.findall("{http://www.w3.org/2005/Atom}link"):
            if link.get("href"):
                return link.get("href")
        return None


class SavedInputAdapter:
    """Adapter for pasted descriptions and saved URLs; useful offline and in tests."""

    source_name = "saved_input"

    def __init__(self, inputs: tuple[JobInput, ...]):
        self._inputs = inputs

    def fetch(self) -> tuple[SourceItem, ...]:
        return tuple(
            SourceItem(
                source_item_id=f"saved-{index}",
                source_name=self.source_name,
                input=item,
            )
            for index, item in enumerate(self._inputs, start=1)
        )

    def normalize(self) -> tuple[JobRecord, ...]:
        return tuple(normalize_job(item.input) for item in self.fetch())


def ingest_from_adapter(adapter: JobSourceAdapter) -> tuple[JobRecord, ...]:
    """Normalize adapter output; adapter content remains untrusted data."""

    return tuple(normalize_job(item.input) for item in adapter.fetch())
