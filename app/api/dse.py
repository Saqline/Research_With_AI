import json
from groq import Groq
import httpx
import logging
import asyncio
from datetime import datetime
from fastapi import FastAPI, HTTPException, Query, WebSocket, Depends, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.requests import Request
from pydantic import BaseModel
from typing import List, Dict
import re
import requests
from requests.exceptions import SSLError
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import sessionmaker, Session, relationship
from langchain_community.utilities import SearxSearchWrapper
from langchain_community.document_loaders import WebBaseLoader

from app.database import get_db
from app.models import APIKey, RequestLog, User, UserPlan

router = APIRouter()



###not used
def get_current_date_and_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
# Initialize Groq client with direct API key
api_key = "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"
client = Groq(api_key=api_key)
#SEARXNG_API_URL = "https://searsobjanta-gkd0dyewhyaug0as.eastus-01.azurewebsites.net/search"
SEARXNG_API_URL = "http://36.50.40.36:8888/search"

DSE_WEBSITES = [
    "https://www.dsebd.org",
    "https://www.amarstock.com",
    "https://www.dse.com.bd",
    "https://dsemonitor.com",
    "https://lankabd.com",
    "https://stocknow.com.bd",
    "https://tradingeconomics.com/bangladesh/stock-market"
    # "https://www.investing.com/indices/bd-dhaka-stock-exchange",
    
    # Add other reliable sources as necessary
]

@router.websocket("/ws/dse-updates")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time DSE updates.
    """
    await websocket.accept()
    try:
        timeout = httpx.Timeout(100.0, read=100.0)  # Set timeout to 100 seconds

        async with httpx.AsyncClient(timeout=timeout) as client:
            for website in DSE_WEBSITES:
                try:
                    # Initialize WebBaseLoader with the correct parameters
                    loader = WebBaseLoader()  # Initialize without url

                    # Load content from the URL directly
                    response = await client.get(website)
                    page_content = response.text

                    # Clean and process the content
                    cleaned_content = clean_whitespace(page_content)

                    # Summarize content
                    summary = summarize_content_dse(cleaned_content)
                    
                    # Send summary to client
                    await websocket.send_json({
                        "url": website,
                        "summary": summary
                    })

                except Exception as e:
                    logging.error(f"Error while loading {website}: {e}")
                    continue

                await asyncio.sleep(1)  # Adding delay to simulate real-time streaming

    except WebSocketDisconnect:
        logging.info("Client disconnected from WebSocket")
    except Exception as e:
        logging.error(f"Error during WebSocket communication: {e}")
    finally:
        await websocket.close()


# @router.get("/getlatestdseupdates")
# async def get_latest_dse_updates():
#     try:
#         # Increase timeout to 100 seconds
#         timeout = httpx.Timeout(100.0, read=100.0)

#         # Store data from all sources
#         url_contents = []

#         async with httpx.AsyncClient(timeout=timeout) as client:
#             for website in DSE_WEBSITES:
#                 try:
#                     # Use WebBaseLoader to load content from the URL
#                     loader = WebBaseLoader(website)
#                     docs = loader.load()

#                     # Clean and process the content
#                     page_content = docs[0].page_content
#                     cleaned_content = clean_whitespace(page_content)

#                     # Store the cleaned content with URL and title
#                     url_contents.append({
#                         "url": website,
#                         "content": cleaned_content
#                     })

#                 except httpx.RequestError as e:
#                     logging.error(f"Request Error for {website}: {e}")
#                     continue
#                 except Exception as e:
#                     logging.error(f"Error while loading {website}: {e}")
#                     continue

#         # Summarize content for each website
#         summaries = []
#         for item in url_contents:
#             url = item["url"]
#             content = item["content"]
#             summary = summarize_content_dse(content)
#             summaries.append({"url": url, "summary": summary})

#         return {"summaries": summaries}  # Return the summarized content

#     except httpx.RequestError as exc:
#         # Handle any request errors
#         raise HTTPException(status_code=500, detail=f"An error occurred while fetching data: {exc}")



def summarize_content_dse(content: str) -> str:
    try:
        chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": f"Please note that the current date and time is: {get_current_date_and_time}. I will provide a summary and analysis of the main points and update data of Dhaka Stock Exchange as an expert."
            },
            {
                "role": "user",
                "content": f"Please summarize the content with 3 line and top will be date of that contents . The content is: {content}"
            }
        ],
        model="llama-3.1-70b-versatile",
)
        return chat_completion.choices[0].message.content
    except Exception as e:
        print(f"An error occurred: {e}")
        return ''


def clean_whitespace(text):
    text = re.sub(r'\s+', ' ', text)
    return text.strip()
