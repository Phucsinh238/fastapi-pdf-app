from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse, HTMLResponse, StreamingResponse
import paypalrestsdk
from app.database import get_document_by_id, get_db
from sqlalchemy.orm import Session
from app.models import Purchase, User, Document
import boto3, io
from datetime import datetime

# ==============================
# 🔧 Config PayPal (LIVE)
# ==============================
paypalrestsdk.configure({
    "mode": "live",   # 🔥 LIVE MODE 
    "client_id": "AfRAxtTLX8MQiNBF_WPZpHIeK3rr4qIP_jKWylw33oZIL_9pHmH0YlwPX5u6ZtVryLC2uR5EDBTdB-OJ",
    "client_secret": "EGo2TwZrGZO12ZlMIc3TgnW-ReDv4skxIAbLeRRx8OgW5uzqkfIanwrX2GBe2DTr8b0gOxsYKBEGkAFd"
})

router = APIRouter()

# ==============================
# 🔧 Config Cloudflare R2
# ==============================
R2_ACCESS_KEY = "24bcd7f68391b74c3712d0919b6a0c66"
R2_SECRET_KEY = "8eb34c1864c1e90ec42f67d0217aa2e3e7fac5225dd8b32e52b3575536ac6f4b"
R2_BUCKET = "fastapi-pdf-app"
R2_ENDPOINT = "https://bcdb766b6e3d7d90bf451671a1d7c3de.r2.cloudflarestorage.com"

s3 = boto3.client(
    "s3",
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
)


# 🛒 Tạo thanh toán
@router.get("/pay/{file_id}")
def create_payment(file_id: int, request: Request):
    document = get_document_by_id(file_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    price = float(document.get("price", 19.99))
    base_url = str(request.base_url).rstrip("/")

    payment = paypalrestsdk.Payment({
        "intent": "sale",
        "payer": {"payment_method": "paypal"},
        "redirect_urls": {
            "return_url": f"{base_url}/payment/success?file_id={file_id}",
            "cancel_url": f"{base_url}/payment/cancel"
        },
        "transactions": [{
            "item_list": {
                "items": [{
                    "name": document["filename"],
                    "sku": f"file-{file_id}",
                    "price": f"{price:.2f}",
                    "currency": "USD",
                    "quantity": 1
                }]
            },
            "amount": {"total": f"{price:.2f}", "currency": "USD"},
            "description": f"Access full document #{file_id}"
        }]
    })

    if payment.create():
        for link in payment.links:
            if link.rel == "approval_url":
                return RedirectResponse(url=link.href)
        raise HTTPException(status_code=500, detail="Approval URL not found.")
    else:
        raise HTTPException(status_code=500, detail="Payment creation failed.")


# ✅ Thanh toán thành công
@router.get("/payment/success")
def payment_success(request: Request, paymentId: str, PayerID: str, file_id: int, db: Session = Depends(get_db)):
    payment = paypalrestsdk.Payment.find(paymentId)
    if not payment.execute({"payer_id": PayerID}):
        raise HTTPException(status_code=400, detail="Payment failed.")

    # 🧩 Kiểm tra user đăng nhập
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User must be logged in to complete payment.")

    # 🧩 Ghi vào session cũ
    if "paid_files" not in request.session:
        request.session["paid_files"] = []
    if file_id not in request.session["paid_files"]:
        request.session["paid_files"].append(file_id)

    # 🧩 Ghi vào bảng purchases
    existing = db.query(Purchase).filter(
        Purchase.user_id == user_id,
        Purchase.document_id == file_id
    ).first()

    if not existing:
        new_purchase = Purchase(
            user_id=user_id,
            document_id=file_id,
            purchased_at=datetime.utcnow()
        )
        db.add(new_purchase)
        db.commit()

    document = get_document_by_id(file_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    base_url = str(request.base_url).rstrip("/")
    download_url = f"{base_url}/download/{file_id}"

    html_content = f"""
    <html>
        <head><meta charset="utf-8" /><title>Download</title></head>
        <body style="font-family: Arial; text-align: center; margin-top: 50px;">
            <h2>✅ Payment Successful!</h2>
            <p>Your file <b>{document["filename"]}</b> is ready. if file is not dounloaded automatically, please do right click on Download file and click save link as...</p>
            <a href="{download_url}" style="background: #0070f3; color: white; padding: 10px 20px; border-radius: 5px; text-decoration: none;">⬇️ Download File</a>
            <script>setTimeout(() => {{ window.location = "{download_url}"; }}, 1000);</script>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)


# ❌ Thanh toán bị hủy
@router.get("/payment/cancel")
def payment_cancel(request: Request):
    request.session["flash"] = "❌ Bạn đã hủy thanh toán."
    base_url = str(request.base_url).rstrip("/")
    return RedirectResponse(url=base_url, status_code=303)


# 📥 Download file (check login + quyền)
@router.get("/download/{file_id}")
def download_file(request: Request, file_id: int, db: Session = Depends(get_db)):
    # 🧩 Kiểm tra login
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="You must be logged in to download files.")

    # 🧩 Lấy file
    document = db.query(Document).filter(Document.id == file_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # 🧩 Kiểm tra quyền tải
    purchase = db.query(Purchase).filter(
        Purchase.user_id == user_id,
        Purchase.document_id == file_id
    ).first()

    user = db.query(User).filter(User.id == user_id).first()
    is_uploader = document.uploaded_by == user.username if user else False

    if not purchase and not is_uploader:
        raise HTTPException(status_code=403, detail="You do not have access to this file.")

    # 🧩 Tải file từ R2
    file_obj = io.BytesIO()
    try:
        s3.download_fileobj(R2_BUCKET, document.filepath, file_obj)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"File not found in R2: {str(e)}")

    file_obj.seek(0)
    return StreamingResponse(
        file_obj,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{document.filename}"'}
    )
