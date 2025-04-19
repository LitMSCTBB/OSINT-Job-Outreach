CHROME_PATH = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
EDGE_PATH = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe"
CHROME_USER_DATA_DIR = (
    "C:\\Users\\Windows\\AppData\\Local\\Google\\Chrome\\User Data"  # mac@gmail.com
)
CHROME_PROFILE_DIRECTORY = "Default"
EDGE_USER_DATA_DIR = "C:\\Users\\Windows\\AppData\\Local\\Microsoft\\Edge\\User Data"
EDGE_PROFILE_DIRECTORY = "Profile 1"
RESUME_PATH = "C:\\Users\\Windows\\OneDrive\\Documents\\Safekeep\\Arnav_Adhikari_CV.pdf"
CHATGPT_URL = "https://chatgpt.com/g/g-68000029439481918c5cab9ddff22b40-internship-seeking-cold-outreach/c/68002cc7-fbac-8001-abe6-ef674f188dc4"



def get_transmission_ready(domain: str):
    return f"data/{domain}/transmissions/ready.json"

def get_transmissions_dir(domain: str):
    return f"data/{domain}/transmissions"


def get_process(domain: str):
    transmissions_dir = get_transmissions_dir(domain)
    return {
        "scrape_company_people": {
            "output_file": f"{transmissions_dir}/profiles.json",
            "done_key": "profiles_ready",
        },
        "user_choose_profiles": {
            "output_file": f"{transmissions_dir}/chosen_indices.json",
            "done_key": "chosen_indices_ready",
        },
        "scrape_internet_content_and_craft_email": {
            "output_file": f"{transmissions_dir}/drafts.json",
            "done_key": "drafts_ready",
        },
        "user_revisions": {
            "output_file": f"{transmissions_dir}/revisions.json",
            "done_key": "revisions_ready",
        },
    }


MY_BACKGROUND = """
I'm a 19-year-old EECS student @ MIT into AI, startups, VC, and PM. Currently freelancing.

My interests extend to fintech (payments, wealth management, AI analysts), robotics (collaboration and control), healthtech (LLM-aided care), and productivity tools. I'm a big proponent of "automating the mundane" and believe BS jobs should be automated away and cut out. By doing so I believe significantly more attention can be redirected towards the things that require human ingenuity.

Technical highlights:
- USAJMO winner, USACO Gold, MOP participant
- HackMIT 2024 winner
- Deep experience with AI infra, LLMs, motion planning, human-AI collaboration, control systems
- Published in IF 39+ journal
- Built predictive control systems, semantic database engines, and real-time robotic planning
- Automating my personal workflow with AI agents and extensive MCP user

Outside of tech:
- Tennis, basketball, football, rap, dude perfect, sunny vibes, outdoor stuff, Saturday Night Live, Brooklyn 99, sidequesting / exploring

Website: https://www.arnavadhikari.com
LinkedIn: https://www.linkedin.com/in/arnavwad
Email: arnavwad@mit.edu
"""

# Optional: high-level tags or values
MY_VALUES = [
    "building tools in AI, productivity, robotics, health, or education",
    "interested in reducing friction or automating away BS work",
    "deeply technical, especially with a background in algorithms, math, or systems thinking",
    "curious, ambitious, and has an appreciation for smart hustle",
    "likely to respond well to someone with the following background:",
]

CHOOSE_PROFILE_PROMPT = """
You are helping Arnav, a 19-year-old EECS student at MIT and cold email god, land a job via cold outreach. Choose the 4 most relevant people to email given their scraped linkedin summaries.

The order of preference is cofounders of the company, c suite, people from mit / harvard / stanford / berkeley, technical leads.

The output should be a list of 4 indices ONLY with no other text, each on a new line.
"""

example_emails = [
    """Arjun | Prev @ Stanford AIMI and now undergrad @ MIT CSAIL | Interested in Cartesia
Hi Arjun, I used to work with David Ouyang at AIMI! Funny how many SAIL people I've been emailing recently.

Also recently got in touch with a St Francis alum / MIT alum who was YC S24, now building quality voice datasets at Overeasy!!  You should definitely reach out!

Otherwise find your background super interesting. And I love Cartesia's approach with SSMs.

I learn fast and balance between building fast and being detail-oriented. Have some offers lined up, but would love to interview for a role at Cartesia, in person in the Bay!

Best,
    """,
    """MIT CSAIL DSG researcher / builder Interested in Etched!
Hi Chris, Saw you took MIT's 6.9430 which I found really funny. I'm planning to take it probably in junior year. Also have a couple of friends who did Promys! 

Currently have a final interview scheduled with Groq, but I find Etched super cool as well and admire the specialization for JUST transfomers angle.

So would love to explore opportunities for Etched in the Bay this summer.

P.S. My friends Arjun, Shaurya, Christina, Will G. and Will B. were actually at the Etched/Cognition/Mercor hackathon a couple weeks ago and got 7th place. Gave them emotional support as I couldn't be there in person, lol.
    """,
]

example_dms = [
    """Hi Elias,
Would love to work on hard human motion and speech problems. I've done motion planning with 7D manipulators and state computation research previously, as well as extensive applied AI (CV, RL, and more) to domains like healthcare and the environment.
I learn fast and love to build. http://github.com/litmsctbb http://arnavadhikari.com
    """,
    """Hey Finn, looking for roles this summer and Origami Agents caught my eye. I work hard and learn fast. Really like the agentic email route and would love to chat and explore opportunities. Also might be in SF and would be down to meet in person.
    """,
]

COLD_EMAIL_PROMPTS = [
    f"""
    You are helping Arnav, a 19-year-old EECS student at MIT and cold email god, land an internship at {{company}} via cold outreach.
    
    Generate a list of 2-3 email topics. The output should be a list of lists of keywords, each on a new line. Include all specific details to be able to generate a standout email.
    
    Start with a specific detail about them (class, tweet, research, connection, etc), mention something Arnav is working on, and drop a shared vibe or detail (e.g., competition history, AI interest, builder energy).

    The background of the company employee to send an email to:
    {{recipient_insights}}
    
    And the following personal background:
    {MY_BACKGROUND}
    """,
    f"""
    Given a list of email topics, convert them to fleshed out sentences and compose the final result into a subject line and email body. The first line of output should be the subject line (with no other text), and the rest of the output should be the email body.

    Email topics:
    {{email_topics}}

    Here are 2 stellar examples of emails:
    {example_emails[0]}
    {example_emails[1]}
    """,
    f"""Based on the generated email, draft a short, concise twitter DM of a similar sentiment that I could send to them to land an internship.
    Email:
    {{email}}

    Example DMs:
    {example_dms[0]}
    {example_dms[1]}
    """,
]

SCRAPING_INSTRUCTIONS = """
If on twitter, output their url / handle.

Otherwise, extract the most relevant and compelling information about this person that could help someone personalize a cold email.

Focus on:
- name, location, job title, prev exp, education exp, hot takes, vibes, hobbies, cool tweets, personality, sarcasm, sports, philosophical conclusions
- overlaps with my background (college student, top college / ivy + mit + stanford + cmu + berkeley, ai agents, mcp, ai safety, inference, builder mentality, building communities, previous math/cs olympiad competitor, ai research in healthcare and the environment, robotics research, VEX, FRC)
"""

GATHER_PROMPT = """
Find twitter handle, as well as anything else you can find about {name} and return it in a structured format.

Do not worry about grammar or punctuation or complete sentences at all. Just important details, keyword phrases, concise, to the point.

Output Structure:
- First line: twitter handle in the format @handle
- Second line: based on subtle insights you've found, give quick phrase description of type of email they would respond to e.g. "short concise genz" or "semi-formal"
- After that, all the useful info for cold email
"""

ASK_PROMPT = """
Given these details about {name}.

---
{internet_content}
---

{question}
"""
