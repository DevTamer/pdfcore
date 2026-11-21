"""Session-scoped, in-memory undo/redo history of whole-document snapshots.

A lightweight "history palette" (Photoshop-style): each recorded action
becomes one entry holding a full serialized copy of the document at that
point. Undo/redo/jump hand back an earlier or later entry for the caller to
load.

This is deliberately memory-only and nothing here ever writes to disk. For
the redactor that's a security property, not just a convenience: a
redaction's whole point is that removed content can't be recovered, so
history that could bring it back must not outlive the running app. Keep it
that way — don't add persistence to this module. An app that wants
persistent history should build that itself, in its own code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import pymupdf

HISTORY_LIMIT = 20  # Max snapshots kept by default


@dataclass(frozen=True)
class HistoryEntry:
    """One snapshot of the document."""

    label: str
    doc_bytes: bytes

    def open(self) -> pymupdf.Document:
        """A new, independent pymupdf.Document holding this snapshot."""
        return pymupdf.open(stream=self.doc_bytes, filetype="pdf")


class SnapshotHistory:
    """An ordered list of document snapshots plus a "current" position.

    Recording a new snapshot while positioned before the end discards the
    redo branch beyond the current position. Once more than ``limit``
    snapshots exist, the oldest are dropped — including the very first one
    (usually the "Original" state), so undo can't reach further back than
    what's left.
    """

    def __init__(self, limit: int = HISTORY_LIMIT):
        if limit < 1:
            raise ValueError("limit must be at least 1")
        self.limit = limit
        self._entries: List[HistoryEntry] = []
        self._index: int = -1

    # -- Recording --------------------------------------------------------

    def reset(self, doc: pymupdf.Document, label: str = "Original") -> None:
        """Forget everything and start over with ``doc`` as the only entry."""
        self.clear()
        self.record(doc, label)

    def clear(self) -> None:
        self._entries = []
        self._index = -1

    def record(self, doc: pymupdf.Document, label: str) -> None:
        """Snapshot ``doc``'s current state as a new entry, discarding any
        redo branch beyond the current position."""
        del self._entries[self._index + 1:]
        self._entries.append(HistoryEntry(label=label, doc_bytes=doc.tobytes()))
        if len(self._entries) > self.limit:
            del self._entries[:len(self._entries) - self.limit]
        self._index = len(self._entries) - 1

    # -- Inspection -------------------------------------------------------

    @property
    def index(self) -> int:
        """Position of the current entry, or -1 when empty."""
        return self._index

    @property
    def labels(self) -> List[str]:
        """Labels of every entry, oldest first."""
        return [e.label for e in self._entries]

    @property
    def current(self) -> HistoryEntry:
        if self._index < 0:
            raise IndexError("History is empty")
        return self._entries[self._index]

    def __len__(self) -> int:
        return len(self._entries)

    def can_undo(self) -> bool:
        return self._index > 0

    def can_redo(self) -> bool:
        return self._index < len(self._entries) - 1

    # -- Moving -----------------------------------------------------------

    def undo(self) -> HistoryEntry:
        """Step back one entry and return it."""
        if not self.can_undo():
            raise ValueError("Nothing to undo")
        return self.jump(self._index - 1)

    def redo(self) -> HistoryEntry:
        """Step forward one entry and return it."""
        if not self.can_redo():
            raise ValueError("Nothing to redo")
        return self.jump(self._index + 1)

    def jump(self, index: int) -> HistoryEntry:
        """Move directly to an arbitrary entry and return it."""
        if not (0 <= index < len(self._entries)):
            raise IndexError(f"History index {index} out of range")
        self._index = index
        return self._entries[index]
