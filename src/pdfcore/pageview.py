"""PageView — shows one rendered PDF page on a Tk canvas.

This is the only pdfcore module that imports tkinter. Import it explicitly
(``from pdfcore.pageview import PageView``), and in a py2app-bundled app
only after calling ``pdfcore.frozen.configure_bundled_tcl_tk()``.
"""

from __future__ import annotations

import tkinter as tk
from typing import Optional, Tuple

import fitz  # PyMuPDF
from PIL import Image, ImageTk

from .coords import CoordinateMapper
from .renderer import PDFRenderer

PAGE_IMAGE_TAG = "page_image"
MIN_FIT_WIDTH = 400  # Smallest width a page is scaled to when auto-fitting
FIT_MARGIN = 20      # Horizontal room left beside the page when auto-fitting


class PageView:
    """Displays a page scaled to fit the canvas width, and converts between
    canvas pixels and PDF points for whatever page is currently shown.

    Apps subclass this (or wrap it) to add their own mouse handling and
    overlays. ``show_page`` clears the whole canvas, so a subclass should
    redraw its overlays after calling it.
    """

    def __init__(self, canvas: tk.Canvas, renderer: PDFRenderer):
        self.canvas = canvas
        self.renderer = renderer
        self._mapper = CoordinateMapper()
        self._photo: Optional[ImageTk.PhotoImage] = None  # prevent GC
        self._pil_image: Optional[Image.Image] = None
        self._display_size: Tuple[int, int] = (0, 0)

    # -- Coordinates ------------------------------------------------------

    @property
    def mapper(self) -> CoordinateMapper:
        return self._mapper

    @property
    def display_size(self) -> Tuple[int, int]:
        """(width, height) in canvas pixels of the page currently shown,
        or (0, 0) before any page has been shown."""
        return self._display_size

    def event_coords(self, event) -> Tuple[float, float]:
        """Scroll-aware canvas coordinates of a Tk mouse event."""
        return self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)

    def canvas_to_pdf(self, cx: float, cy: float) -> Tuple[float, float]:
        return self._mapper.canvas_to_pdf(cx, cy)

    def pdf_to_canvas(self, px: float, py: float) -> Tuple[float, float]:
        return self._mapper.pdf_to_canvas(px, py)

    # -- Display ----------------------------------------------------------

    def show_page(self, page: fitz.Page, page_num: int,
                  fit_width: Optional[int] = None) -> Tuple[int, int]:
        """Render ``page`` (cached under ``page_num``), scale it to
        ``fit_width`` pixels wide (default: the canvas's current width less
        a small margin), and make it the only thing on the canvas.

        Returns the displayed (width, height) in canvas pixels.
        """
        pil_image = self.renderer.render_page(page, page_num)
        self._pil_image = pil_image

        if fit_width is None:
            fit_width = max(self.canvas.winfo_width() - FIT_MARGIN,
                            MIN_FIT_WIDTH)

        self._mapper.total_scale = CoordinateMapper.compute_total_scale(
            pil_image.width, fit_width)
        display_scale = fit_width / pil_image.width

        new_w = int(pil_image.width * display_scale)
        new_h = int(pil_image.height * display_scale)
        display_img = pil_image.resize((new_w, new_h), Image.LANCZOS)

        # Keep a reference, or Tk shows a blank image once Python GCs it.
        self._photo = ImageTk.PhotoImage(display_img)

        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self._photo,
                                 tags=(PAGE_IMAGE_TAG,))
        self.canvas.config(scrollregion=(0, 0, new_w, new_h))
        self._display_size = (new_w, new_h)
        return new_w, new_h
