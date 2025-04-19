import asyncio
import json
import os
import re
import pandas as pd
from playwright.async_api import Page

from utils.CONSTANTS import RESUME_PATH
from utils.notifications import notify_user

def generate_permutations(name, domain):
    first, last = name.lower().split()
    f, l = first[0], last[0]

    formats = [
        f"{first}",
        f"{last}",
        f"{first}{last}",
        f"{first}.{last}",
        f"{f}{last}",
        f"{f}.{last}",
        f"{first}{l}",
        f"{first}.{l}",
        f"{last}{first}",
        f"{last}.{first}",
    ]

    return [f"{fmt}@{domain}" for fmt in formats]


# ---------------------------- Simplified Finder ----------------------------


async def find_all_permutation_emails(name, domain):
    print(f"📇 Generating permutations for {name} at {domain}...")
    return generate_permutations(name, domain)


async def send_gmail(email_address, email_data, page: Page = None):
    try:

        if type(email_data) == str:
            email_subject = email_data.split("\n")[0]
            email_body = "\n".join(email_data.split("\n")[1:]).strip()
        else:
            email_subject = email_data["subject"]
            email_body = email_data["body"]

        # Click Compose
        await page.click("div.T-I.T-I-KE.L3")
        # await page.wait_for_selector("div.AD", timeout=10_000)
        await page.wait_for_timeout(1000)

        # Fill in recipient
        await page.fill("input[aria-label='To recipients']", email_address)

        # Fill subject
        await page.fill("input[name=subjectbox]", email_subject)

        # Fill body
        body = page.locator("div[aria-label='Message Body']")
        await body.click()
        await body.press("Control+Home")
        await body.fill(email_body)

        # Wait to ensure everything is filled
        await page.wait_for_timeout(500)

        # Find the hidden file input and upload
        # attachment_button = page.locator("div.a1")
        # await attachment_button.click()
        # attach_files = page.locator("div[command='+untrackedFile']")
        # await attach_files.click()

        input = page.locator("input[type='file']").nth(2)
        await input.set_input_files(RESUME_PATH)

        # Wait a bit for the upload to complete
        await page.wait_for_timeout(2000)

        # Click send
        print("Clicking send button...")
        await page.click("div.dC")
        print(f"Email sent to {email_address}")
        return True
    except Exception as e:
        print(f"Error sending email to {email_address}: {e}")
        notify_user(
            "Error Sending Email",
            f"Error sending email to {email_address}: {e}",
            duration=5,
        )
        return False


# Example usage
# asyncio.run(send_gmail_emails(df, sent_emails, subject, template))


# ---------------------------- CLI Test ----------------------------

if __name__ == "__main__":
    name = "Jesse Zhang"
    domain = "decagon.ai"

    emails = asyncio.run(find_all_permutation_emails(name, domain))
    print("\n📧 Final Emails to Send:")
    for email in emails:
        print("-", email)

# ---------------------------- Legacy Agent Code (Commented Out) ----------------------------

"""
from browser_use import Browser, BrowserConfig, Agent
from langchain_openai import ChatOpenAI

EMAIL_FINDING_SITES = [
    "https://hunter.io/find",
    "https://prospeo.io/",
    "https://cultivatedculture.com/mailscoop/",
    "https://apollo.io/",
    "https://findthatlead.com/",
    "https://snov.io/",
    "https://clearbit.com/",
    "https://experte.com/email-finder"
]

async def try_find_email(browser, site_url, name, company, domain):
    agent = Agent(llm=ChatOpenAI(model="gpt-4o"),
                  browser=browser,
                  save_conversation_path=f"data/email_finder_conversations_{name}.txt",
                  initial_actions=[{ 'open_tab': { 'url': site_url } }],
                  task=f"The tab with the url {site_url} is open. Use the site's engine to find the email of {name} at {company} ({domain}).")
    email_candidates = (await agent.run()).final_result()
    return extract_emails(email_candidates)
"""
