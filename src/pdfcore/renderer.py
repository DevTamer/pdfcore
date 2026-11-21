"""Rendering PDF pages to PIL images, with a small LRU cache."""

from __future__ import annotations

from collections import OrderedDict
from typing import Optional

import pymupdf
from PIL import Image

from .coords import RENDER_DPI

CACHE_LIMIT = 5  # Rendered pages kept in memory by default


class PDFRenderer:
    """Renders PDF pages to PIL Images at RENDER_DPI with an LRU cache.

    The cache is keyed by page number only, so callers must call
    ``invalidate()`` whenever the document a page number refers to changes
    (a different file is opened, content is modified, history is undone...).
    """

    def __init__(self, cache_limit: int = CACHE_LIMIT):
        if cache_limit < 1:
            raise ValueError("cache_limit must be at least 1")
        self.cache_limit = cache_limit
        self._cache: "OrderedDict[int, Image.Image]" = OrderedDict()

    def render_page(self, page: pymupdf.Page, page_num: int) -> Image.Image:
        """Render a page at RENDER_DPI. Returns a PIL Image."""
        if page_num in self._cache:
            self._cache.move_to_end(page_num)
            return self._cache[page_num]

        pix = page.get_pixmap(dpi=RENDER_DPI)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        self._cache[page_num] = img
        if len(self._cache) > self.cache_limit:
            self._cache.popitem(last=False)

        return img

    def invalidate(self, page_num: Optional[int] = None) -> None:
        """Drop one cached page, or every cached page if none is given."""
        if page_num is not None:
            self._cache.pop(page_num, None)
        else:
            self._cache.clear()
