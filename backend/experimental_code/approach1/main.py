# Explanation:
# It's cheaper to have the LLM gather just the profile links (small prompt usage),
# and then use normal Playwright actions (no prompt usage) to open each link.
# This eliminates the overhead of LLM-driven multi-tab opening.
# Below is an example code approach.

import os
import time
import re
import json
import asyncio
from bs4 import BeautifulSoup
from browser_use import Agent, Browser, BrowserConfig, Controller
from langchain_openai import ChatOpenAI
from openai import AsyncOpenAI
from playwright.async_api import Page
from dotenv import load_dotenv
import requests
from utils.email_utils import find_all_permutation_emails, send_gmail
from utils.osint import fetch_internet_content
from utils.CONSTANTS import (
    CHATGPT_URL,
    COLD_EMAIL_PROMPTS,
    CHOOSE_PROFILE_PROMPT,
    get_transmission_ready,
    get_process,
    SIGNATURE,
)

import json
from functools import wraps

from utils.file_handlers import write_step_output, wait_until_ready
from utils.linkedin import scrape_linkedin_profile
from utils.person_cache import cache_person_data, get_all_cached_persons
from utils.prompter import prompt
from utils.twitter import scrape_twitter_posts, send_twitter_dm
from utils.notifications import notify_user

load_dotenv()
openai = AsyncOpenAI()

browser_config = BrowserConfig(
    cdp_url="http://localhost:9222",  # 👈 connect to existing Chrome
    browser_class="chromium",  # required
    headless=False,
    keep_alive=True,  # optional but helpful if reusing
    extra_chromium_args=["--window-size=1920,1080", "--window-position=0,0"],
    new_context_config=BrowserConfig(keep_alive=True),
)

browser = Browser(config=browser_config)

global b, context


async def scrape_company_people(company_url: str, domain: str):
    """
    1) For each keyword in JOB_KEYWORDS, go to the "people" tab with that keyword.
    2) Scroll & parse the page to find up to MAX_PEOPLE total.
    3) Open each profile to gather 'about' and 'experience', then filter via LLM.
    """

    page: Page = await context.new_page()

    profiles = []

    for keyword in ["cofounder", "MIT"]:
        url_with_keyword = f"{company_url}/people?keywords={keyword}"
        await page.goto(url_with_keyword)
        await page.wait_for_timeout(3000)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
        await page.wait_for_timeout(2000)

        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")

        profile_links = soup.find_all(
            "a",
            href=lambda h: h and "linkedin.com/in/" in h,
            attrs={"aria-label": re.compile(r"^View .+ profile$")},
        )

        for link in profile_links:
            href = link["href"]
            href = href.split("?")[0]
            name_div = link.find("div")
            name_text = (
                name_div.text.strip() if name_div and name_div.text.strip() else ""
            )
            if not name_text:
                aria = link.get("aria-label", "")
                name_text = aria.replace("View ", "").split("'")[0].strip()
            if not name_text or any(p["profile_link"] == href for p in profiles):
                continue
            profiles.append({"name": name_text, "profile_link": href})

    print([p["name"] for p in profiles])

    # scrape linkedin profiles as a first step
    for person in profiles:
        if not person.get("linkedin_summary"):
            linkedin = await scrape_linkedin_profile(person, page=page)
            # prettyify the linkedin summary probably with gpt
            linkedin = await prompt(
                system_prompt="Prettyify the following linkedin summary. Make it more readable and easier to understand. Keep it short, concise, don't need a ton of english, just the facts.",
                user_prompt=linkedin,
                model="gpt-3.5-turbo",
                provider="openai",
            )
            person["linkedin_summary"] = linkedin

        if not person.get("linkedin_relevant"):
            # quickly ascertain if this is a good person to email
            verdict = await prompt(
                system_prompt="Given this linkedin profile scraping, at the top output their likely role in the company in bold, followed by a summary of all the interesting things from the profile. Keep it short, concise, don't need a ton of english, just the facts.",
                user_prompt=f"{person['linkedin_summary']}",
                model="gpt-3.5-turbo",
                provider="openai",
            )
            person["linkedin_relevant"] = verdict

        # cache the person's data
        cache_person_data(domain, person)

    # choose the 4 most relevant profiles via LLM. order of preference is cofounders, mit, people i have stuff in common with, c suite, then finally technical leads
    choices = await prompt(
        system_prompt=CHOOSE_PROFILE_PROMPT,
        user_prompt="\n".join([p["linkedin_relevant"] for p in profiles]),
        model="gpt-3.5-turbo",
        provider="openai",
    )

    indices = [int(line) for line in choices.split("\n") if line.strip()]

    return profiles, indices


async def scrape_internet_content(person: dict, domain: str):
    # scrape internet content as a second step
    if not person.get("internet_content"):
        print(f"Scraping internet content for {person['name']} of {domain}")
        person["internet_content"] = fetch_internet_content(
            f"{person['name']} of {domain}"
        )

    # this indicates that the field hasn't been set at all, NOT that there's no twitter handle - that's when twitter_handle == "NONE"
    if not person.get("twitter_handle"):
        # extract twitter handle from internet_content with language model
        print(f"Finding twitter handle for {person['name']} of {domain}")
        twitter_handle = re.search(r"https://x\.com/(\w+)", person["internet_content"])
        if twitter_handle:
            twitter_handle = twitter_handle.group(1)
        else:
            twitter_handle = await prompt(
                system_prompt="Extract the twitter handle from the following text if you are confident that it's the right one: {internet_content}. The output should contain ONLY the handle in the format @handle, or NONE if no handle is found.",
                user_prompt=person["internet_content"],
                model="gpt-3.5-turbo",
                provider="openai",
            )

        person["twitter_handle"] = twitter_handle

        if not twitter_handle == "NONE":
            print(f"Scraping twitter posts for {person['name']} of {domain}")
            page: Page = await context.new_page()
            twitter_summary = await scrape_twitter_posts(
                twitter_handle, browser=browser, page=page
            )

            person["twitter_summary"] = twitter_summary
        else:
            print(f"No twitter handle found for {person['name']} of {domain}")

    insights = f"LinkedIn Summary: {person['linkedin_summary']}\nInternet Content: {person['internet_content']}"
    if person.get("twitter_summary"):
        insights += f"\nTwitter Summary: {person['twitter_summary']}"
    person["insights"] = insights


async def craft_messages(
    person: dict,
    domain: str,
    method="playwright-gpt",
    regen=False,
    agent: Agent = None,
    page: Page = None,
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
                f"Write a cold email to {person['name']} of {domain} to land an internship. Here's some information about them:\n{person['insights']}"
            )
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(20000)

            # get the inner text of the last element with selector article.text-token-text-primary
            email = await page.evaluate(
                """
                const elements = document.querySelectorAll("article.text-token-text-primary");
                let length = elements.length;
                elements[length - 1].innerText
            """
            )

            # ask gpt 3.5 to quickly extract just the subject and body
            email_content = await prompt(
                system_prompt=f"From this GPT response, extract just the email content with NO OTHER TEXT. The first line of output should be the subject (without the words Subject or anything) and afterwards should be the body. Replace whatever signature is in the email with the following: {SIGNATURE}",
                user_prompt=email,
                model="gpt-3.5-turbo",
                provider="openai",
            )

            person["email"] = email_content
            print("generated email", person["email"])

        if not person["twitter_handle"] == "NONE":
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
    elif method == "bu-gpt":
        print(f"Crafting email for {person['name']} of {domain} using bu-gpt")
        # agent.add_new_task(f"""TYPE INTO THE VISIBLE CHATBOX THE FOLLOWING:

        # \"Write a cold email to {person['name']} of {domain} to land an internship.\"

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


async def outreach(company_url: str, domain: str):
    """
    Main function to orchestrate the outreach process.
    """
    global b, context
    b = await browser.get_playwright_browser()
    context = b.contexts[0]

    # Initial notification that process has started
    notify_user(
        "Outreach Process Started",
        f"Starting outreach process for {domain}. Profiles will be scraped first.",
        duration=5,
    )

    # Get company-specific paths
    transmission_ready = get_transmission_ready(domain)
    process = get_process(domain)

    # update the current.json file to have the company domain
    with open("data/current.json", "w") as f:
        json.dump({"company": domain}, f, indent=2)

    if not os.path.exists(transmission_ready):
        os.makedirs(os.path.dirname(transmission_ready), exist_ok=True)

    # modify keys in ready.json if you want to skip certain steps
    transmission_obj = json.load(open(transmission_ready))
    transmission_obj["profiles_ready"] = True
    transmission_obj["chosen_indices_ready"] = True

    with open(transmission_ready, "w") as f:
        json.dump(transmission_obj, f, indent=2)

    # if the data has been saved before load it into the variable for now; the next if clause will actully recompute all_people depending on the process status flags (specifically chosen_indices_ready)
    all_people = []
    if transmission_obj["profiles_ready"]:
        print("Loading people data from cache")
        all_people = get_all_cached_persons(domain)
        if len(all_people) > 0:
            transmission_obj["profiles_ready"] = True

    # if user has already made choices load them, otherwise do the scraping again
    chosen_indices = None
    if transmission_obj["chosen_indices_ready"]:
        chosen_indices = json.load(open(process["user_choose_profiles"]["output_file"]))
        if not all_people:
            # Load from the initial scrape if cache is empty
            all_people = json.load(
                open(process["scrape_company_people"]["output_file"])
            )["profiles"]
            # Cache each person's data
            for person in all_people:
                cache_person_data(domain, person)
    else:
        all_people, indices = await scrape_company_people(company_url, domain)
        write_step_output(
            process["scrape_company_people"],
            {"profiles": all_people, "chosen_indices": indices},
        )
        # Cache each person's data
        for person in all_people:
            cache_person_data(domain, person)

    # Notify user to select profiles
    notify_user(
        "Profile Selection Required",
        f"Found {len(all_people)} profiles for {domain}. Please select the ones to contact in the UI.",
        duration=10,
    )

    # wait for the user's selection of profiles from the ui
    if not chosen_indices:
        chosen_indices = wait_until_ready(process["user_choose_profiles"])
    chosen_ppl = []

    if not transmission_obj["drafts_ready"]:
        # Notify that we're starting to draft emails
        notify_user(
            "Drafting Emails",
            f"Starting to draft emails for {len(chosen_indices)} selected profiles.",
            duration=5,
        )

        # iterate through the chosen profiles
        for ind in chosen_indices:
            person = all_people[ind]
            print(f"Processing {person['name']}")

            await scrape_internet_content(person, domain)
            cache_person_data(domain, person)

            gmail_page: Page = await context.new_page()
            await gmail_page.goto(CHATGPT_URL)
            await craft_messages(
                person, domain, method="playwright-gpt", regen=True, page=gmail_page
            )
            possible_emails = await find_all_permutation_emails(person["name"], domain)
            person["possible_emails"] = possible_emails

            chosen_ppl.append(person)

            # Update cache with the processed person data
            cache_person_data(domain, person)

        write_step_output(
            process["scrape_internet_content_and_craft_email"], chosen_ppl
        )

    # Notify user to review and revise emails
    notify_user(
        "Email Review Required",
        f"Emails have been drafted for {len(chosen_ppl)} profiles. Please review and revise them in the UI.",
        duration=10,
    )

    chosen_ppl_email_revisions = wait_until_ready(process["user_revisions"])
    for person in chosen_ppl_email_revisions:
        # cache the person's data based on the revisions
        cache_person_data(domain, person)

    # Notify that we're about to start sending emails
    notify_user(
        "Starting Email Sending",
        f"About to send emails to {len(chosen_ppl_email_revisions)} profiles. Please ensure Gmail is ready.",
        duration=5,
    )

    # send emails
    gmail_page: Page = await context.new_page()
    await gmail_page.goto("https://mail.google.com")
    twitter_page: Page = await context.new_page()
    await twitter_page.goto("https://x.com/messages")
    # Wait for Gmail to load
    print("Waiting for Gmail to load...")
    await gmail_page.wait_for_selector("div.T-I.T-I-KE.L3", timeout=300_000)
    print("Gmail loaded successfully!")

    for person in chosen_ppl_email_revisions:
        if not person.get("email_sent"):
            person["email_sent"] = []
            person["twitter_message_sent"] = False
        for email in person["possible_emails"]:
            if email in person["email_sent"]:
                print(f"Email already sent to {email}, skipping...")
                continue
            status = await send_gmail(email, person["email"], page=gmail_page)
            if status:
                print(f"Sent email to {person['name']}")
                person["email_sent"].append(email)
            await asyncio.sleep(2)

        # try twitter message as well
        if (
            person["twitter_handle"] != "NONE"
            and person["twitter_message"]
            and not person["twitter_message_sent"]
        ):
            try:
                # TBH for now we should just send the email message as a DM
                status = await send_twitter_dm(
                    person["twitter_handle"], person["email"], page=twitter_page
                )
                if status:
                    print(f"Sent twitter message to {person['twitter_handle']}")
                    person["twitter_message_sent"] = True
                    await asyncio.sleep(2)
            except Exception as e:
                print(
                    f"Error sending twitter message to {person['twitter_handle']}: {e}"
                )

        cache_person_data(domain, person)

    # Final completion notification
    notify_user(
        "Outreach Complete",
        f"All outreach completed for {domain}:\n- {len(chosen_ppl_email_revisions)} profiles contacted\n- Emails and DMs sent successfully",
        duration=10,
    )


if __name__ == "__main__":

    async def main():
        # company_url = "https://www.linkedin.com/company/decagon-ai"
        # domain = "decagon.ai"

        company_url = "https://www.linkedin.com/company/hebbia"
        domain = "hebbia.com"
        # update the current.json file to have the company domain
        with open("data/current.json", "w") as f:
            json.dump({"company": domain}, f, indent=2)

        await outreach(company_url, domain)

    asyncio.run(main())
