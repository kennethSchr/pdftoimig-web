"""PDFtoIMG — FastAPI web application."""

import io
import os
import zipfile
from collections import defaultdict
from pathlib import Path

import stripe
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from itsdangerous import BadSignature, SignatureExpired, TimestampSigner

from convert import convert_pdf

load_dotenv()

stripe.api_key        = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_ID       = os.getenv("STRIPE_PRICE_ID", "")
STRIPE_PUB_KEY        = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
DOWNLOAD_FILE         = Path(os.getenv("DOWNLOAD_FILE", "/downloads/PDFtoIMAGE.zip"))
TOKEN_SECRET          = os.getenv("TOKEN_SECRET", "change-me-in-production")

signer = TimestampSigner(TOKEN_SECRET)

app = FastAPI(title="PDFtoIMG")

# ── A/B test tracking (in-memory, resets on redeploy) ─────────────────────────
ab_impressions = defaultdict(int)
ab_clicks      = defaultdict(int)


# ── Convert ───────────────────────────────────────────────────────────────────

@app.post("/api/convert")
async def api_convert(
    file: UploadFile = File(...),
    dpi: int = Form(150),
    fmt: str = Form("png"),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")
    if dpi < 36 or dpi > 600:
        raise HTTPException(status_code=400, detail="DPI must be between 36 and 600.")
    if fmt not in ("png", "jpg"):
        raise HTTPException(status_code=400, detail="Format must be 'png' or 'jpg'.")

    pdf_bytes = await file.read()
    if len(pdf_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(pdf_bytes) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 50 MB.")

    try:
        images = convert_pdf(pdf_bytes, dpi=dpi, fmt=fmt)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not process PDF: {e}")

    if not images:
        raise HTTPException(status_code=422, detail="PDF appears to have no pages.")

    stem = Path(file.filename).stem
    buf  = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, img_bytes in enumerate(images, start=1):
            ext = "jpg" if fmt == "jpg" else "png"
            zf.writestr(f"{stem}_page{i:04d}.{ext}", img_bytes)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{stem}_images.zip"'},
    )


# ── Stripe: create checkout session ──────────────────────────────────────────

@app.post("/api/stripe/checkout")
async def create_checkout(request: Request):
    if not stripe.api_key or not STRIPE_PRICE_ID:
        raise HTTPException(status_code=503, detail="Stripe is not configured.")

    base = str(request.base_url).rstrip("/")
    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
            success_url=f"{base}/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{base}/?cancelled=1",
        )
    except stripe.StripeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return {"url": session.url}


# ── Stripe: webhook ───────────────────────────────────────────────────────────

@app.post("/api/stripe/webhook")
async def stripe_webhook(request: Request):
    payload    = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except stripe.errors.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature.")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        print(f"Payment confirmed: {session['id']} — {session.get('customer_email')}")

    return {"ok": True}


# ── Stripe: verify session → return signed download token ────────────────────

@app.get("/api/stripe/session")
async def get_session(session_id: str):
    if not stripe.api_key:
        raise HTTPException(status_code=503, detail="Stripe not configured.")
    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except stripe.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if session.payment_status != "paid":
        raise HTTPException(status_code=402, detail="Payment not completed.")

    # Generate a signed token valid for 24 hours
    token = signer.sign(session_id).decode()
    return {"download_token": token}


# ── Secure download ───────────────────────────────────────────────────────────

@app.get("/api/download/{token}")
async def secure_download(token: str):
    try:
        # max_age = 24 hours
        signer.unsign(token, max_age=86400)
    except SignatureExpired:
        raise HTTPException(status_code=410, detail="Download link has expired.")
    except BadSignature:
        raise HTTPException(status_code=403, detail="Invalid download link.")

    if not DOWNLOAD_FILE.exists():
        raise HTTPException(status_code=404, detail="File not found on server.")

    media = "application/octet-stream"
    return FileResponse(
        path=str(DOWNLOAD_FILE),
        media_type=media,
        filename=DOWNLOAD_FILE.name,
    )


# ── A/B test endpoints ────────────────────────────────────────────────────────

@app.post("/api/ab/impression")
async def ab_impression(request: Request):
    data = await request.json()
    variant = data.get("variant", "unknown")
    ab_impressions[variant] += 1
    return {"ok": True}

@app.post("/api/ab/click")
async def ab_click(request: Request):
    data = await request.json()
    variant = data.get("variant", "unknown")
    ab_clicks[variant] += 1
    return {"ok": True}

@app.get("/api/ab/results")
def ab_results():
    variants = sorted(set(list(ab_impressions.keys()) + list(ab_clicks.keys())))
    rows = []
    for v in variants:
        imp = ab_impressions[v]
        clicks = ab_clicks[v]
        ctr = round(clicks / imp * 100, 1) if imp > 0 else 0
        rows.append({"variant": v, "impressions": imp, "clicks": clicks, "ctr": f"{ctr}%"})
    return {"results": rows}


# ── Pages ─────────────────────────────────────────────────────────────────────

@app.get("/success")
async def success_page():
    return FileResponse(str(Path(__file__).parent / "static" / "success.html"))


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok"}


# ── Static frontend (must be last) ────────────────────────────────────────────
static_dir = Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
