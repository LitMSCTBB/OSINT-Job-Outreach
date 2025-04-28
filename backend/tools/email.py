import asyncio
import json
import os
import re
from browser_use import Agent
from langchain_openai import ChatOpenAI
import pandas as pd
from playwright.async_api import Page

from CONSTANTS import COLD_EMAIL_PROMPTS, RESUME_PATH
from utils.notifications import notify_user
from utils.prompter import prompt

def generate_permutations(name, domain):
    first, last = name.lower().split()
    f, l = first[0], last[0]

    formats = [
        f"{first}",
        f"{last}",
        f"{first}{last}",
        f"{first}.{last}",
        f"{f}{last}",
        f"{f}.{last}"
    ]

    return [f"{fmt}@{domain}" for fmt in formats]


# ---------------------------- Simplified Finder ----------------------------


async def find_all_permutation_emails(name, domain):
    print(f"📇 Generating permutations for {name} at {domain}...")
    return generate_permutations(name, domain)


async def craft_messages(
    browser,
    context,
    page: Page,
    domain: str,
    person: dict,
    method="playwright-gpt",
    regen=False,
    notes=None,
):
    """
    Craft an email to the person.
    """
    # we'll split into 2 steps:
    # given my background and the person's insights, generate a list of 3-5 email subjects
    # then, for each subject, generate an email body

    print(f"Crafting messages for {person['name']} of {domain} using {method}")

    if method == "playwright-gpt":
        if not person.get("email") or regen:
            await page.wait_for_timeout(3000)
            # await page.click("p[data-placeholder='Ask anything']")
            try:
                await page.focus('div.ProseMirror[contenteditable="true"]')
            except Exception as e:
                print(
                    f"Error focusing on the email input; MOST LIKELY CHATGPT ISNT LOADING ON CHROME:\n{e}"
                )
                # notify here as well
                notify_user(
                    "ChatGPT Not Loading",
                    f"ChatGPT is not loading on chrome. Please check your chrome browser and try again. Error:\n{e}",
                    duration=5,
                )
            await page.keyboard.insert_text(
                f"Write a cold email to {person['name']} of {domain} to land an internship. Here's some information about them:\n{person['insights']}\n\nHere's some additional context about them that would be super cool to include in the email:\n{notes}"
            )
            await page.keyboard.press("Enter")
            # await page.wait_for_timeout(20000)
            await page.wait_for_selector(
                'button[aria-label="Edit in canvas"] >> visible=true'
            )

            # get the inner text of the last element with selector article.text-token-text-primary
            email = await page.evaluate(
                """
                    const elements = document.querySelectorAll("article.text-token-text-primary");
                    let length = elements.length;
                    elements[length - 1].innerText
                """
            )

            signature = """
    Best,SIGNATURE"""
    

            # ask gpt 3.5 to quickly extract just the subject and body
            email_content = await prompt(
                system_prompt=f"From this GPT response, extract just the email content with NO OTHER TEXT. The first line of output should be the subject (without the words Subject or anything) and afterwards should be the body. Replace whatever signature is in the email with the following: {signature}.",
                user_prompt=email,
                model="gpt-3.5-turbo",
                provider="openai",
            )

            person["email"] = email_content
            print("generated email", person["email"])

        if person.get("twitter_handle", "NONE") != "NONE":
            if not person.get("twitter_message") or regen:
                # do the same thing as above
                # await page.wait_for_timeout(3000)
                # # await page.click("p[data-placeholder='Ask anything']")
                # await page.focus('div.ProseMirror[contenteditable="true"]')
                # await page.keyboard.insert_text(f"Also draft a quick twitter DM of the same sentiment that I can write to them ({person['twitter_handle']}).")
                # await page.keyboard.press("Enter")
                # await page.wait_for_timeout(15000)

                # twitter_message = await page.evaluate("""
                #     const elements = document.querySelectorAll("article.text-token-text-primary");
                #     let length = elements.length;
                #     elements[length - 1].innerText;
                # """)

                # # ask gpt 3.5 to quickly extract just the twitter message
                # twitter_message = await prompt(
                #     system_prompt=f"From this GPT response, extract just the twitter message with NO OTHER TEXT. The first line of output should be the twitter message. Here's the twitter message: {twitter_message}",
                #     user_prompt=twitter_message,
                #     model="gpt-3.5-turbo",
                #     provider="openai"
                # )
                person["twitter_message"] = person["email"]
                print("generated twitter message", person["twitter_message"])

    if method == "gpt-api":
        if not person.get("email") or regen:
            # Step 1: Generate email subjects. assume output is a list of phrases, each on a new line.
            email_topics = await prompt(
                system_prompt=COLD_EMAIL_PROMPTS[0].format(
                    name=person["name"],
                    company=domain,
                    recipient_insights=person["insights"],
                ),
                user_prompt=person["insights"],
                model="gpt-3.5-turbo",
                provider="openai",
            )
            email_topics = email_topics.split("\n")
            print("generated email topics")

            # Step 2: Generate email bodies for each subject
            email = await prompt(
                user_prompt=COLD_EMAIL_PROMPTS[1].format(
                    recipient_insights=person["insights"], email_topics=email_topics
                ),
                model="gpt-4o",
                provider="openai",
            )

            person["email"] = email
            print("generated email")
        else:
            print(f"using cached email for {person['name']}")

        if not person["twitter_handle"] == "NONE":
            if not person.get("twitter_message") or regen:
                # also draft a twitter message
                twitter_message = await prompt(
                    user_prompt=COLD_EMAIL_PROMPTS[2].format(
                        email=person["email"]["body"]
                    ),
                    model="gpt-4o",
                    provider="openai",
                )
                person["twitter_message"] = twitter_message
                print("generated twitter message")
            else:
                print(f"using cached twitter message for {person['name']}")
    elif method == "bu-gpt":
        print(f"Crafting email for {person['name']} of {domain} using bu-gpt")
        # agent.add_new_task(f"""TYPE INTO THE VISIBLE CHATBOX THE FOLLOWING:

        # \"Write a cold email to {person['name']} of {self.domain} to land an internship.\"

        # Return the output when it is generated.""")
        agent = Agent(
            llm=ChatOpenAI(model="gpt-4o"),
            task=f"""On the tab with the ChatGPT conversation called \"Internship Seeking Cold Outreach\", click on the <p> element with data-placeholder="Ask anything" and type:
                            
                \"Write a cold email to {person['name']} of {domain} to land an internship. Here's some information about them: {person['insights']}\"
                
                Return the output when it is generated.""",
            browser=browser,
            max_actions_per_step=10,
        )
        agent.save_conversation_path = (
            f"data/email_bugpt_conversations_{person['name']}.txt"
        )
        result = (await agent.run()).final_result()
        person["email"] = result
        print("generated email")

        if not person["twitter_handle"] == "NONE":
            if not person.get("twitter_message") or regen:
                # also draft a twitter message
                agent.add_new_task(
                    f"""On the tab with the ChatGPT conversation called \"Internship Seeking Cold Outreach\", click on the <p> element with data-placeholder="Ask anything" and type:
                        
                        \"Also draft a quick twitter DM of the same sentiment that I can write to them ({person['name']}'s handle is {person['twitter_handle']}).\"
                        
                        Return the output when it is generated."""
                )
                result = (await agent.run()).final_result()
                person["twitter_message"] = result
                print("generated twitter message")


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
