"""Tests for SnapshotHistory: the in-memory undo/redo stack of snapshots."""

import pymupdf
import pytest

from pdfcore import HISTORY_LIMIT, HistoryEntry, SnapshotHistory


def _doc_with_text(text: str) -> pymupdf.Document:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 100), text)
    return doc


def _text_of(entry: HistoryEntry) -> str:
    doc = entry.open()
    try:
        return doc[0].get_text().strip()
    finally:
        doc.close()


@pytest.fixture
def history_abc():
    """A history with three entries, A/B/C, positioned at C."""
    history = SnapshotHistory()
    for label in ("A", "B", "C"):
        doc = _doc_with_text(f"state {label}")
        history.record(doc, label)
        doc.close()
    return history


# -- Empty / reset ------------------------------------------------------------

def test_new_history_is_empty():
    history = SnapshotHistory()
    assert len(history) == 0
    assert history.index == -1
    assert history.labels == []
    assert not history.can_undo()
    assert not history.can_redo()
    with pytest.raises(IndexError):
        history.current


def test_reset_leaves_only_the_given_document(history_abc):
    doc = _doc_with_text("fresh")
    history_abc.reset(doc)

    assert history_abc.labels == ["Original"]
    assert history_abc.index == 0
    assert _text_of(history_abc.current) == "fresh"
    doc.close()


def test_clear_empties_everything(history_abc):
    history_abc.clear()
    assert len(history_abc) == 0
    assert history_abc.index == -1


@pytest.mark.parametrize("bad_limit", [0, -5])
def test_limit_must_be_positive(bad_limit):
    with pytest.raises(ValueError):
        SnapshotHistory(limit=bad_limit)


def test_default_limit():
    assert SnapshotHistory().limit == HISTORY_LIMIT


# -- Snapshots are real, independent copies -----------------------------------

def test_snapshot_is_unaffected_by_later_changes_to_the_document():
    history = SnapshotHistory()
    doc = _doc_with_text("before")
    history.record(doc, "Before")

    doc[0].insert_text((50, 200), "added later")

    assert "added later" not in _text_of(history.current)
    doc.close()


def test_entry_open_returns_independent_documents(history_abc):
    entry = history_abc.current
    first = entry.open()
    second = entry.open()
    try:
        first[0].insert_text((50, 300), "mutated")
        assert "mutated" not in second[0].get_text()
        assert "mutated" not in _text_of(entry)
    finally:
        first.close()
        second.close()


# -- Undo / redo / jump -------------------------------------------------------

def test_undo_and_redo_walk_the_entries(history_abc):
    assert history_abc.undo().label == "B"
    assert history_abc.undo().label == "A"
    assert not history_abc.can_undo()
    assert history_abc.redo().label == "B"
    assert history_abc.redo().label == "C"
    assert not history_abc.can_redo()


def test_undo_returns_the_matching_snapshot_content(history_abc):
    assert _text_of(history_abc.undo()) == "state B"


def test_undo_at_start_raises(history_abc):
    history_abc.jump(0)
    with pytest.raises(ValueError):
        history_abc.undo()


def test_redo_at_end_raises(history_abc):
    with pytest.raises(ValueError):
        history_abc.redo()


def test_jump_moves_to_any_entry(history_abc):
    entry = history_abc.jump(0)
    assert entry.label == "A"
    assert history_abc.index == 0
    assert history_abc.can_redo()


@pytest.mark.parametrize("bad_index", [-1, 3, 99])
def test_jump_out_of_range_raises_and_does_not_move(history_abc, bad_index):
    with pytest.raises(IndexError):
        history_abc.jump(bad_index)
    assert history_abc.index == 2


def test_record_after_undo_discards_redo_branch(history_abc):
    history_abc.undo()  # at B
    doc = _doc_with_text("state D")
    history_abc.record(doc, "D")
    doc.close()

    assert history_abc.labels == ["A", "B", "D"]
    assert history_abc.index == 2
    assert not history_abc.can_redo()


# -- Size cap -----------------------------------------------------------------

def test_oldest_entries_are_dropped_beyond_limit():
    history = SnapshotHistory(limit=3)
    doc = _doc_with_text("x")
    for i in range(5):
        history.record(doc, f"step {i}")
    doc.close()

    assert history.labels == ["step 2", "step 3", "step 4"]
    assert history.index == 2
    # Undo only reaches back as far as what's left.
    history.undo()
    history.undo()
    assert not history.can_undo()


def test_limit_of_one_keeps_only_the_latest():
    history = SnapshotHistory(limit=1)
    doc = _doc_with_text("x")
    history.record(doc, "first")
    history.record(doc, "second")
    doc.close()

    assert history.labels == ["second"]
    assert history.index == 0
    assert not history.can_undo()
