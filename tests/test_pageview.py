"""Tests for PageView, using a real (hidden) Tk canvas.

Needs a Tcl/Tk that works on this machine and a display session; skips
itself cleanly when a Tk root can't be created (headless CI, Apple's
system Python, ...).
"""

import fitz
import pytest

from pdfcore import PDFRenderer

tk = pytest.importorskip("tkinter")

from pdfcore.pageview import (  # noqa: E402  (after the importorskip)
    MIN_FIT_WIDTH, PAGE_IMAGE_TAG, PageView,
)

BOX = fitz.Rect(300, 400, 360, 440)


@pytest.fixture
def root():
    try:
        r = tk.Tk()
    except Exception as exc:  # no working Tk / no display
        pytest.skip(f"Tk isn't usable in this environment: {exc}")
    r.withdraw()
    yield r
    r.destroy()


@pytest.fixture
def view(root):
    canvas = tk.Canvas(root, width=600, height=400)
    return PageView(canvas, PDFRenderer())


@pytest.fixture
def boxed_page():
    doc = fitz.open()
    page = doc.new_page(width=500, height=600)
    page.draw_rect(BOX, color=(0, 0, 0), fill=(0, 0, 0))
    yield page
    doc.close()


def test_display_size_is_zero_before_showing(view):
    assert view.display_size == (0, 0)


def test_show_page_scales_to_fit_width(view, boxed_page):
    w, h = view.show_page(boxed_page, 0, fit_width=250)

    assert w == 250
    assert h == pytest.approx(300, abs=1)  # 500x600 page, aspect kept
    assert view.display_size == (w, h)
    scrollregion = [float(v) for v in str(view.canvas.cget("scrollregion")).split()]
    assert scrollregion == [0, 0, w, h]


def test_show_page_sets_mapper_scale(view, boxed_page):
    view.show_page(boxed_page, 0, fit_width=250)

    # 500pt wide page shown 250px wide: 0.5 canvas px per PDF point.
    assert view.mapper.total_scale == pytest.approx(0.5, rel=0.01)
    assert view.pdf_to_canvas(500, 600) == pytest.approx((250, 300), abs=1.5)
    assert view.canvas_to_pdf(250, 300) == pytest.approx((500, 600), abs=3)


def test_show_page_replaces_canvas_contents(view, boxed_page):
    view.canvas.create_rectangle(0, 0, 10, 10, tags=("stale",))
    view.show_page(boxed_page, 0, fit_width=250)
    view.show_page(boxed_page, 0, fit_width=300)

    assert view.canvas.find_withtag("stale") == ()
    assert len(view.canvas.find_withtag(PAGE_IMAGE_TAG)) == 1
    assert len(view.canvas.find_all()) == 1


def test_shown_pixels_match_coordinate_mapping(view, boxed_page):
    """The image actually on the canvas has the box where pdf_to_canvas
    says it is."""
    view.show_page(boxed_page, 0, fit_width=320)

    def shown_pixel(cx, cy):
        # ImageTk.PhotoImage has no .get(); ask Tk's image directly.
        rgb = view.canvas.tk.call(str(view._photo), "get", int(cx), int(cy))
        if isinstance(rgb, str):
            rgb = rgb.split()
        return [int(v) for v in rgb]

    cx, cy = view.pdf_to_canvas((BOX.x0 + BOX.x1) / 2, (BOX.y0 + BOX.y1) / 2)
    assert sum(shown_pixel(cx, cy)) < 60

    cx, cy = view.pdf_to_canvas(BOX.x0 - 10, BOX.y0 - 10)
    assert sum(shown_pixel(cx, cy)) > 700


def test_default_fit_width_uses_canvas_width_with_minimum(view, boxed_page):
    # A withdrawn, never-mapped canvas reports a tiny width, so the
    # minimum kicks in.
    w, _ = view.show_page(boxed_page, 0)
    assert w == MIN_FIT_WIDTH


def test_event_coords_account_for_scrolling(view, boxed_page, root):
    view.show_page(boxed_page, 0, fit_width=1000)  # taller than the canvas
    view.canvas.configure(height=200)
    view.canvas.pack()
    root.update_idletasks()
    view.canvas.yview_moveto(0.5)
    root.update_idletasks()

    class FakeEvent:
        x, y = 10, 10

    cx, cy = view.event_coords(FakeEvent)
    assert cx == pytest.approx(10 + view.canvas.canvasx(0))
    assert cy > 10  # scrolled down, so canvas y is offset
    assert cy == pytest.approx(10 + view.canvas.canvasy(0))


def test_render_is_cached_across_show_page_calls(view, boxed_page):
    view.show_page(boxed_page, 0, fit_width=250)
    first = view._pil_image
    view.show_page(boxed_page, 0, fit_width=300)
    assert view._pil_image is first
