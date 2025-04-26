import asyncio
import re
import time
import diskcache
import hashlib
import json
from functools import wraps
from bs4 import BeautifulSoup
from browser_use import Agent
from langchain_openai import ChatOpenAI
import os
import requests

from utils.person_cache import make_auto_caching
from utils.prompter import prompt

# Setup the cache (can persist across runs)
cache = diskcache.Cache("data/linkedin_profiles")


def async_cache_on_person(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        person = args[0] if args else kwargs.get("person")
        if not person or "profile_link" not in person:
            raise ValueError(
                "async_cache_on_person requires person dict with 'profile_link'"
            )

        key_material = json.dumps(
            {"name": person.get("name"), "link": person.get("profile_link")},
            sort_keys=True,
        )

        cache_key = hashlib.sha256(key_material.encode()).hexdigest()
        if cache_key in cache:
            return cache[cache_key]

        result = await func(*args, **kwargs)
        cache[cache_key] = result
        return result

    return wrapper


# for testing manually person needs to be a dict with name, profile_link


@async_cache_on_person
async def scrape_linkedin_profile(
    person: dict, method: str = "playwright", browser=None, page=None
):
    if method == "playwright":
        details = {}
        # get the about section first
        url = f"{person['profile_link']}"

        try:

            await page.goto(url)
            await page.wait_for_timeout(3000)
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")

            # get the about section, will be the first one under this selector
            about_section = soup.select_one(
                'div.inline-show-more-text--is-collapsed span[aria-hidden="true"]'
            )
            if about_section:
                details["about"] = about_section.get_text(strip=True, separator="\n")

            for section in ["experience", "education"]:
                url = f"{person['profile_link']}/details/{section}"
                print(person["name"], section, url)
                await page.goto(url)
                await page.wait_for_timeout(3000)
                # extract from div.pvs-list__container
                html = await page.content()
                soup = BeautifulSoup(html, "html.parser")

                # extract from div.pvs-list__container
                container = soup.find("div", class_="pvs-list__container")

                if container:
                    details[section] = container.get_text(strip=True)
                else:
                    details[section] = ""

            # combined everything into one string
            insights = "\n".join(
                [f"{section}:\n{text}" for section, text in details.items()]
            )

            print(f"{person['name']} done:\n{insights}")
            person["linkedin_summary"] = insights

        except Exception as e:
            print(f"Error scraping linkedin profile for {person['name']}: {e}")
            return ""

    elif method == "proxycurl":
        headers = {"Authorization": f"Bearer {os.getenv('PROXYCURL_API_KEY')}"}

        params = {
            "url": person["profile_link"],
            "use_cache": "if-present",
            "fallback_to_cache": "true",
        }

        response = requests.get(
            "https://nubela.co/proxycurl/api/v2/linkedin",
            params=params,
            headers=headers,
        )

        if response.status_code != 200:
            print("Proxycurl error:", response.text)
            return {}

        data = response.json()

        return {
            "name": data.get("full_name"),
            "title": data.get("occupation"),
            "about": data.get("summary"),
            "experience": "\n".join(
                f"{item.get('title', '')} at {item.get('company', {}).get('name', '')}"
                for item in (data.get("experiences", []) or [])
            ),
            "location": data.get("location"),
            "linkedin": person["profile_link"],
        }


async def get_employees(context, company_url: str, domain: str):
    """
    Get the people associated with a company.
    """
    page = await context.new_page()
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


async def scrape_company_employees(context, company_url: str, domain: str):
    """
    1) For each keyword in JOB_KEYWORDS, go to the "people" tab with that keyword.
    2) Scroll & parse the page to find up to MAX_PEOPLE total.
    3) Open each profile to gather 'about' and 'experience', then filter via LLM.
    """

    profiles = await get_employees(context, company_url, domain)

    # scrape linkedin profiles as a first step
    page = await context.new_page()
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

    # When creating new profiles, wrap them in AutoCachingPerson
    profiles = [make_auto_caching(domain, profile) for profile in profiles]

    return profiles


# run from root python -m utils.linkedin
if __name__ == "__main__":
    from browser_use import Browser, BrowserConfig
    from dotenv import load_dotenv

    load_dotenv()

    async def main():
        browser_config = BrowserConfig(
            cdp_url="http://localhost:9222",  # 👈 connect to existing Chrome
            browser_class="chromium",  # required
            headless=False,
            keep_alive=True,  # optional but helpful if reusing
            extra_chromium_args=["--window-size=1920,1080", "--window-position=0,0"],
        )

        browser = Browser(config=browser_config)

        b = await browser.get_playwright_browser()
        context = b.contexts[0]
        page = await context.new_page()

        res = await scrape_linkedin_profile(
            {
                "name": "Jesse Zhang",
                "profile_link": "https://www.linkedin.com/in/thejessezhang/",
            },
            "manual-bu",
            page=page,
        )

    asyncio.run(main())
