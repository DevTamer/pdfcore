"""pdfcore — shared PDF viewing/state plumbing for the PDF Redactor and PDF
Editor macOS apps.

What lives here is deliberately app-agnostic: rendering pages to images,
mapping between PDF points and on-screen canvas pixels, holding an open
document plus a session-scoped (memory-only) undo/redo history, and
displaying a page on a Tk canvas. Anything that decides *what happens to
the document's content* — redaction, scrubbing, text editing — belongs in
the app that does it, not here. That keeps a change made for one app from
silently altering another app's guarantees (in particular, the redactor's
guarantee that removed content is really gone).

Importing ``pdfcore`` never imports ``tkinter``. That matters for
``pdfcore.frozen.configure_bundled_tcl_tk()``, which has to run before
tkinter is first imported, and it lets the non-GUI parts be used and tested
without a working Tk. The Tk-based page view lives in ``pdfcore.pageview``
and must be imported explicitly.
"""

from .coords import RENDER_DPI, CoordinateMapper
from .history import HISTORY_LIMIT, HistoryEntry, SnapshotHistory
from .renderer import CACHE_LIMIT, PDFRenderer
from .session import DocumentSession

__version__ = "0.1.0"

__all__ = [
    "CACHE_LIMIT",
    "CoordinateMapper",
    "DocumentSession",
    "HISTORY_LIMIT",
    "HistoryEntry",
    "PDFRenderer",
    "RENDER_DPI",
    "SnapshotHistory",
    "__version__",
]
