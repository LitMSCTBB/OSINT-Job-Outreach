from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from contextlib import asynccontextmanager
from tools.linkedin import get_employees
print("yooo")
from utils.person_cache import get_person_data
from person_processor import (
    generate_email,
    parse_text_with_gpt,
    browser,
    scrape_person,
    send_messages,
)
from browser_use import Browser

# Global variables to store browser instance
global b, context
b = None
context = None

# In-memory store for demo purposes (swap this with file/db logic)
people = {}


class Person(BaseModel):
    id: str
    name: str
    linkedin: str
    twitter: Optional[str] = None
    notes: Optional[str] = None
    domain: str
    email: Optional[str] = None
    status: str = "pending"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize browser on startup
    global b, context
    print("Initializing browser...")
    try:
        b = await browser.get_playwright_browser()
        context = b.contexts[0]
        print("Browser initialized successfully")
        yield  # This yields control back to FastAPI
    except Exception as e:
        print(f"Error initializing browser: {e}")
        raise
    finally:
        # Cleanup on shutdown
        print("Shutting down browser...")
        try:
            if context:
                await context.close()
            if b:
                await b.close()
            print("Browser shutdown complete")
        except Exception as e:
            print(f"Error during browser shutdown: {e}")


app = FastAPI(lifespan=lifespan)


@app.post("/api/generate-person-content")
async def generate_content(text: str):
    try:
        person_data = await parse_text_with_gpt(text)
        person = await scrape_person(person_data)
        await generate_email(person)
        return person
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/send-person")
async def send_person(person: dict):
    try:
        person = get_person_data(person["domain"], person["name"])
        status = await send_messages(person)
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/get-company-people")
async def get_company_people(company_url: str):
    try:
        return await get_employees(company_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
