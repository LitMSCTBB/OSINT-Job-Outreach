import re
from typing import Any, Dict
from urllib.parse import urlparse
from dotenv import load_dotenv

from CONSTANTS import CHATGPT_URL, DEEP_DIVE

load_dotenv()
import argparse
import asyncio
from tools.linkedin import scrape_linkedin_profile
from tools.twitter import scrape_twitter_posts, send_twitter_dm
from tools.osint import crawl_person
from backend.tools.email import craft_messages, find_all_permutation_emails, send_gmail
from utils.person_cache import get_person_data, make_auto_caching
from browser_use import Browser, BrowserConfig

from utils.prompter import prompt
import json
import tempfile
import os
import subprocess

browser_config = BrowserConfig(
    cdp_url="http://localhost:9222",  # connect to existing Chrome
    browser_class="chromium",
    headless=False,
    keep_alive=True,
    extra_chromium_args=["--window-size=1920,1080", "--window-position=0,0"],
    new_context_config=BrowserConfig(keep_alive=True),
)

browser = Browser(config=browser_config)
global b, context

PARSE_PROMPT = """Extract information from the following text into a JSON object with these fields:
- name: The person's full name
- linkedin: Their LinkedIn URL (if found)
- twitter_handle: Their twitter / X url (if found)
- domain: Company domain (if found)
- notes: Any other relevant information for personalizing outreach

If any field is not found, omit it from the JSON.

Example output:
{
    "name": "Jesse Zhang",
    "linkedin": "https://www.linkedin.com/in/thejessezhang/",
    "twitter_handle": "https://x.com/thejessezhang",
    "domain": "decagon.ai",
    "notes": "Met at MIT hackathon\nWorking on LLM agents\nPreviously at Google Brain"
}

Text to parse:
"""


async def parse_text_with_gpt(text: str) -> Dict[str, Any]:
    """Use GPT to parse text into structured info"""
    response = await prompt(
        system_prompt=PARSE_PROMPT,
        user_prompt=text,
        model="gpt-3.5-turbo",
        provider="openai",
    )

    try:
        return json.loads(response)
    except json.JSONDecodeError as e:
        print(f"Error parsing GPT response: {e}")
        print("GPT response:", response)
        return {}


async def edit_message(message: str) -> str:
    """Open message in system editor for quick editing"""
    # Create a temporary file with the message
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tf:
        tf.write(message)
        temp_path = tf.name

    try:
        # Open with default editor (uses EDITOR env var, defaults to notepad on Windows)
        editor = os.environ.get("EDITOR", "notepad" if os.name == "nt" else "nano")
        subprocess.call([editor, temp_path])

        # Read back the edited content
        with open(temp_path, "r") as f:
            edited_message = f.read()

        return edited_message

    finally:
        # Clean up temp file
        os.unlink(temp_path)

async def scrape_person(person_data):
    # merge with loaded person
    try:
        person = get_person_data(person_data["domain"], person_data["name"])
        person["profile_link"] = person_data["linkedin"]
        person["twitter_handle"] = person_data["twitter_handle"]
        person["domain"] = person_data["domain"]
        person["notes"] = person_data["notes"]
    except Exception as e:
        print(f"Error loading person from cache, making new person: {e}")
        person = make_auto_caching(
            person_data["domain"],
            {
                "name": person_data["name"],
                "profile_link": person_data["linkedin"],
                "twitter_handle": person_data["twitter_handle"],
                "domain": person_data["domain"],
                "notes": person_data["notes"],
            },
        )

    # Scrape LinkedIn
    page = await context.new_page()
    await scrape_linkedin_profile(person, page=page)

    person["insights"] = f"LinkedIn: {person['linkedin_summary']}"

    if DEEP_DIVE:
        # updates person["insights"], person["internet_content"], and person["twitter_summary"] with internet content
        await crawl_person(browser, context, person["domain"], person)
    else:
        # no deep dive but still scrape twitter if twitter handle was provided
        if person["twitter_handle"] != None:
            page = await context.new_page()
            person["twitter_summary"] = await scrape_twitter_posts(
                person["twitter_handle"], browser=browser, page=page
            )
            await page.close()
    
    return person

async def generate_email(person):
    # Compile insights
    if not person["email"]:

        # Draft message using ChatGPT (or switch to API if you want)
        page = await context.new_page()
        await page.goto(CHATGPT_URL)
        await craft_messages(
            browser,
            context,
            page,
            person["domain"],
            person,
            notes=person["notes"],
        )
        await page.close()

    # Optional: email permutations
    person["possible_emails"] = await find_all_permutation_emails(
        person["name"], person["domain"]
    )

    # print("\n📧 POSSIBLE EMAILS:")
    # print("\n".join(person["possible_emails"]))

    # After generating email
    print("\nGenerated Email:")
    print("-" * 40)
    print(person["email"])

async def send_messages(person):
    gmail_page = await context.new_page()
    await gmail_page.goto("https://mail.google.com/mail/u/0/#inbox")
    for email in person["possible_emails"]:
        try:
            await send_gmail(email, person["email"], gmail_page)
        except Exception as e:
            print(f"Error sending email {email}: {e}")
    await gmail_page.close()

    if person.get("twitter_handle") and person.get("twitter_message"):
        twitter_page = await context.new_page()
        await twitter_page.goto("https://x.com/messages")
        try:
            await send_twitter_dm(
                person["twitter_handle"], person["twitter_message"], twitter_page
            )
        except Exception as e:
            print(f"Error sending Twitter DM to {person['twitter_handle']}: {e}")
        await twitter_page.close()

    return "email and "


async def run(person_data):
    # this first func returns the person obj
    person = await scrape_person(person_data)

    await generate_email(person)
    
    # Ask if user wants to edit
    edit = input("\nEdit message? (y/N): ").lower().strip()
    if edit == "y":
        person["email2"] = await edit_message(person["email"])
        person["twitter_message"] = person["email2"]
        print("\nUpdated Email:")
        print("-" * 40)
        print(person["email2"])

    await send_messages(person)

async def main():
    global b, context
    b = await browser.get_playwright_browser()
    context = b.contexts[0]

    parser = argparse.ArgumentParser(
        description="Parse person info using GPT",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    # Main text input
    parser.add_argument(
        "--text",
        required=True,
        help="""Paste any text about the person. Will try to extract:
- Name
- LinkedIn URL
- Twitter handle
- Company domain
- Other notes

Example:
Jesse Zhang
https://linkedin.com/in/jesse
@jesseontwitter
Works at decagon.ai
Met at hackathon, interested in LLMs""",
    )

    # Optional override arguments
    parser.add_argument("--name", help="Override extracted name")
    parser.add_argument("--linkedin", help="Override LinkedIn URL")
    parser.add_argument("--twitter_handle", help="Override Twitter handle")
    parser.add_argument("--domain", help="Override company domain")
    parser.add_argument("--notes", help="Additional notes to append")

    args = parser.parse_args()

    # Parse info using GPT first
    person_data = await parse_text_with_gpt(args.text)

    # Apply overrides if provided
    if args.name:
        person_data["name"] = args.name
    if args.linkedin:
        person_data["linkedin"] = args.linkedin
    if args.twitter_handle:
        person_data["twitter_handle"] = args.twitter_handle.lstrip("@")
    if args.domain:
        person_data["domain"] = args.domain
    if args.notes:
        existing_notes = person_data.get("notes", "")
        person_data["notes"] = (
            f"{existing_notes}\n\n{args.notes}" if existing_notes else args.notes
        )

    # Print extracted info
    print("\nExtracted Information:")
    print(json.dumps(person_data, indent=2))

    # Continue with processing...
    await run(person_data)

# if running this file standalone on the backend
if __name__ == "__main__":
    asyncio.run(main())
