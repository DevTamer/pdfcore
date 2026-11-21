"""End-to-end check that the rendered image and the coordinate math agree:
a shape drawn at known PDF coordinates must show up at the pixel position
CoordinateMapper says it's at. Both apps rely on this (the redactor to
remove what you drew over, the editor to edit what you clicked on)."""

import pymupdf
import pytest

from pdfcore import CoordinateMapper, PDFRenderer

# A solid black box at a known place on a white 500x600pt page.
BOX = pymupdf.Rect(300, 400, 360, 440)


@pytest.fixture
def boxed_page():
    doc = pymupdf.open()
    page = doc.new_page(width=500, height=600)
    page.draw_rect(BOX, color=(0, 0, 0), fill=(0, 0, 0))
    yield page
    doc.close()


def _is_dark(rgb) -> bool:
    return sum(rgb[:3]) < 60


def _is_light(rgb) -> bool:
    return sum(rgb[:3]) > 700


@pytest.mark.parametrize("fit_width", [None, 300, 1500])
def test_box_lands_where_the_mapper_says(boxed_page, fit_width):
    image = PDFRenderer().render_page(boxed_page, 0)
    if fit_width is None:
        fit_width = image.width  # no display scaling, render scale only
    mapper = CoordinateMapper(
        CoordinateMapper.compute_total_scale(image.width, fit_width))
    display = image.resize(
        (int(image.width * fit_width / image.width),
         int(image.height * fit_width / image.width)))

    # Centre of the box: dark.
    cx, cy = mapper.pdf_to_canvas((BOX.x0 + BOX.x1) / 2, (BOX.y0 + BOX.y1) / 2)
    assert _is_dark(display.getpixel((int(cx), int(cy))))

    # Just outside each edge (a few points out): light.
    for px, py in [(BOX.x0 - 5, BOX.y0 + 20), (BOX.x1 + 5, BOX.y0 + 20),
                   (BOX.x0 + 30, BOX.y0 - 5), (BOX.x0 + 30, BOX.y1 + 5)]:
        cx, cy = mapper.pdf_to_canvas(px, py)
        assert _is_light(display.getpixel((int(cx), int(cy)))), (px, py)


def test_canvas_point_maps_back_into_the_box(boxed_page):
    image = PDFRenderer().render_page(boxed_page, 0)
    mapper = CoordinateMapper(
        CoordinateMapper.compute_total_scale(image.width, 400))

    # Click in the middle of where the box appears on screen...
    cx0, cy0 = mapper.pdf_to_canvas(BOX.x0, BOX.y0)
    cx1, cy1 = mapper.pdf_to_canvas(BOX.x1, BOX.y1)
    px, py = mapper.canvas_to_pdf((cx0 + cx1) / 2, (cy0 + cy1) / 2)

    # ...and it should resolve to a PDF point inside the box.
    assert pymupdf.Point(px, py) in BOX
