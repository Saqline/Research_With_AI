from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse,JSONResponse
import stripe
from fastapi.templating import Jinja2Templates
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Access the variables
STRIPE_API_KEY = os.getenv("STRIPE_API_KEY")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")
stripe.api_key = STRIPE_API_KEY
templates = Jinja2Templates(directory="app/api/payment/templates")

router = APIRouter()

@router.get("/")
async def home():
    return "working..."

# @router.get("/", response_class=HTMLResponse)
# async def home(request: Request):
#     return templates.TemplateResponse("index.html", {"request": request, "publishable_key": STRIPE_PUBLISHABLE_KEY})

@router.post("/create-checkout-session-stripe")
async def create_checkout_session(request: Request):
    try:
        data = await request.json()
        product_id = data.get("product_id")  # Get the product ID from the request
        if not product_id:
            return JSONResponse({"error": "No product ID provided"}, status_code=400)

        # Fetch the prices associated with the product ID
        prices = stripe.Price.list(product=product_id)
        if not prices or len(prices.data) == 0:
            return JSONResponse({"error": "No prices found for the product"}, status_code=400)

        # Use the first price available for the product (you can add logic to select specific prices)
        price_id = prices.data[0].id

        line_items = [{
            "price": price_id,
            "quantity": 1
        }]

        success_url = "https://searchapi.sobjanta.ai/deshboard?session_id={CHECKOUT_SESSION_ID}" 
        cancel_url=f'https://searchapi.sobjanta.ai/cancel'
        #success_url = "http://localhost:5173/deshboard?session_id={CHECKOUT_SESSION_ID}" 
        #cancel_url=f'http://localhost:5173/cancel'
     



        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='subscription',
            success_url=success_url,  
            cancel_url=cancel_url,
        )

        return JSONResponse({"sessionId": checkout_session['id']})

    except stripe.error.InvalidRequestError as e:
        return JSONResponse({"error": str(e)}, status_code=400)

    except Exception as e:
        return JSONResponse({"error": "An unexpected error occurred."}, status_code=500)

from fastapi import Query

@router.get("/success")
async def success(session_id: str = Query(...)):
    try:
        # Retrieve the checkout session using the session_id
        checkout_session = stripe.checkout.Session.retrieve(session_id)

        # Check if the session has an invoice
        invoice_id = checkout_session.get('invoice')

        if invoice_id:
            # Retrieve the invoice details
            invoice = stripe.Invoice.retrieve(invoice_id)
            invoice_number = invoice.get('number', 'N/A')

            # Return the invoice number as JSON
            return JSONResponse({"message": "Payment successful", "invoice_number": invoice_number})
        else:
            return JSONResponse({"message": "No invoice associated with this session."})

    except Exception as e:
        return JSONResponse({"error": "Could not retrieve invoice information."}, status_code=500)



@router.get("/cancel")
async def cancel(request: Request):
    return  {"Failure": f"request: {dict(request)}"}