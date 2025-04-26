import re
from llm_osint.tools.search import get_search_tool
from llm_osint.tools.read_link import get_read_link_tool
from llm_osint import knowledge_agent, web_agent, cache_utils, llm
from CONSTANTS import MY_BACKGROUND, MY_VALUES, GATHER_PROMPT, ASK_PROMPT, SCRAPING_INSTRUCTIONS

from dotenv import load_dotenv

from tools.twitter import scrape_twitter_posts
from utils.prompter import prompt

load_dotenv()

def build_web_agent(name):
    
    tools = [get_search_tool(), get_read_link_tool(name=name, example_instructions=SCRAPING_INSTRUCTIONS)]
    return web_agent.build_web_agent(tools)


@cache_utils.cache_func
def fetch_internet_content(name, deep_dive_topics=1, deep_dive_rounds=1, retries=1) -> str:
    knowlege_chunks = knowledge_agent.run_knowledge_agent(
        GATHER_PROMPT.format(name=name),
        build_web_agent_func=lambda: build_web_agent(name),
        deep_dive_topics=deep_dive_topics,
        deep_dive_rounds=deep_dive_rounds,
        retries=retries,
        name=name,
    )
    return "\n\n".join(knowlege_chunks)


async def crawl_person(browser, context, domain, person: dict):
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
                system_prompt="Extract the twitter handle from the following text if you are confident that it's the right one. The output should contain ONLY the handle in the format @handle, or NONE if no handle is found.",
                user_prompt=person["internet_content"],
                model="gpt-3.5-turbo",
                provider="openai",
            )

        person["twitter_handle"] = twitter_handle

        if not twitter_handle == "NONE":
            print(f"Scraping twitter posts for {person['name']} of {domain}")
            page = await context.new_page()
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


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("name")
    parser.add_argument("--ask")
    args = parser.parse_args()

    fn = re.sub(r"[^\w]", "", args.name).lower() + ".txt"

    content = fetch_internet_content(args.name)
    with open(fn, "w") as f:
        f.write(content)

    if args.ask:
        model = llm.get_default_llm()
        print(model.call_as_llm(ASK_PROMPT.format(name=args.name, internet_content=content, question=args.ask)))

    # print(get_read_link_tool(name="Jesse Zhang")("https://www.linkedin.com/in/thejessezhang"))
