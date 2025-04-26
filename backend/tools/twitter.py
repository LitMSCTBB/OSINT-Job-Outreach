from functools import wraps
from bs4 import BeautifulSoup
from browser_use import Agent
from langchain_openai import ChatOpenAI

from utils.notifications import notify_user


async def scrape_twitter_posts(handle: str, max_tweets=5, scroll_attempts=2, browser=None, page=None) -> list[str]:
    """
    Scrapes recent tweets from a Twitter user's profile using Playwright.

    Args:
        handle (str): Twitter handle without '@'
        page (playwright.async_api.Page): A Playwright page instance
        max_tweets (int): Max number of tweets to return
        scroll_attempts (int): Times to scroll down for more tweets

    Returns:
        List of tweet text strings
    """
    tweets = []

    # Normalize handle, including if they're urls
    if "x.com" in handle or "twitter.com" in handle:
        handle = handle.split(".com/")[1].split("/")[0]
    
    if "@" in handle:  
        handle = handle.replace("@", "")

    twitter_url = f"https://twitter.com/{handle}"
    await page.goto(twitter_url)
    await page.wait_for_timeout(3000)

    # Attempt to click the Follow button manually
    try:
        follow_text = await page.inner_text("div[data-testid='placementTracking']")
        if "Follow" in follow_text and not "Following" in follow_text:
            await page.click("div[data-testid='placementTracking']")
            print(f"✅ Followed @{handle}")
        elif "Following" in follow_text:
            print(f"❌ Already following @{handle}")
        else:
            print(f"⚠️ Could not find Follow button for @{handle}")
    except Exception as e:
        print(f"⚠️ Could not follow @{handle}: {e}")

    # Scroll to load more content if needed
    for _ in range(scroll_attempts):
        await page.mouse.wheel(0, 3000)
        await page.wait_for_timeout(1500)

    html = await page.content()
    soup = BeautifulSoup(html, "html.parser")

    tweet_blocks = soup.find_all("article", attrs={"role": "article"})

    for block in tweet_blocks:
        tweet_content = block.find_all(attrs={"data-testid": "tweetText"})
        tweet_text = " ".join([el.get_text(strip=True)
                              for el in tweet_content])

        if tweet_text:
            tweets.append(tweet_text)

        if len(tweets) >= max_tweets:
            break

    return tweets


async def send_twitter_dm(username_or_handle: str, message_text: str, page=None):
    try:
        # Normalize handle
        username = username_or_handle.lstrip("@")

        # Wait for DM modal
        await page.wait_for_selector(
            "div[role='dialog'] input[aria-label='Search people']", timeout=15000
        )

        # Search for the user
        search_input = page.locator("div[role='dialog'] input[aria-label='Search people']")
        await search_input.fill(username)
        await page.wait_for_timeout(1000)  # Let results populate

        # Click the first result (should be the user)
        await page.locator("div[role='listbox'] div[role='option']").first.click()
        await page.wait_for_timeout(1000)

        # Click "Next" to start chat
        await page.click("div[role='dialog'] div[role='button']:has-text('Next')")
        await page.wait_for_selector(
            "div[data-testid='dmComposerTextInput']", timeout=10000
        )

        # Type the message
        message_input = page.locator("div[data-testid='dmComposerTextInput']")
        await message_input.click()
        await message_input.type(message_text)

        # Click send (paper plane icon)
        await page.click("div[data-testid='dmComposerSendButton']")
        print(f"DM sent to @{username}")
    except Exception as e:
        print(f"Error sending DM to @{username}: {e}")
        notify_user(
            "Error Sending DM",
            f"Error sending DM to @{username}: {e}",
            duration=5,
        )