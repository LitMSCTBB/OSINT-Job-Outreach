# Explanation:
# It's cheaper to have the LLM gather just the profile links (small prompt usage),
# and then use normal Playwright actions (no prompt usage) to open each link.
# This eliminates the overhead of LLM-driven multi-tab opening.
# Below is an example code approach.

import json
from dotenv import load_dotenv

load_dotenv()

import asyncio
from browser_use import Browser, BrowserConfig
from backend.experimental_code.approach2.task_manager import TaskManager
from backend.experimental_code.approach2.company_processor import CompanyProcessor

browser_config = BrowserConfig(
    cdp_url="http://localhost:9222",  # connect to existing Chrome
    browser_class="chromium",
    headless=False,
    keep_alive=True,
    extra_chromium_args=["--window-size=1920,1080", "--window-position=0,0"],
    new_context_config=BrowserConfig(keep_alive=True),
)

browser = Browser(config=browser_config)

# Example companies to process
COMPANIES = [
    {"url": "https://www.linkedin.com/company/decagon-ai", "domain": "decagon.ai"},
    {
        "url": "https://www.linkedin.com/company/boltohq/",
        "domain": "bolto.com",
    },
    # Add more companies here
]



async def process_company(processor: CompanyProcessor, company_url: str, domain: str):
    try:
        print(f"Starting outreach for {domain}...")
        success = await processor.outreach(company_url, domain)
        if success:
            print(f"Successfully completed outreach for {domain}")
        else:
            print(f"Failed to complete outreach for {domain}")
    except Exception as e:
        print(f"Error processing {domain}: {e}")


async def main():
    # Initialize browser

    # write companies to task status file
    with open("data/task_state.json", "w") as f:
        json.dump({"companies": COMPANIES}, f)

    try:
        # Initialize task manager
        async with TaskManager(browser) as task_manager:
            # Add all companies to the task manager
            for company in COMPANIES:
                await task_manager.add_company(company["url"], company["domain"], rerun_config={"messages": True})

            await task_manager.process_companies()

    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Cleanup
        if "browser" in locals():
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
