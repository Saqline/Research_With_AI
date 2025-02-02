from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from oauthlib.oauth2 import WebApplicationClient
import requests
import uuid
import os


router = APIRouter()


GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI')

google_client = WebApplicationClient(GOOGLE_CLIENT_ID)

GOOGLE_AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v1/userinfo"

@router.get("/login")
async def google_login(request: Request):
    state = str(uuid.uuid4())
    request.session["state"] = state

    authorization_url = google_client.prepare_request_uri(
        GOOGLE_AUTHORIZATION_URL,
        redirect_uri=GOOGLE_REDIRECT_URI,
        scope=["profile", "email"],
        state=state,
    )
    return RedirectResponse(authorization_url)

@router.get("/callback")
async def google_callback(request: Request):
    code = request.query_params.get('code')
    state = request.query_params.get('state')

    if not code or not state:
        raise HTTPException(status_code=400, detail="Invalid callback request")

    if state != request.session.get("state"):
        raise HTTPException(status_code=400, detail="Invalid state")

    try:
        token_url, headers, body = google_client.prepare_token_request(
            GOOGLE_TOKEN_URL,
            authorization_response=str(request.url),
            redirect_url=GOOGLE_REDIRECT_URI,
            code=code
        )
        token_response = requests.post(token_url, headers=headers, data=body, auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET))
        token_response.raise_for_status()
        token_data = google_client.parse_request_body_response(token_response.text)

        userinfo_endpoint, headers, _ = google_client.add_token(GOOGLE_USERINFO_URL)
        userinfo_response = requests.get(userinfo_endpoint, headers=headers)
        userinfo_response.raise_for_status()
        user_info = userinfo_response.json()
        print(user_info) 
        # Notify WebSocket clients about the login success
        
            
        return user_info
        #return {"message": "User logged in successfully", "user_info": user_info}
    except requests.exceptions.RequestException:
        raise HTTPException(status_code=500, detail="Error fetching user info")
