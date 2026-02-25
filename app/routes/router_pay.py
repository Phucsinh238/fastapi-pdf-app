from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse, HTMLResponse, StreamingResponse
import paypalrestsdk
from app.database import get_document_by_id, get_db
from sqlalchemy.orm import Session
from app.models import Purchase, User, Document
import boto3, io
from datetime import datetime
import time
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

import math
import fitz  # PyMuPDF

from fastapi_mail import FastMail, MessageSchema
from app.routes.auth import conf   # dùng lại SMTP config đã có

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
    user_id = request.session.get("user_id")

    if not user_id:
        # ⚠️ Nếu chưa đăng nhập → chuyển đến trang login, kèm theo redirect_url để quay lại
        base_url = str(request.base_url).rstrip("/")
        login_url = f"{base_url}/login?next=/pay/{file_id}"
        return RedirectResponse(url=login_url, status_code=303)

    
    payment = paypalrestsdk.Payment({
        "intent": "sale",
        "payer": {"payment_method": "paypal"},
        "redirect_urls": {
            "return_url": f"{base_url}/payment/success?file_id={file_id}&user_id={user_id}",
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

@router.get("/payment/success")
async def payment_success(
    request: Request,
    paymentId: str,
    PayerID: str,
    file_id: int,
    user_id: int = None,       # ← cho phép PayPal redirect kèm user_id
    db: Session = Depends(get_db)
):
    payment = paypalrestsdk.Payment.find(paymentId)

    if not payment.execute({"payer_id": PayerID}):
        raise HTTPException(status_code=400, detail="Payment failed.")

    # 🧩 Kiểm tra login (session hoặc query)
    session_user_id = request.session.get("user_id")
    if not session_user_id:
        if user_id:
            session_user_id = user_id
            request.session["user_id"] = user_id  # Gắn lại session nếu mất
        else:
            raise HTTPException(status_code=401, detail="User must be logged in to complete payment.")

    # 🧩 Ghi session file đã trả tiền
    if "paid_files" not in request.session:
        request.session["paid_files"] = []
    if file_id not in request.session["paid_files"]:
        request.session["paid_files"].append(file_id)

    # 🧩 Ghi vào bảng purchases (chống trùng)
    existing = db.query(Purchase).filter(
        Purchase.user_id == session_user_id,
        Purchase.document_id == file_id
    ).first()

    if not existing:
        new_purchase = Purchase(
            user_id=session_user_id,
            document_id=file_id,
            purchased_at=datetime.utcnow()
        )
        db.add(new_purchase)
        db.commit()

    # 🧩 Kiểm tra file tồn tại
    document = get_document_by_id(file_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # 🧩 Tạo URL download động
    base_url = str(request.base_url).rstrip("/")
    download_url = f"{base_url}/secure-download/{file_id}"
    #download_url = f"{base_url}/secure-download/{file_id}?t={int(time.time())}"

    # 🧩 Lấy user
    user = db.query(User).filter(User.id == session_user_id).first()

    if user:
        try:
            message = MessageSchema(
                subject="Payment Successful - Download Link",
                recipients=[user.email],               # 📩 gửi cho user
                cc=["muabanraovat1982@gmail.com"],       # 📩 CC cho admin
                body=f"""
                <h2>Payment Successful ✅</h2>

                <p><b>User:</b> {user.username}</p>
                <p><b>Email:</b> {user.email}</p>
                <p><b>File:</b> {document["filename"]}</p>

                <p>Click below to download:</p>
                <a href="{download_url}">{download_url}</a>

                <br><br>
                <small>This link requires login and will be watermarked.</small>
                """,
                subtype="html"
            )

            fm = FastMail(conf)
            await fm.send_message(message)

            print("✅ Email sent to user + admin CC")

        except Exception as e:
            print("❌ Email send failed:", str(e))
        
    
    html_content = f"""
    <html>
        <head><meta charset="utf-8" /><title>Download</title></head>
        <body style="font-family: Arial; text-align: center; margin-top: 80px; font-size: 20px; color: #222;">
            <h2 style="font-size: 32px; color: #28a745;">✅ Payment Successful!</h2>

            <p style="font-size: 20px; max-width: 700px; margin: 20px auto;">
                Your file <b>{document["filename"]}</b> is ready and email with download link is sent to your mailbox/spambox<br>
                If the file is not downloaded automatically, please click the button below or right click with save as<br>
                If the download is fail because of big size pdf file, please go to mailbox/spambox and lick on link directly two times or more to download<br>
                Any support is need, please reply email to muabanraovat1982@gmail.com
            </p>

            <a href="{download_url}" 
               style="background: #0070f3; 
                      color: white; 
                      padding: 14px 28px; 
                      border-radius: 8px; 
                      text-decoration: none; 
                      font-size: 22px; 
                      display: inline-block;
                      margin-top: 20px;">
               ⬇️ Download File
            </a>

            <script>
                setTimeout(() => {{
                    window.location = "{download_url}";
                }}, 1000);
            </script>
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



def apply_watermark_to_pdf(original_pdf_bytes, username, email):

    print("🔥 Watermark for user:", username, email)

    pdf_data = original_pdf_bytes.read()
    doc = fitz.open(stream=pdf_data, filetype="pdf")

    wm_text = f"{username} | {email} | DO NOT SHARE"

    fontname = "helv"
    fontsize = 18

    # 🔑 TÍNH CHIỀU DÀI TEXT
    text_width = fitz.get_text_length(
        wm_text,
        fontname=fontname,
        fontsize=fontsize
    )

    # 🔑 STEP PHỤ THUỘC TEXT
    x_step = int(text_width + 120)
    y_step = int(fontsize * 10)

    for page in doc:
        rect = page.rect

        # ✅ XOAY 45°
        matrix = fitz.Matrix(1, 1).prerotate(45)

        y_index = 0
        for y in range(-int(rect.height), int(rect.height * 1.5), y_step):
            x_offset = 0 if y_index % 2 == 0 else x_step // 2

            for x in range(
                -int(rect.width) + x_offset,
                int(rect.width * 1.5),
                x_step
            ):
                page.insert_text(
                    fitz.Point(x, y),
                    wm_text,
                    fontname=fontname,
                    fontsize=fontsize,
                    color=(0, 0, 0),
                    fill_opacity=0.12,
                    overlay=True,
                    morph=(fitz.Point(0, 0), matrix)
                )
            y_index += 1

    output = io.BytesIO()
    doc.save(
        output,
        encryption=fitz.PDF_ENCRYPT_AES_128,
        owner_pw="OWNER_SECRET_2025",
        permissions=(
            fitz.PDF_PERM_ACCESSIBILITY |
            fitz.PDF_PERM_FORM
        )
    )
    doc.close()

    output.seek(0)
    print("✅ Watermark PDF generated")

    return output



# 📥 Download file (check login + quyền)
@router.get("/secure-download/{file_id}")
def download_file(request: Request, file_id: int, db: Session = Depends(get_db)):
    # 🧩 Kiểm tra login
    user_id = request.session.get("user_id")
    print("🔥🔥🔥 KOYEB VERSION 2025-01-16 WATERMARK ACTIVE")
    if not user_id:
        raise HTTPException(status_code=401, detail="You must be logged in to download files.")

    # 🧩 Lấy document
    document = db.query(Document).filter(Document.id == file_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # 🧩 Kiểm tra quyền
    purchase = db.query(Purchase).filter(
        Purchase.user_id == user_id,
        Purchase.document_id == file_id
    ).first()

    user = db.query(User).filter(User.id == user_id).first()
    is_uploader = document.uploaded_by == user.username if user else False

    if not purchase and not is_uploader:
        raise HTTPException(status_code=403, detail="You do not have access to this file.")

    # 🧩 Tải PDF gốc từ Cloudflare R2
    #original_pdf = io.BytesIO()
    #try:
    #    s3.download_fileobj(R2_BUCKET, document.filepath, original_pdf)
    #except Exception as e:
    #    raise HTTPException(status_code=404, detail=f"File not found in R2: {str(e)}")
    #original_pdf.seek(0)


 # 🔥 ÉP STREAM → FULL BYTES (CỰC KỲ QUAN TRỌNG)
 #   tmp_buffer.seek(0)
 #   pdf_bytes = tmp_buffer.read()

 #   print("🔥 PDF size from R2:", len(pdf_bytes))

 #   if len(pdf_bytes) < 1000:
 #       raise HTTPException(status_code=500, detail="Downloaded PDF is invalid or empty")

 #   original_pdf = io.BytesIO(pdf_bytes)


    tmp_buffer = io.BytesIO()
    try:
        s3.download_fileobj(R2_BUCKET, document.filepath, tmp_buffer)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"File not found in R2: {str(e)}")

    tmp_buffer.seek(0)
    pdf_bytes = tmp_buffer.read()

    print("🔥 PDF size from R2:", len(pdf_bytes))

    if len(pdf_bytes) < 1000:
        raise HTTPException(status_code=500, detail="Downloaded PDF is invalid or empty")

    original_pdf = io.BytesIO(pdf_bytes)



    # 🧩 Áp watermark cá nhân
    print(f"🔥 Watermark user = {user.username} | {user.email}")


    watermarked_pdf = apply_watermark_to_pdf(
        original_pdf_bytes=original_pdf,
        username=user.username,
        email=user.email
    )

    # 🧩 Trả file PDF đã watermark
    #return StreamingResponse(
    #    watermarked_pdf,
    #    media_type="application/pdf",
    #    headers={"Content-Disposition": f'attachment; filename=\"{document.filename}\"'}
    #)

    return StreamingResponse(
        watermarked_pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{document.filename}"',
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        }
    )
