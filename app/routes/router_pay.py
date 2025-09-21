from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse, StreamingResponse
import paypalrestsdk
from app.database import get_document_by_id
import boto3, io

# ==============================
# 🔧 Config PayPal
# ==============================
paypalrestsdk.configure({
    "mode": "sandbox",  # hoặc "live"
    "client_id": "Aeub7AkBsgWgmX0SvYEh4XIbqpfRWlTF2QYzneH16RvgwSR_rZMO9NQ6I-vUkTMdhJV3GfEFFX9Qj-L7",
    "client_secret": "ELjY_MLftZa0jlYsFqdj5fxJxs1znLFgKDKV9Il0EBtzmSjK7WB7KSmKooM1nYaU5Y0YhXWgEl1Njmuz"
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

    price = float(document.get("price", 19.99))  # fallback nếu chưa có giá
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
def payment_success(request: Request, paymentId: str, PayerID: str, file_id: int):
    payment = paypalrestsdk.Payment.find(paymentId)

    if payment.execute({"payer_id": PayerID}):
        if "paid_files" not in request.session:
            request.session["paid_files"] = []
        if file_id not in request.session["paid_files"]:
            request.session["paid_files"].append(file_id)

        document = get_document_by_id(file_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        base_url = str(request.base_url).rstrip("/")
        download_url = f"{base_url}/download/{file_id}"

        html_content = f"""
        <html>
            <head>
                <meta charset="utf-8" />
                <title>Download</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; background: #f9f9f9; }}
                    .box {{
                        background: #fff;
                        border: 1px solid #ddd;
                        border-radius: 8px;
                        padding: 20px;
                        max-width: 600px;
                        margin: auto;
                        text-align: center;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    }}
                    a.button {{
                        display: inline-block;
                        margin-top: 15px;
                        padding: 10px 20px;
                        background: #0070f3;
                        color: white;
                        border-radius: 6px;
                        text-decoration: none;
                    }}
                    a.button:hover {{ background: #0059c9; }}
                </style>
            </head>
            <body>
                <div class="box">
                    <h2>✅ Payment Successful!</h2>
                    <p>Your file <b>{document["filename"]}</b> is ready.</p>

                    <p><strong>We are starting your download automatically...</strong></p>
                    <p>If it does not start, click the button below or right-click and choose <i>“Save link as...”</i>.</p>

                    <a class="button" href="{download_url}" download="{document["filename"]}">⬇️ Download File</a>

                    <p style="margin-top:20px;">
                        <a href="{base_url}">⬅️ Back to Home</a>
                    </p>
                </div>

                <script>
                    // Try to auto-download after 1 second
                    setTimeout(function() {{
                        var a = document.createElement("a");
                        a.href = "{download_url}";
                        a.download = "{document["filename"]}";
                        document.body.appendChild(a);
                        a.click();
                    }}, 1000);
                </script>
            </body>
        </html>
        """
        return HTMLResponse(content=html_content)

    else:
        raise HTTPException(status_code=400, detail="Payment failed.")




# ❌ Thanh toán bị hủy
@router.get("/payment/cancel")
def payment_cancel(request: Request):
    request.session["flash"] = "❌ Bạn đã hủy thanh toán."
    base_url = str(request.base_url).rstrip("/")
    return RedirectResponse(url=base_url, status_code=303)


# 📥 Download file từ R2 (chỉ cho người đã trả tiền)
# 📥 Download file từ R2 (chỉ cho người đã trả tiền)
@router.get("/download/{file_id}")
def download_file(request: Request, file_id: int):
    paid_files = request.session.get("paid_files", [])
    if file_id not in paid_files:
        raise HTTPException(status_code=403, detail="You must pay to download this file.")

    document = get_document_by_id(file_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    file_obj = io.BytesIO()
    try:
        s3.download_fileobj(R2_BUCKET, document["r2_key"], file_obj)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"File not found in R2: {str(e)}")

    file_obj.seek(0)
    # Ép buộc tải file xuống (mọi trình duyệt)
    return StreamingResponse(
        file_obj,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{document["filename"]}"'}
    )



