"""Tests for DocumentSession: open/close lifecycle, paging, and history."""

import pymupdf
import pytest

from pdfcore import DocumentSession, PasswordProtectedError
from conftest import PAGE_TEXTS


def _stamp(session: DocumentSession, page_num: int, text: str) -> None:
    """Change the live document, the way an app operation would."""
    session.get_page(page_num).insert_text((50, 300), text)


@pytest.fixture
def session(sample_pdf_path):
    s = DocumentSession()
    s.open_document(str(sample_pdf_path))
    yield s
    s.close_document()


# -- Lifecycle ----------------------------------------------------------------

def test_new_session_has_no_document():
    s = DocumentSession()
    assert s.doc is None
    assert s.file_path is None
    assert s.page_count == 0
    assert s.history_entries() == []
    assert s.history_index == -1
    assert not s.can_undo()
    assert not s.can_redo()


def test_open_document(session, sample_pdf_path):
    assert session.page_count == len(PAGE_TEXTS)
    assert session.file_path == str(sample_pdf_path)
    assert session.current_page == 0
    assert session.history_entries() == ["Original"]
    assert session.history_index == 0
    assert "John Doe" in session.get_page(0).get_text()


def test_open_missing_file_raises():
    s = DocumentSession()
    with pytest.raises(Exception):
        s.open_document("/nonexistent/definitely-not-here.pdf")
    assert s.doc is None


def test_reopening_resets_page_and_history(session, sample_pdf_path):
    session.current_page = 2
    _stamp(session, 0, "edit")
    session.record_snapshot("Edit")

    session.open_document(str(sample_pdf_path))

    assert session.current_page == 0
    assert session.history_entries() == ["Original"]


def test_close_document_resets_everything(session):
    doc = session.doc
    session.current_page = 1

    session.close_document()

    assert doc.is_closed
    assert session.doc is None
    assert session.file_path is None
    assert session.current_page == 0
    assert session.page_count == 0
    assert session.history_entries() == []
    assert session.history_index == -1


def test_close_without_document_is_harmless():
    s = DocumentSession()
    s.close_document()
    assert s.doc is None


def test_session_never_modifies_the_source_file(session, sample_pdf_path):
    before = sample_pdf_path.read_bytes()
    _stamp(session, 0, "edit")
    session.record_snapshot("Edit")
    session.undo()
    session.redo()
    session.close_document()

    assert sample_pdf_path.read_bytes() == before


def test_history_limit_is_passed_through():
    assert DocumentSession(history_limit=3).history.limit == 3


# -- History ------------------------------------------------------------------

def test_record_snapshot_enables_undo(session):
    _stamp(session, 0, "first edit")
    session.record_snapshot("Edit 1")

    assert session.history_entries() == ["Original", "Edit 1"]
    assert session.history_index == 1
    assert session.can_undo()
    assert not session.can_redo()


def test_undo_and_redo_swap_the_live_document(session):
    _stamp(session, 0, "first edit")
    session.record_snapshot("Edit 1")

    assert session.undo() == "Original"
    assert "first edit" not in session.get_page(0).get_text()
    assert session.can_redo()

    assert session.redo() == "Edit 1"
    assert "first edit" in session.get_page(0).get_text()


def test_undo_closes_the_replaced_document(session):
    _stamp(session, 0, "first edit")
    session.record_snapshot("Edit 1")
    replaced = session.doc

    session.undo()

    assert replaced.is_closed
    assert not session.doc.is_closed


def test_jump_to_history(session):
    for i in range(3):
        _stamp(session, 0, f"edit {i}")
        session.record_snapshot(f"Edit {i}")

    assert session.jump_to_history(1) == "Edit 0"
    text = session.get_page(0).get_text()
    assert "edit 0" in text
    assert "edit 1" not in text


@pytest.mark.parametrize("bad_index", [-1, 1, 7])
def test_jump_out_of_range_raises(session, bad_index):
    with pytest.raises(IndexError):
        session.jump_to_history(bad_index)


def test_undo_with_nothing_to_undo_raises(session):
    with pytest.raises(ValueError):
        session.undo()


def test_redo_with_nothing_to_redo_raises(session):
    with pytest.raises(ValueError):
        session.redo()


def test_undo_keeps_current_page(session):
    _stamp(session, 0, "edit")
    session.record_snapshot("Edit")
    session.current_page = 2

    session.undo()

    assert session.current_page == 2


def test_undo_clamps_current_page_when_snapshot_has_fewer_pages(session):
    # Snapshot "Original" has 3 pages; grow the doc to 4 and view page 4.
    session.doc.new_page()
    session.record_snapshot("Added page")
    session.current_page = 3

    session.undo()

    assert session.page_count == 3
    assert session.current_page == 2


def test_undo_does_not_touch_snapshots_with_later_edits(session):
    """Editing the live document after an undo must not leak into the
    snapshot it was loaded from (redo must still return the real state)."""
    _stamp(session, 0, "edit A")
    session.record_snapshot("A")
    session.undo()

    _stamp(session, 0, "unrecorded scribble")
    session.redo()

    text = session.get_page(0).get_text()
    assert "edit A" in text
    assert "unrecorded scribble" not in text


def test_zero_page_document_is_closed_on_close():
    """pymupdf.Document is falsy when it has no pages; make sure that doesn't
    stop close_document from closing it."""
    s = DocumentSession()
    empty = pymupdf.open()
    s.doc = empty

    s.close_document()

    assert empty.is_closed


# -- Failed opens ----------------------------------------------------------------

def _encrypted_pdf(path):
    doc = pymupdf.open()
    doc.new_page().insert_text((50, 100), "secret")
    doc.save(str(path), encryption=pymupdf.PDF_ENCRYPT_AES_256,
             user_pw="pw", owner_pw="pw")
    doc.close()


def _assert_empty(s):
    assert s.doc is None
    assert s.file_path is None
    assert s.page_count == 0
    assert s.history_entries() == []
    assert s.history_index == -1


def test_password_protected_pdf_is_refused_cleanly(tmp_path):
    path = tmp_path / "locked.pdf"
    _encrypted_pdf(path)
    s = DocumentSession()
    with pytest.raises(PasswordProtectedError, match="password-protected"):
        s.open_document(str(path))
    _assert_empty(s)


def test_failed_open_closes_the_previous_document(session, tmp_path):
    previous = session.doc
    path = tmp_path / "locked.pdf"
    _encrypted_pdf(path)
    with pytest.raises(PasswordProtectedError):
        session.open_document(str(path))
    assert previous.is_closed
    _assert_empty(session)


def test_unreadable_file_is_refused_cleanly(tmp_path):
    path = tmp_path / "junk.pdf"
    path.write_bytes(b"not a pdf at all")
    s = DocumentSession()
    with pytest.raises(Exception):
        s.open_document(str(path))
    _assert_empty(s)


def test_password_error_is_a_value_error():
    assert issubclass(PasswordProtectedError, ValueError)
