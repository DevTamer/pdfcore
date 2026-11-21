"""Pure PDF-point <-> canvas-pixel coordinate math (no Tk dependency)."""

from __future__ import annotations

from typing import Tuple

# DPI that pages are rasterized at for display. PDFRenderer and
# CoordinateMapper both read this one constant so the image on screen and
# the coordinate math can't disagree about the render scale.
RENDER_DPI = 150


class CoordinateMapper:
    """Converts between PDF point space and displayed canvas pixel space.

    ``total_scale`` is canvas pixels per PDF point: the render scale
    (RENDER_DPI / 72) multiplied by whatever extra scaling was applied to
    fit the rendered image into the visible canvas.

    Kept free of any Tk dependency so it can be unit tested without a live
    display/canvas.
    """

    def __init__(self, total_scale: float = 1.0):
        self.total_scale = total_scale

    def canvas_to_pdf(self, cx: float, cy: float) -> Tuple[float, float]:
        if self.total_scale == 0:
            return 0.0, 0.0
        return cx / self.total_scale, cy / self.total_scale

    def pdf_to_canvas(self, px: float, py: float) -> Tuple[float, float]:
        return px * self.total_scale, py * self.total_scale

    @staticmethod
    def render_scale() -> float:
        return RENDER_DPI / 72.0

    @staticmethod
    def compute_total_scale(image_width: int, fit_width: int) -> float:
        """Combine render DPI scale with the display-fit scale."""
        display_scale = fit_width / image_width
        return CoordinateMapper.render_scale() * display_scale
