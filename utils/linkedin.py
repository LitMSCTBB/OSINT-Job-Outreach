import asyncio
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

# Setup the cache (can persist across runs)
cache = diskcache.Cache("data/linkedin_profiles")

def async_cache_on_person(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        person = args[0] if args else kwargs.get("person")
        if not person or "profile_link" not in person:
            raise ValueError("async_cache_on_person requires person dict with 'profile_link'")

        key_material = json.dumps({
            "name": person.get("name"),
            "link": person.get("profile_link")
        }, sort_keys=True)

        cache_key = hashlib.sha256(key_material.encode()).hexdigest()
        if cache_key in cache:
            return cache[cache_key]

        result = await func(*args, **kwargs)
        cache[cache_key] = result
        return result

    return wrapper

# for testing manually person needs to be a dict with name, profile_link

@async_cache_on_person
async def scrape_linkedin_profile(person: dict, method: str = "manual-bu", browser=None, page=None):
    if method == "manual-bu":
        details = {}
        # get the about section first
        url = f"{person['profile_link']}"

        try:


            await page.goto(url)
            await page.wait_for_timeout(3000)
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")

            # get the about section, will be the first one under this selector
            about_section = soup.select_one('div.inline-show-more-text--is-collapsed span[aria-hidden="true"]')
            if about_section:
                details["about"] = about_section.get_text(strip=True, separator='\n')

            for section in ["experience", "education"]:
                url = f"{person['profile_link']}/details/{section}"
                print(person['name'], section, url)
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
            insights = "\n".join([f"{section}:\n{text}" for section, text in details.items()])

            print(f"{person['name']} done:\n{insights}")
            return insights
        
        except Exception as e:
            print(f"Error scraping linkedin profile for {person['name']}: {e}")
            return ""

    elif method == "browser-use":
        if not browser:
            raise ValueError("browser object is required for browser-use method")
        agent = Agent(
            llm=ChatOpenAI(model="gpt-4o"),
            initial_actions=[{ 'open_tab': { 'url': person['profile_link'] } }],
            task=f'''Extract all profile information you can about {person['name']}
            Make sure to collect EVERYTHING you can about About, Experience, Education (and activities they did in high school!!), as well as just the links of the posts. Scroll and click show all buttons if needed.
            Ignore any other elements on the linkedin page as they can be a distraction.
            Pace yourself to not get rate limited. Also be as smart as possible, preferring to click buttons, extract html, and then process info from the html.
            Return the information in a structured format.''',
            browser=browser,
            save_conversation_path=f"data/linkedin_bu_conversations_{person['name']}.txt",
            max_actions_per_step=10
        )
        summary = await agent.run()
        return summary.final_result()

    elif method == "manual":
        if not page:
            raise ValueError("page object is required for manual method")
        await page.goto(person["profile_link"])
        await page.wait_for_timeout(3000)
        profile_html = await page.content()
        profile_soup = BeautifulSoup(profile_html, "html.parser")

        title_el = profile_soup.find("div", class_="text-body-medium")
        title_txt = title_el.text.strip() if title_el else ""

        about_section = profile_soup.find("section", id="about")
        about_txt = about_section.get_text(strip=True).replace("About", "") if about_section else ""

        exp_section = profile_soup.find("section", id="experience")
        exp_txt = exp_section.get_text(strip=True).replace("Experience", "") if exp_section else ""

        return "\n".join([title_txt, about_txt, exp_txt])

    elif method == "proxycurl":
        headers = {
            "Authorization": f"Bearer {os.getenv('PROXYCURL_API_KEY')}"
        }

        params = {
            "url": person["profile_link"],
            "use_cache": "if-present",
            "fallback_to_cache": "true"
        }

        response = requests.get(
            "https://nubela.co/proxycurl/api/v2/linkedin",
            params=params,
            headers=headers
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

# run from root python -m utils.linkedin
if __name__ == "__main__":
    from browser_use import Browser, BrowserConfig
    from dotenv import load_dotenv
    load_dotenv()
    async def main():
        browser_config = BrowserConfig(
            cdp_url="http://localhost:9222",  # 👈 connect to existing Chrome
            browser_class="chromium",         # required
            headless=False,
            keep_alive=True,                  # optional but helpful if reusing
            extra_chromium_args=["--window-size=1920,1080", "--window-position=0,0"],
        )

        browser = Browser(
            config=browser_config
        )
        
        b = await browser.get_playwright_browser()
        context = b.contexts[0]
        page = await context.new_page()

        res = await scrape_linkedin_profile(
            {
                "name": "Jesse Zhang",
                "profile_link": "https://www.linkedin.com/in/thejessezhang/",
            },
            "manual-bu",
            page=page
        )

    asyncio.run(main())
