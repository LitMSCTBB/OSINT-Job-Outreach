from browser_use import Agent, Browser, BrowserConfig
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os
import asyncio
from utils.CONSTANTS import CHROME_PATH, CHROME_PROFILE_DIRECTORY, CHROME_USER_DATA_DIR, EDGE_PATH, EDGE_PROFILE_DIRECTORY, EDGE_USER_DATA_DIR
load_dotenv()

# chrome url
chrome_path = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
edge_path = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe"

# Configure the browser to connect to your Chrome instance
config1=BrowserConfig(
        chrome_instance_path=chrome_path,
        headless=False,
        extra_chromium_args=[
            "--remote-debugging-port=9222",  # enables CDP connection
            "--no-first-run",
            "--no-default-browser-check"
        ]
    )

config2 = BrowserConfig(
    cdp_url="http://localhost:9222",  # 👈 connect to existing Chrome
    browser_class="chromium",         # required
    headless=False,
    keep_alive=True,                  # optional but helpful if reusing
)

config3 = BrowserConfig(
    cdp_url="http://localhost:9223",  # 👈 connect to existing Edge
    browser_class="chromium",         # required
    headless=False,
    keep_alive=True,                  # optional but helpful if reusing
)

config4 = BrowserConfig(
    # user_data_dir=USER_DATA_DIR,
    # profile_directory=PROFILE_DIRECTORY,
    chrome_instance_path=CHROME_PATH,
    browser_class="chromium",
    extra_chromium_args=[f"--profile-directory={CHROME_PROFILE_DIRECTORY}", f"--user-data-dir={CHROME_USER_DATA_DIR}"]
)

browser = Browser(config=config2)

async def main():
    # Create agent with the specified browser and model
    agent = Agent(
        task="go to chatgpt.com and ask 'what is my most recent project?' and return the response",
        llm=ChatOpenAI(model="gpt-4o"),
        use_vision=True,
        browser=browser,
    )
    
    try:
        result = await agent.run()
        print(result)
    finally:
        await browser.close()

asyncio.run(main())
    
