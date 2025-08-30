from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse, FileResponse, HTMLResponse
import paypalrestsdk
from app.database import get_document_by_id  # Tuỳ bạn tổ chức project
import os



# Cấu hình PayPal
paypalrestsdk.configure({
    "mode": "sandbox",  # hoặc "live"
    "client_id": "Aeub7AkBsgWgmX0SvYEh4XIbqpfRWlTF2QYzneH16RvgwSR_rZMO9NQ6I-vUkTMdhJV3GfEFFX9Qj-L7",
    "client_secret": "ELjY_MLftZa0jlYsFqdj5fxJxs1znLFgKDKV9Il0EBtzmSjK7WB7KSmKooM1nYaU5Y0YhXWgEl1Njmuz"
})

router = APIRouter()


@router.get("/pay/{file_id}")
def create_payment(file_id: int, request: Request):
    document = get_document_by_id(file_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    payment = paypalrestsdk.Payment({
        "intent": "sale",
        "payer": {
            "payment_method": "paypal"
        },
        "redirect_urls": {
            "return_url": f"http://localhost:8000/payment/success?file_id={file_id}",
            "cancel_url": "http://localhost:8000/payment/cancel"
        },
        "transactions": [{
            "item_list": {
                "items": [{
                    "name": document["filename"],
                    "sku": f"file-{file_id}",
                    "price": "5.00",
                    "currency": "USD",
                    "quantity": 1
                }]
            },
            "amount": {
                "total": "5.00",
                "currency": "USD"
            },
            "description": f"Access full document #{file_id}"
        }]
    })

    if payment.create():
        for link in payment.links:
            if link.rel == "approval_url":
                return RedirectResponse(url=link.href)
        raise HTTPException(status_code=500, detail="Approval URL not found.")
    else:
        print("Payment error:", payment.error)
        raise HTTPException(status_code=500, detail="Payment creation failed.")

"""
@router.get("/payment/success")
def payment_success(request: Request, paymentId: str, PayerID: str, file_id: int):
    payment = paypalrestsdk.Payment.find(paymentId)

    if payment.execute({"payer_id": PayerID}):
        if "paid_files" not in request.session:
            request.session["paid_files"] = []
        if file_id not in request.session["paid_files"]:
            request.session["paid_files"].append(file_id)

        return RedirectResponse(url=f"/download/{file_id}")
    else:
        raise HTTPException(status_code=400, detail="Payment failed.")

"""

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
       filepath = document["filepath"]
       if not os.path.exists(filepath):
           raise HTTPException(status_code=404, detail="File does not exist")
       # Trả về trang HTML có JS: tự tải file và quay lại trang chủ
       html_content = f"""
       <html>
           <head>
               <meta charset="utf-8" />
               <title>Download</title>
           </head>
           <body>
               <p>Đang tải file <b>{document["filename"]}</b>...</p>
               <script>
                   // Tạo link ẩn để tải file
                   var a = document.createElement("a");
                   a.href = "/download/{file_id}";
                   a.download = "{document["filename"]}";
                   document.body.appendChild(a);
                   a.click();
                   // Sau 2 giây quay về trang chủ
                   setTimeout(function() {{
                        window.location.href = "{previous_url}";
                    }}, 2000);
               </script>
           </body>
       </html>
       """
       return HTMLResponse(content=html_content)
   else:
       raise HTTPException(status_code=400, detail="Payment failed.")

@router.get("/payment/cancel")
def payment_cancel(request: Request):
    # Ghi flash message vào session
    request.session["flash"] = "❌ Bạn đã hủy thanh toán."
    referer = request.headers.get("referer", "/")  # Nếu không có thì fallback về "/"
    return RedirectResponse(url=referer, status_code=303)



@router.get("/download/{file_id}")
def download_file(request: Request, file_id: int):
    paid_files = request.session.get("paid_files", [])
    if file_id not in paid_files:
        raise HTTPException(status_code=403, detail="You must pay to download this file.")

    document = get_document_by_id(file_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    filepath = document["filepath"]
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File does not exist")

    return FileResponse(path=filepath, filename=document["filename"], media_type='application/pdf')
