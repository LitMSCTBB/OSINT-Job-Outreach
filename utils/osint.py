import re
from llm_osint.tools.search import get_search_tool
from llm_osint.tools.read_link import get_read_link_tool
from llm_osint import knowledge_agent, web_agent, cache_utils, llm
from utils.CONSTANTS import MY_BACKGROUND, MY_VALUES, GATHER_PROMPT, ASK_PROMPT, SCRAPING_INSTRUCTIONS

from dotenv import load_dotenv

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