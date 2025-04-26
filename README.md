# 🚀 300 Personalized Emails in 10 Minutes: Cold Outreach Automation

Most advice today agrees: cold emails open doors.  
When a Sequoia partner visited my campus recently, she closed with:  
> “As a student or innovator, your email address is your biggest unlock."

Cold email galleries like [@_sonith](https://twitter.com/sonith) showcase this too.

I've been cold emailing for 6 years and unlocked massive opportunities.  
But we're now in an era where **information transfer and transformation can be automated**.

And I **hate mundane tasks**.

Cold emails are a craft — but when you're playing a numbers game, sacrificing a little quality for a lot of volume **is worth it**.

So I built a workflow to scale **personalized startup outreach** using GPT, React, and FastAPI.

---

# 📬 Contact **realarnavadhikari24@gmail.com** for questions

I’ll help when I can — otherwise, I’ll try to intro you to someone who can.

**If you find this helpful, please share the repo!** 🙌

Check out [Other Notes and Future Directions](#other-notes-and-future-directions) for more details.

# 🛠 Getting Started

## Prerequisites

- Chrome installed
- ChatGPT account (ideally Plus or better)

You'll also need to **create a custom GPT** with:
- Name: `Internship Seeking Cold Outreach`
- Description: `Helps me generate emails and Twitter DMs for founders, CEOs, technical staff, and alumni to land jobs.`
- Instructions: Use the bottom section of `PROMPTS_example.py`

## Setup Steps

1. **Backend Environment**
   - In `backend/`, copy `.env.example` ➔ `.env`
   - Fill in variables:
     - `OPENAI_API_KEY` (required)
     - (Optional) Other LLM API keys and ScrapingBee, ProxyCurl API keys for advanced scraping
   - Find your local Chrome paths on your machine. Google how to do this. Needed for browser-use and playwright/browser automation 

2. **Connect your Custom GPT**
   - Open a conversation with your custom GPT.
   - Copy the conversation link.
   - Paste it into the `CHATGPT_URL` `.env` variable.

3. **Customize Prompts**
   - Copy `PROMPTS_example.py` ➔ `PROMPTS.py`
   - Modify as needed (the examples are already well-commented).

4. **Frontend Environment**
   - In `frontend/`, run `npm install`
   - Run `npm run dev`

5. **Backend Environment**
   - In `backend/`, run `pip install -r requirements.txt`
   - Run `python app.py`

# 🕵️‍♂️ OSINT and Deep Dive Agents

- If you want to use the deep dive agent for every person, set `DEEP_DIVE = True` in `CONSTANTS.py`.
- You can understand more via the `crawl_person` function in `tools/osint.py`.
- Uses the super smart [`llm_osint`](https://github.com/sshh12/llm_osint) library (props to @sshh12)


# 🤖 Tools: Email, Twitter, LinkedIn

- Mainly relying on Playwright scraping because very reliable for high-repetition scraping
- `browser-use` can get unreliable and expensive
- You can experiment by invoking the different specified methods in each of the tool files but be prepared to refactor.

# `experimental_code` Approaches

Approaches that took up 90% of my dev time on before the current approach. These are provided for reference in case others want to try them out.

I care so much about keeping the code because I FUNDAMENTALLY BELIEVE USER EXPERIENCE AND FLEXIBILITY TO MATCH WORKFLOWS is the thing that sets apart applications today.

### Approach 1: Single company script

The first was running the whole process for a company from one python script and a streamlit interface. Because you can't easily call some sort of streamlit api to render aspects from the script, I had to create and run a separate streamlit script (`st.py`) then facilitate the data communication via files (there was a `data/transmissions` directory). Yep. Basically I implemented the JSON file equivalent of HTTP requests. It wasn't too bad, slightly cumbersome, and it did the job for one company at a time.

Of course, for this to be useful, needed to scale.

### Approach 2: Multiple company script

Because the processing for each company takes in user input from the frontend, I wanted a way to have some kind of queueing system so that other companies could start / resume their processes while waiting for me to resolve things that needed review.

So I formalized the script from approach one into `company_processor.py` and created a `task_manager.py` to manage all these `CompanyProcessor`s. I was getting there but midway I realized - all of this is literally calling for a simple HTTP API which literally has its own elastic multithreading via requests.

----

So now we're at React + FastAPI. You can attempt to use those older approaches but be prepared to do some minor refactoring (shouldn't be too bad if you're decently versed with Python, hit me up with questions) especially because some functions have been changed.

#  Other Notes and Future Directions

This project is an **experimental** toolkit, not a polished SaaS product.

I welcome PRs and improvements, but please treat it as a playground first.

> In fact, I did **NOT** enjoy building this at all. I went down too many Cursor / AI rabbitholes building multiple broken approaches to try to best suit my busy workflow / schedule as a student builder / researcher. My goal was to literally leave this as an agent getting these emails ready and sending them as much as possible while I do my other work, sending me notifications to review things (drafts) as much as possible. So I naturally tried a ton of different approaches. Was it time well spent, I don't know, but I sure am ready to get this out there to move on to the more exciting things I want to work on.

### Technical Details

- Pretty Cheap - small GPT calls to clean / standardize data for each person (and I turn on data sharing so 250K tokens / model / day for free)
  - Email generation is done suspiciously(figure it out and keep on down-low, LOL)

- Can explore fine-tuning deep dive agents of various depths, capabilities, and purposes, and control for speed and cost

- Different mechanisms / agents for different types of messages - e.g. instead of GenZ startups, do Big Tech / IB / Consulting companies or Professors for research positions.

# ⚡TL;DR
This repo is your blueprint for:

- Scalable cold outreach

- High personalization without the manual grind

- Real-world battle-tested automation

I hope it saves you months of grunt work like it did for me.