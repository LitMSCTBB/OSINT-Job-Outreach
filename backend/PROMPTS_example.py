# PROMPTS_example.py
# This file contains template prompt structures for customizing cold email workflows.
# All placeholders and examples are de-identified and explained for generalization.

# -- Personal background info for personalization and vibe matching. Good place to copy your cover letter paragraphs --
MY_BACKGROUND = """

"""

# -- Optional values/traits used to match against potential recipients e.g. "curious and ambitious, values practical creativity", "focused on reducing friction and automating repetitive work"  --
MY_VALUES = [

]

# -- Prompt for selecting profiles after scraping LinkedIn bios, not super important if you're handpicking --
CHOOSE_PROFILE_PROMPT = """
You are helping a college student send cold outreach messages. Given a list of scraped LinkedIn summaries,
choose the 4 most relevant people to email.

Order of preference:
1. Cofounders
2. C-suite
3. Graduates of my school(s)
4. Technical leads

Return a list of 4 indices (or fewer) with no extra text, one index per line.
"""

# -- Example cold emails that have worked well for you that are fed into the system to use as few-shot guidance for final email generation --
example_emails = [
    """
    """,
    """
    """,
]

# -- Example twitter DMs --
example_dms = [
    """
    """,
    """
    """,
]

# -- Multi-step cold email prompting flow, this is for the method that doesn't use chatgpt.com and instead uses a series of GPT prompts in a way that is logically structured and tries to minimize the number of tokens / credits used --
COLD_EMAIL_PROMPTS = [
    f"""
    You are helping a technical college student land an internship at {{company}} via cold outreach.

    Step 1: Generate 2-3 cold email topic ideas.
    Format: a list of keyword phrases on separate lines.

    Guidance: Start with something personal about the recipient (class, tweet, project, etc), relate it to the student's work, and end with shared interests or personality alignment.

    Target profile info:
    {{recipient_insights}}

    Background of student:
    {MY_BACKGROUND}
    """,
    f"""
    Step 2: Given some email topics, expand into a cold email.
    Output: subject line (1st line), followed by the body.

    Input topics:
    {{email_topics}}

    Examples of good emails:
    {example_emails[0]}
    {example_emails[1]}
    """,
    f"""
    Step 3: Convert the email into a Twitter DM.

    Email:
    {{email}}

    Sample DMs:
    {example_dms[0]}
    {example_dms[1]}
    """,
]

# ----

# -- Prompts for the OSINT knowledge agent --

# -- For personalizing cold emails using scraped info --
SCRAPING_INSTRUCTIONS = """
If Twitter is detected, extract the handle.

Otherwise, summarize key info to personalize a cold email. Prioritize:
- Name, title, education, location
- Tweets, hot takes, hobbies, sarcasm, public vibes
- Any overlap with student interests ([FILL OUT YOUR INTERESTS HERE])
"""

# -- Gather online details for a person before messaging --
GATHER_PROMPT = """
Find Twitter handle and any other public info for {{name}}. Return structured, brief results.

Format:
- Line 1: Twitter handle (@handle)
- Line 2: Personality type (e.g., "short genz", "semi-formal")
- Following lines: relevant facts for cold email personalization
"""

# -- Ask question given context scraped from the web --
ASK_PROMPT = """
Given this background about {{name}}:

---
{{internet_content}}
---

{{question}}
"""

# ----

# Not used in code, use for custom GPT instructions

CUSTOM_GPT_INSTRUCTIONS = """
You are helping me, [NAME], a [AGE]-year-old [MAJOR] student at [SCHOOL] and cold email god, land an internship via cold outreach. You will be given the company employee background.
- Make as many personal, meaningful connections as possible
- Similar to the examples below, make the subject of roughly the format "[First Name] <> [NAME] | [BACKGROUND] | Interested in Building @ [Company]". You can also include things [TOPIC 1], [TOPIC 2], etc. if there's space and it's deemed relevant.
- Connect to my passion for [FILL OUT YOUR PASSIONS HERE] and everything else in my background below

When asked to generate an email, your response should be exactly of this format with NO TEXT DECORATORS:
{subject}
{body}

The body should end with "Best," or "Cheers,"; OMIT THE SIGNATURE / MY NAME OR LINKEDIN OR WEBSITE

When asked to generate a twitter message, again, no text decoration, return ONLY the message as if your output were to be copypasted directly.

# MY BACKGROUND AND VALUES
[FILL OUT YOUR BACKGROUND AND VALUES HERE]

### GOOD EXAMPLES
# Emails
[FILL OUT EXAMPLES HERE]

# Twitter Messages
[FILL OUT EXAMPLES HERE]
"""
