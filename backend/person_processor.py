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
from tools.email import craft_messages, find_all_permutation_emails, send_gmail
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
b = None
context = None

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
    # this logic handles partial args, like just name+linkedin, just name+domain, or just domain+linkedin
    page = await context.new_page()
    # Scrape LinkedIn first
    person = {}
    if person_data.get("linkedin"):
        person["profile_link"] = person_data.get("linkedin")
    if person_data.get("domain"):
        person["domain"] = person_data.get("domain")

    if person_data.get("name"):
        person["name"] = person_data.get("name")
    else:
        await scrape_linkedin_profile(person, page=page) # this part should just update the name internally

    # get existing person data and reset person obj if it exists
    person2 = get_person_data(person_data.get("domain"), person_data.get("name") or person.get("name"))
    if person2:
        person = person2
    else:
        person = make_auto_caching(person_data.get("domain"), person)

    if person.get("linkedin_summary") is None:
        await scrape_linkedin_profile(person, page=page)

    print(person)

    if person_data.get("twitter_handle"):
        person["twitter_handle"] = person_data.get("twitter_handle")
    if person_data.get("notes"):
        person["notes"] = person_data.get("notes")

    person["insights"] = f"LinkedIn: {person['linkedin_summary']}"

    if DEEP_DIVE:
        # updates person["insights"], person["internet_content"], and person["twitter_summary"] with internet content
        await crawl_person(browser, context, person["domain"], person)
    else:
        # no deep dive but still scrape twitter if twitter handle was provided
        if person.get("twitter_handle"):
            page = await context.new_page()
            person["twitter_summary"] = await scrape_twitter_posts(
                person["twitter_handle"], browser=browser, page=page
            )
            person["insights"] += f"\n\nTwitter: {person['twitter_summary']}"
            await page.close()

    return person


async def generate_email(person: dict):
    # Compile insights
    if person.get("email") is None:
        # Draft message using ChatGPT (or switch to API if you want)
        page = await context.new_page()
        await page.goto(CHATGPT_URL)
        await craft_messages(
            browser,
            context,
            page,
            person["domain"],
            person,
            notes=person.get("notes", ""),
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

    if person.get("email_sent", None) is None:
        person["email_sent"] = []

    for email in person["possible_emails"]:
        try:
            if email not in person["email_sent"]:
                if person.get("email2"):
                    status = await send_gmail(email, person["email2"], gmail_page)
                    if status:
                        print(f"Email sent to {email}, should be appending to list")
                        person["email_sent"] = person["email_sent"] + [email]

        except Exception as e:
            print(f"Error sending email {email}: {e}")
    await gmail_page.close()

    if person.get("twitter_handle") and person.get("twitter_message"):
        twitter_page = await context.new_page()
        await twitter_page.goto("https://x.com/messages")

        person["twitter_message_sent"] = False
        try:
            if not person["twitter_message_sent"]:
                await send_twitter_dm(
                    person["twitter_handle"], person["twitter_message"], twitter_page
                )
                person["twitter_message_sent"] = True
        except Exception as e:
            print(f"Error sending Twitter DM to {person['twitter_handle']}: {e}")
        await twitter_page.close()


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


async def initialize_globals():
    global b, context
    b = await browser.get_playwright_browser()
    context = b.contexts[0]
    return b, context


async def main():
    await initialize_globals()

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
