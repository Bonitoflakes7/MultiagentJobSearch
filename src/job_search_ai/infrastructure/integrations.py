"""Safe integration contracts and local source adapters."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

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

