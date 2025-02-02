import json
from groq import Groq
import httpx
import logging
import asyncio
from datetime import datetime
from fastapi import FastAPI, HTTPException, Query, WebSocket, Depends, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.requests import Request
from langchain_text_splitters import RecursiveCharacterTextSplitter
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

from app.api.search.utills import call_embedding_api, stream_chat_ollama, clean_whitespace, stream_summarize 
from app.database import get_db
from app.models import APIKey, RequestLog, User, UserPlan

router = APIRouter()



SEARXNG_API_URL = "http://localhost:8888/search"

@router.websocket("/ws/chat")
async def websocket_search(websocket: WebSocket, db: Session = Depends(get_db)):
    await websocket.accept()
    print("WebSocket connection established.")
    try:
        # Receive the input from WebSocket
        data = await websocket.receive_json()
        query = data.get("query")
        api_key = data.get("api_key")
        model = data.get("model", "llama-3.1-70b-versatile")

       # Check if API key exists and is active
        db_key = db.query(APIKey).filter(APIKey.key == api_key, APIKey.status == True).first()
        if not db_key:
            raise HTTPException(status_code=403, detail="Invalid or disabled API key")

        # Retrieve the user associated with the API key
        user = db.query(User).filter(User.id == db_key.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User associated with the API key not found")

        # Check if the user has the role 'customer'
        if user.role == "customer":
            # Count the number of queries made with this API key
            user_plan = db.query(UserPlan).filter(UserPlan.user_id == user.id).first()
            
            if not user_plan or user_plan.remain_request <= 0 or user_plan.plan_expire_date < datetime.now():
                if user_plan and user_plan.plan_expire_date < datetime.now():
                    user_plan.plan_status = False
                    user_plan.remain_request = 0
                    user_plan.total_request = 0
                    db.commit()
                return {"message": "You have exhausted your request quota or your plan has expired. Please upgrade your plan or wait for it to reset."}
            
            user_plan.remain_request -= 1
            db.commit()

        #Log the Request
        log = RequestLog(api_key=api_key, query=query, model_id=None)
        db.add(log)
        db.commit()

        # Perform the search or summarization
        # This example assumes you want to stream content from a summarization model
        summary_generator = stream_chat_ollama(query, model)
        print("WebSocket call ollama.")
        async for partial_summary in summary_generator:
            print("WebSocket partial_summary: ", partial_summary)
            await websocket.send_json({"partial_summary": partial_summary})

        await websocket.send_json({"message": "Summary complete"})
        await websocket.close()

    except Exception as e:
        await websocket.send_json({"error": str(e)})
        await websocket.close()

@router.websocket("/ws/search-summary")
async def searchsummary1( 
    websocket: WebSocket = WebSocket,
    db: Session = Depends(get_db)):
    try:
        await websocket.accept()
        print("WebSocket connection established.")
        # Receive the input from WebSocket
        data = await websocket.receive_json()
        query = data.get("query")
        categories = data.get("categories","general")
        engines = data.get("engines","all")
        api_key = data.get("api_key")
        # model = data.get("model", "llama-3.1-70b-versatile")
        # Increase timeout to 10 seconds
        timeout = httpx.Timeout(100.0, read=100.0)
        params = {
            "q": query,
            "categories": categories if categories else "general",  # Default to "general" if None
            "engines": engines if engines else "all",  # Default to "all" if None
            "format":"json",  # Use provided format, default to "json"
        }

        #Check if API key exists and is active
        db_key = db.query(APIKey).filter(APIKey.key == api_key, APIKey.status == True).first()
        if not db_key:
            raise HTTPException(status_code=403, detail="Invalid or disabled API key")
        
        #Retrieve the user associated with the API key
        user = db.query(User).filter(User.id == db_key.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User associated with the API key not found")

        # Check if the user has the role 'customer'
        if user.role == "customer":
            # Count the number of queries made with this API key
            user_plan = db.query(UserPlan).filter(UserPlan.user_id == user.id).first()
            
            if not user_plan or user_plan.remain_request <= 0 or user_plan.plan_expire_date < datetime.now():
                if user_plan and user_plan.plan_expire_date < datetime.now():
                    user_plan.plan_status = False
                    user_plan.remain_request = 0
                    user_plan.total_request = 0
                    db.commit()
                return {"message": "You have exhausted your request quota or your plan has expired. Please upgrade your plan or wait for it to reset."}
            
            user_plan.remain_request -= 1
            db.commit()

        #Log the Request
        log = RequestLog(api_key=api_key, query=query, model_id=None)
        db.add(log)
        db.commit()
        
        # Making an asynchronous GET request to SearxNG API with the search query and increased timeout
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(SEARXNG_API_URL, params=params)

        # Log response status and content
        logging.debug(f"Response Status Code: {response.status_code}")
        logging.debug(f"Response Content: {response.text}")

        

        
        # Check if the SearxNG API request was successful
        if response.status_code == 200:
            search_results = response.json().get("results", [])  # Extract the results from the response

            # Initialize list to store cleaned content
            all_cleaned_content = []

            # Process only the top 7 search results
            for result in search_results[:6]:
                url = result.get('url')  # Adjust key based on your actual response structure
                #logging.debug(f"Fetching {url}:")
                
                loader = WebBaseLoader(url)
                try:
                    # Load and clean the content from the URL
                    docs = loader.load()
                    page_content = docs[0].page_content
                    #print(page_content)
                    cleaned_content = clean_whitespace(page_content)
                    #print(cleaned_content)
                    all_cleaned_content.append(cleaned_content)
                except httpx.RequestError as e:
                    logging.error(f"Request Error while fetching {url}: {e}")
                    continue
                except Exception as e:
                    logging.error(f"Error while processing {url}: {e}")
                    continue 

            # Combine all cleaned content and summarize it
            combined_content = "\n\n---\n\n".join(all_cleaned_content)
            summary_generator = stream_summarize(combined_content,query)
            print("WebSocket call ollama.")
            async for partial_summary in summary_generator:
                print("WebSocket partial_summary: ", partial_summary)
                await websocket.send_json({"partial_summary": partial_summary})

            await websocket.send_json({"message": "Summary complete"})
            await websocket.close()

        

        else:
            raise HTTPException(status_code=response.status_code, detail=f"Error fetching data from SearxNG API: {response.text}")

    except httpx.RequestError as exc:
        # Handle any request errors, such as connection issues
        raise HTTPException(status_code=500, detail=f"An error occurred while requesting SearxNG API: {exc}")
    except Exception as e:
            await websocket.send_json({"error": str(e)})
            await websocket.close()


@router.get("/chat")
async def pg_chat(query: str, api_key: str, model: str = "llama-3.1-70b-versatile", db: Session = Depends(get_db)):
    
    # db_key = db.query(APIKey).filter(APIKey.key == api_key, APIKey.status == True).first()
    # if not db_key:
    #     raise HTTPException(status_code=403, detail="Invalid or disabled API key")

    # # Retrieve the user associated with the API key
    # user = db.query(User).filter(User.id == db_key.user_id).first()
    # if not user:
    #     raise HTTPException(status_code=404, detail="User associated with the API key not found")

    # # Check if the user has the role 'customer'
    # if user.role == "customer":
    #     # Count the number of queries made with this API key
    #     query_count = db.query(func.count(RequestLog.id)).filter(RequestLog.api_key == api_key).scalar()

    #     # Check if the number of queries exceeds the free quota
    #     if query_count >= 10:
    #         return {"message": "Your free quota is over. Please make a payment to continue using the service."}

    # # Log the request
    # log = RequestLog(api_key=api_key, query=query,model_id=model)
    # db.add(log)
    # db.commit()

    
    #chat_answer = chat_ollama(query,model)
    try:
        # Call the chat_ollama function
        responses = []
        async for response in stream_chat_ollama(query, model):
            responses.append(response)

        # Combine all responses into a single output
        chat_answer = " ".join(responses)  # Adjust based on how you want to format the output
        return {"answer": chat_answer}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    
  

# Search function using the API key
@router.get("/search-summary")
async def searchsummary1(
    q: str = Query(..., description="The search query"),
    categories: str = Query("general", description="The categories to filter by"),
    engines: str = Query("all", description="The engines to use"),
):
    try:
        # Increase timeout to 100 seconds
        timeout = httpx.Timeout(100.0, read=100.0)
        params = {
            "q": q,
            "categories": categories if categories else "general",
            "engines": engines if engines else "all",
            "format":  "json",
        }
        # Making an asynchronous GET request to SearxNG API
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(SEARXNG_API_URL, params=params)

        # Log response status and content
        logging.debug(f"Response Status Code: {response.status_code}")
        logging.debug(f"Response Content: {response.text}")

        if response.status_code == 200:
            search_results = response.json().get("results", [])
            all_cleaned_content = []

            for result in search_results[:10]:
                url = result.get('url')
                loader = WebBaseLoader(url)
                try:
                    docs = loader.load()
                    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
                    splits = text_splitter.split_documents(docs)
                    all_cleaned_content.extend(split.page_content for split in splits)  # Gather only content
                except httpx.RequestError as e:
                    logging.error(f"Request Error while fetching {url}: {e}")
                    continue
                except Exception as e:
                    logging.error(f"Error while processing {url}: {e}")
                    continue
            # Step 1: Embed all collected content in batches
            embeddings = await call_embedding_api(all_cleaned_content)

            summary = []
            async for part in stream_summarize(all_cleaned_content, q):
                summary.append(part)
            
            # Combine all parts of the summary
            summary = " ".join(summary)
            return {"summary": summary}

        else:
            raise HTTPException(status_code=response.status_code, detail=f"Error fetching data from SearxNG API: {response.text}")

    except httpx.RequestError as exc:
        raise HTTPException(status_code=500, detail=f"An error occurred while requesting SearxNG API: {exc}")


@router.get("/searchsummarymultiple")
async def searchsummary2(
    q: str = Query(..., description="The search query"),
    categories: str = Query("general", description="The categories to filter by"),
    engines: str = Query("all", description="The engines to use"),
    format: str = Query("json", description="The response format")
):
    try:
        # Increase timeout to 100 seconds
        timeout = httpx.Timeout(100.0, read=100.0)
        params = {
            "q": q,
            "categories": categories if categories else "general",  # Default to "general" if None
            "engines": engines if engines else "all",  # Default to "all" if None
            "format": format if format else "json",  # Use provided format, default to "json"
        }
        # Making an asynchronous GET request to SearxNG API with the search query and increased timeout
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(SEARXNG_API_URL, params=params)

        # Log response status and content
        logging.debug(f"Response Status Code: {response.status_code}")
        logging.debug(f"Response Content: {response.text}")

        # Check if the SearxNG API request was successful
        if response.status_code == 200:
            search_results = response.json().get("results", [])  # Extract the results from the response

            # Initialize list to store cleaned content
            url_contents = []

            # Process the top results
            for result in search_results[:5]:
                url = result.get('url')  # Adjust key based on your actual response structure
                title = result.get("title")
    
                loader = WebBaseLoader(url)
                try:
                    # Load and clean the content from the URL
                    docs = loader.load()
                    page_content = docs[0].page_content
                    cleaned_content = clean_whitespace(page_content)

                    # Store the cleaned content with URL
                    url_contents.append({"url": url,"title": title, "content": cleaned_content})
                except httpx.RequestError as e:
                    logging.error(f"Request Error while fetching {url}: {e}")
                    continue
                except Exception as e:
                    logging.error(f"Error while processing {url}: {e}")
                    continue 

            # Summarize content for each URL
            summaries = []
            for item in url_contents:
                title = item["title"]
                url = item["url"]
                content = item["content"]
                summary =  stream_summarize(content, q)
                summaries.append({"url": url,"title": title, "summary": summary})

            return {"summaries": summaries}  # Return the summarized content

        else:
            raise HTTPException(status_code=response.status_code, detail=f"Error fetching data from SearxNG API: {response.text}")

    except httpx.RequestError as exc:
        # Handle any request errors, such as connection issues
        raise HTTPException(status_code=500, detail=f"An error occurred while requesting SearxNG API: {exc}")
    
# Configure logging to output debug information
logging.basicConfig(level=logging.DEBUG)


@router.get("/playground-json")
def search_pg_json(query: str, 
                   api_key: str,
                   categories: str = Query("general", description="The categories to filter by"),
                    engines: str = Query("all", description="The engines to use"),
                    format: str = Query("json", description="The response format"),
                    count: int = Query(10, description="Number of results to return"),
                   db: Session = Depends(get_db)
                   ):
    # Check if API key exists and is active
    db_key = db.query(APIKey).filter(APIKey.key == api_key, APIKey.status == True).first()
    if not db_key:
        raise HTTPException(status_code=403, detail="Invalid or disabled API key")

    # Retrieve the user associated with the API key
    user = db.query(User).filter(User.id == db_key.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User associated with the API key not found")

    # Check if the user has the role 'customer'
    if user.role == "customer":
        # Count the number of queries made with this API key
        user_plan = db.query(UserPlan).filter(UserPlan.user_id == user.id).first()
        
        if not user_plan or user_plan.remain_request <= 0 or user_plan.plan_expire_date < datetime.now():
            if user_plan and user_plan.plan_expire_date < datetime.now():
                user_plan.plan_status = False
                user_plan.remain_request = 0
                user_plan.total_request = 0
                db.commit()
            return {"message": "You have exhausted your request quota or your plan has expired. Please upgrade your plan or wait for it to reset."}
        # Count the number of queries made with this API key
        # query_count = db.query(func.count(RequestLog.id)).filter(RequestLog.api_key == api_key).scalar()

        # # Check if the number of queries exceeds the free quota
        # if query_count >= 10:
        #     return {"message": "Your free quota is over. Please make a payment to continue using the service."}

        # Decrement the remaining requests by 1
        user_plan.remain_request -= 1
        db.commit()

    # Log the request
    log = RequestLog(api_key=api_key, query=query,model_id=None)
    db.add(log)
    db.commit()

    try:
        # Define the query parameters
        params = {
            "q": query,
            "categories": categories if categories else "general",  # Default to "general" if None
            "engines": engines if engines else "all",  # Default to "all" if None
            "count": count,
            "format": format if format else "json",  # Use provided format, default to "json"
        }

        # Send the GET request to SearxNG
        response = requests.get(SEARXNG_API_URL, params=params, timeout=1000)

        # Log response status and content
        logging.debug(f"Response Status Code: {response.status_code}")
        logging.debug(f"Response Content: {response.text}")

        # Check if the SearxNG API request was successful
        if response.status_code == 200:
            response_data = response.json()

            # Extract relevant result fields
            results = [
                {
                    "url": result.get("url"),
                    "title": result.get("title"),
                    "content": result.get("content"),
                    "thumbnail": result.get("thumbnail"),
                    "category":result.get("category"),
                    "score":result.get("score"),
                }
                for result in response_data.get("results", [])
            ]
            limited_results = results[:count]
            # Return the filtered results and the number of results
            return {
                "followup": response_data.get("suggestions"),
                "category":response_data.get("category"),
                "query": query,
                "number_of_results": len(limited_results),
                "results": limited_results
            }
        else:
            raise HTTPException(status_code=response.status_code, detail=f"Error fetching data from Search API: {response.text}")

    except requests.RequestException as exc:
        # Handle any request errors, such as connection issues
        raise HTTPException(status_code=500, detail=f"An error occurred while requesting SearxNG API: {exc}")

@router.get("/searchjson-test")
def searchjson(
    q: str = Query(..., description="The search query"),
    categories: str = Query("general", description="The categories to filter by"),
    engines: str = Query("all", description="The engines to use"),
    format: str = Query("json", description="The response format")
):
    try:
        # Define the query parameters
        params = {
            "q": q,
            "categories": categories if categories else "general",  # Default to "general" if None
            "engines": engines if engines else "all",  # Default to "all" if None
            "format": format if format else "json",  # Use provided format, default to "json"
        }

        # Send the GET request to SearxNG
        response = requests.get(SEARXNG_API_URL, params=params, timeout=1000)

        # Log response status and content
        logging.debug(f"Response Status Code: {response.status_code}")
        logging.debug(f"Response Content: {response.text}")

        # Check if the SearxNG API request was successful
        if response.status_code == 200:
            return response.json()  # Return the JSON response from SearxNG API
        else:
            raise HTTPException(status_code=response.status_code, detail=f"Error fetching data from SearxNG API: {response.text}")

    except requests.RequestException as exc:
        # Handle any request errors, such as connection issues
        raise HTTPException(status_code=500, detail=f"An error occurred while requesting SearxNG API: {exc}")























def clean_whitespace(text):
    text = re.sub(r'\s+', ' ', text)
    return text.strip()




