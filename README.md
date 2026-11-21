# pdfcore

Shared PDF viewing and document-state code for two macOS apps:

- [PDF Redactor](https://github.com/DevTamer/pdf-redactor-for-mac): true,
  permanent redaction
- [PDF Editor](https://github.com/DevTamer/pdf-editor-for-mac): click-to-edit
  text (in development)

It's a small library and not meant for general use. It exists so the two apps
don't each keep their own copy of the renderer and the coordinate math.

## What's in here

| Module | What it does | Needs Tk? |
|---|---|---|
| `pdfcore.renderer` | `PDFRenderer` renders pages to `PIL.Image`s at `RENDER_DPI`, with an LRU cache | no |
| `pdfcore.coords` | `CoordinateMapper` converts PDF points ↔ canvas pixels | no |
| `pdfcore.history` | `SnapshotHistory` is an in-memory undo/redo stack of whole-document snapshots | no |
| `pdfcore.session` | `DocumentSession` holds an open document, the current page and its history; apps subclass it | no |
| `pdfcore.frozen` | `configure_bundled_tcl_tk()`, a startup fix for py2app-bundled apps | no |
| `pdfcore.pageview` | `PageView` shows a page on a `tk.Canvas`, fit to width, and maps clicks to PDF points | **yes** |

`import pdfcore` never imports `tkinter`. Import `pdfcore.pageview`
explicitly when you need it.

## Rules for what belongs here

1. **No content-changing logic.** Redaction, scrubbing, text editing and
   saving stay in the app that does them. `DocumentSession` deliberately has
   no `save()`. That way a change made here for the editor can't weaken the
   redactor's guarantee that removed content is really gone.
2. **History stays in memory only.** `SnapshotHistory` must never write to
   disk. The redactor depends on undo history not outliving the app.
3. **Apps pin an exact version.** They depend on a tagged release
   (`pdfcore @ git+https://github.com/DevTamer/pdfcore.git@vX.Y.Z`) and
   move to a new one only after their own test suites pass against it.
4. **Anything that changes what apps see gets a version bump.** For
   pixel/coordinate behaviour (`RENDER_DPI`, scaling, `PageView` layout),
   bump at least the minor version and say so in the release notes.

## Usage

```python
from pdfcore.frozen import configure_bundled_tcl_tk
configure_bundled_tcl_tk()   # before the first `import tkinter`

import tkinter as tk
from pdfcore import DocumentSession, PDFRenderer
from pdfcore.pageview import PageView

class MyModel(DocumentSession):
    def do_something(self):
        ...                                # change self.doc
        self.record_snapshot("Did something")  # make it undoable

class MyView(PageView):
    def display(self, model):
        self.show_page(model.get_page(model.current_page), model.current_page)
        ...                                # redraw your overlays

```

## Developing alongside an app

Clone pdfcore next to the app(s) and install it in editable mode, so changes
here show up in the app immediately without tagging a release:

```
~/repos/pdfcore/
~/repos/pdf-redactor-for-mac/   # in its venv: pip install -e ../pdfcore
~/repos/pdf-editor-for-mac/     # in its venv: pip install -e ../pdfcore
```

Release builds of the apps install the pinned tag from their
`requirements.txt` instead.

## Running the tests

Use a Python with a working Tk (on macOS, Homebrew's `python-tk@3.11`; Apple's
system Python crashes on modern macOS when a Tk window opens):

```bash
/opt/homebrew/opt/python@3.11/bin/python3.11 -m venv venv
source venv/bin/activate
pip install -e . -r requirements-dev.txt
pytest
```

The `PageView` tests need a working Tk and a display. They skip themselves
when they don't have one. Everything else runs anywhere.

## Releasing

1. Bump `__version__` in `src/pdfcore/__init__.py`.
2. Run `pytest`.
3. Commit, then `git tag vX.Y.Z && git push --tags`.
4. In each app, update the pin in `requirements.txt`, run that app's
   tests, and release the app.
