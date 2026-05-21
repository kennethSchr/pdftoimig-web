"""PDFtoIMG — FastAPI web application."""

import io
import zipfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from convert import convert_pdf

app = FastAPI(title="PDFtoIMG")

# ── API ───────────────────────────────────────────────────────────────────────

@app.post("/api/convert")
async def api_convert(
    file: UploadFile = File(...),
    dpi: int = Form(150),
    fmt: str = Form("png"),
):
    # Validate
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")
    if dpi < 36 or dpi > 600:
        raise HTTPException(status_code=400, detail="DPI must be between 36 and 600.")
    if fmt not in ("png", "jpg"):
        raise HTTPException(status_code=400, detail="Format must be 'png' or 'jpg'.")

    pdf_bytes = await file.read()
    if len(pdf_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(pdf_bytes) > 50 * 1024 * 1024:  # 50 MB limit
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 50 MB.")

    # Convert
    try:
        images = convert_pdf(pdf_bytes, dpi=dpi, fmt=fmt)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not process PDF: {e}")

    if not images:
        raise HTTPException(status_code=422, detail="PDF appears to have no pages.")

    # Pack into ZIP
    stem = Path(file.filename).stem
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, img_bytes in enumerate(images, start=1):
            ext = "jpg" if fmt == "jpg" else "png"
            zf.writestr(f"{stem}_page{i:04d}.{ext}", img_bytes)
    buf.seek(0)

    zip_name = f"{stem}_images.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_name}"'},
    )


@app.get("/api/health")
def health():
    return {"status": "ok"}


# ── Static frontend (must be last) ────────────────────────────────────────────
static_dir = Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
