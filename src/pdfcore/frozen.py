"""Startup fix-up for apps bundled as a standalone .app with py2app.

py2app relocates the Tcl/Tk *dylibs* into the bundle, but not Tcl/Tk's
script library (init.tcl, tk.tcl, ...). Without help, Tcl looks for that
library at a hardcoded build-machine path (e.g. a Homebrew Cellar path)
that won't exist on an end user's Mac. Apps copy the library into
``Contents/Resources/tcl/{tcl8.6,tk8.6}`` at build time and call
``configure_bundled_tcl_tk()`` at startup to point Tcl/Tk at it.

This module must not import tkinter (and neither may ``pdfcore``'s package
``__init__``), because the call has to happen before tkinter is imported.
"""

from __future__ import annotations

import os
import sys
from typing import MutableMapping, Optional


def configure_bundled_tcl_tk(
    environ: Optional[MutableMapping[str, str]] = None,
    frozen: Optional[bool] = None,
) -> bool:
    """Point TCL_LIBRARY/TK_LIBRARY at the copies bundled inside the app.

    Call this before the first ``import tkinter``. It does nothing unless
    running frozen under py2app (``sys.frozen`` set and ``RESOURCEPATH`` in
    the environment), so a normal dev run is unaffected.

    ``environ`` and ``frozen`` default to ``os.environ`` and
    ``sys.frozen``; they're parameters so tests can exercise this without
    actually being frozen.

    Returns True if it was running frozen (whether or not the bundled
    directories were found), False otherwise.
    """
    if environ is None:
        environ = os.environ
    if frozen is None:
        frozen = bool(getattr(sys, "frozen", False))

    if not frozen or "RESOURCEPATH" not in environ:
        return False

    resources = environ["RESOURCEPATH"]
    tcl_lib = os.path.join(resources, "tcl", "tcl8.6")
    tk_lib = os.path.join(resources, "tcl", "tk8.6")
    if os.path.isdir(tcl_lib):
        environ["TCL_LIBRARY"] = tcl_lib
    if os.path.isdir(tk_lib):
        environ["TK_LIBRARY"] = tk_lib
    return True
