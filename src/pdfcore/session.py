"""DocumentSession — an open PDF, the page being viewed, and its history."""

from __future__ import annotations

from typing import List, Optional

import fitz  # PyMuPDF

from .history import HISTORY_LIMIT, HistoryEntry, SnapshotHistory


class DocumentSession:
    """Owns the open ``fitz.Document``, the current page, and an in-memory
    snapshot history (see ``pdfcore.history``).

    Apps subclass this to add their own document operations and state (and
    their own saving — there's intentionally no ``save`` here, since what a
    safe save means differs per app). After an operation that changes the
    document, call ``record_snapshot(label)`` to make it undoable.

    Subclasses that keep extra per-document state should override
    ``open_document``/``close_document``, call ``super()``, then reset that
    state.
    """

    def __init__(self, history_limit: int = HISTORY_LIMIT):
        self.doc: Optional[fitz.Document] = None
        self.file_path: Optional[str] = None
        self.current_page: int = 0
        self.history = SnapshotHistory(limit=history_limit)

    # -- Document lifecycle -----------------------------------------------

    def open_document(self, path: str) -> None:
        """Open ``path``, replacing any currently open document.

        The file on disk is only read here; nothing in this class writes
        to it.
        """
        self.close_document()
        doc = fitz.open(path)
        self.doc = doc
        self.file_path = path
        self.current_page = 0
        self.history.reset(doc, "Original")

    def close_document(self) -> None:
        if self.doc is not None:
            self.doc.close()
        self.doc = None
        self.file_path = None
        self.current_page = 0
        self.history.clear()

    @property
    def page_count(self) -> int:
        return len(self.doc) if self.doc is not None else 0

    def get_page(self, page_num: int) -> fitz.Page:
        return self.doc[page_num]

    # -- Undo / redo history ----------------------------------------------

    def record_snapshot(self, label: str) -> None:
        """Record the current document state as a new history entry,
        discarding any redo branch beyond the current point."""
        self.history.record(self.doc, label)

    @property
    def history_index(self) -> int:
        return self.history.index

    def history_entries(self) -> List[str]:
        """Labels of every history entry, oldest first."""
        return self.history.labels

    def can_undo(self) -> bool:
        return self.history.can_undo()

    def can_redo(self) -> bool:
        return self.history.can_redo()

    def undo(self) -> str:
        """Revert to the previous history entry. Returns the label of the
        state now current."""
        return self._load(self.history.undo())

    def redo(self) -> str:
        """Re-apply the most recently undone state. Returns its label."""
        return self._load(self.history.redo())

    def jump_to_history(self, index: int) -> str:
        """Jump directly to an arbitrary history entry (as clicking an
        entry in a Photoshop-style history panel would). Returns its
        label."""
        return self._load(self.history.jump(index))

    def _load(self, entry: HistoryEntry) -> str:
        """Swap the live document for ``entry``'s snapshot, keeping the
        current page where possible."""
        old_page = self.current_page
        if self.doc is not None:
            self.doc.close()
        self.doc = entry.open()
        self.current_page = (min(old_page, self.page_count - 1)
                             if self.page_count else 0)
        return entry.label
