import json
import os
import traceback
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from contextlib import asynccontextmanager
from tools.linkedin import get_employees
from utils.person_cache import get_person_data, get_records
from person_processor import (
    generate_email,
    initialize_globals,
    parse_text_with_gpt,
    scrape_person,
    send_messages,
)
from fastapi.middleware.cors import CORSMiddleware

class TextRequest(BaseModel):
    text: str

class PersonRequest(BaseModel):
    person: dict

class CompanyRequest(BaseModel):
    url: str
    domain: str

b, context = None, None

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Initializing browser...")
    try:
        # b = await browser.get_playwright_browser()
        # context = b.contexts[0]
        # print("Browser initialized successfully")
        global b, context
        b, context = await initialize_globals()
        yield  # This yields control back to FastAPI
    except Exception as e:
        print(f"Error initializing browser: {e}")
        raise
    finally:
        # Cleanup on shutdown
        print("Done")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/get-people-records")
async def get_people_records():
    return get_records()

@app.post("/api/generate-person-content")
async def generate_content(text: TextRequest):
    try:
        person_data = await parse_text_with_gpt(text.text)
        person = await scrape_person(person_data)
        await generate_email(person)
        return person
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/send-person")
async def send_person(person_request: PersonRequest):
    try:
        person = person_request.person
        person_record = get_person_data(person.get("domain", None), person.get("name", None))
        # update person_record with new data from person
        person_record.update(person)
        await send_messages(person_record)
        return person_record
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/get-company-people")
async def get_company_people(companyRequest: CompanyRequest):
    try:
        return await get_employees(context,companyRequest.url, companyRequest.domain)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# # run the damn app
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
