"""PDF → images conversion logic (shared by CLI and web)."""

from pathlib import Path


def convert_pdf(pdf_bytes: bytes, dpi: int = 150, fmt: str = "png") -> list[bytes]:
    """
    Convert PDF bytes to a list of image bytes (one per page).

    Args:
        pdf_bytes: Raw PDF file content.
        dpi:       Output resolution (default 150).
        fmt:       'png' or 'jpg'.

    Returns:
        List of image bytes in page order.
    """
    import fitz  # PyMuPDF

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)
    images = []

    for page in doc:
        pix = page.get_pixmap(matrix=matrix)
        if fmt == "jpg":
            images.append(pix.tobytes("jpeg"))
        else:
            images.append(pix.tobytes("png"))

    return images
