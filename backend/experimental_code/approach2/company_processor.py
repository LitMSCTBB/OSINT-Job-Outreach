import asyncio
from typing import List, Dict, Optional
from enum import Enum
import os
import json

from tools.linkedin import scrape_company_employees, scrape_linkedin_profile
from utils.notifications import notify_user

from backend.tools.email import craft_messages, send_gmail, find_all_permutation_emails
from CONSTANTS import (
    CHOOSE_PROFILE_PROMPT,
    COLD_EMAIL_PROMPTS,
    CHATGPT_URL,
    ProcessingStage,
    parse_processing_stage,
)
from utils.person_cache import (
    cache_person_data,
    get_all_cached_persons,
    make_auto_caching,
)
from utils.prompter import prompt
from tools.twitter import scrape_twitter_posts, send_twitter_dm
from tools.osint import crawl_person, fetch_internet_content
from bs4 import BeautifulSoup
import re
from langchain_openai import ChatOpenAI
from browser_use import Agent, Browser
from playwright.async_api import BrowserContext, Page


class CompanyProcessor:
    def __init__(
        self,
        browser: Browser,
        context: BrowserContext,
        company_url: str,
        domain: str,
        rerun_config: Dict[str, bool] = {},
    ):
        self.browser = browser
        self.context = context

        # Company-level state
        self.company_url = company_url
        self.domain = domain
        self.stage = ProcessingStage.NOT_STARTED
        self.profiles: List[Dict] = []
        self.chosen_indices: List[int] = []
        self.rerun_config: Dict[str, bool] = rerun_config
        self.error: Optional[str] = None

    async def process_next_available_step(self) -> bool:
        """Advance the processor through the pipeline. Returns True if a step was executed."""
        if not self.company_url or not self.domain:
            raise RuntimeError("Company not initialized")

        # load last state
        self.load_persistent_state()

        print(f"Processing next step for {self.domain} (stage: {self.stage})")

        executed = False
        try:
            match self.stage:
                case ProcessingStage.NOT_STARTED:
                    try:
                        await scrape_company_employees(self.context, self.domain)
                        self.stage = ProcessingStage.PROFILES_SCRAPED
                        executed = True
                    except Exception as e:
                        print(f"Error scraping company people: {e}")
                        notify_user(
                            "Scraping Error", f"Error scraping {self.domain}: {e}"
                        )

                case ProcessingStage.PROFILES_SCRAPED:
                    if not self.chosen_indices:
                        print("No profiles chosen, waiting for selection")
                        return False
                    self.stage = ProcessingStage.PROFILES_SELECTED
                    executed = True

                case ProcessingStage.PROFILES_SELECTED:
                    for ind in self.chosen_indices:
                        try:
                            person = self.profiles[ind]
                            # await crawl_person(self.browser, self.context, self.domain, person)
                            person["insights"] = person["linkedin_summary"]
                        except Exception as e:
                            print(f"Error processing person {ind}: {e}")
                            notify_user(
                                "Processing Error",
                                f"Error processing person in {self.domain}: {e}",
                            )
                            continue
                    self.stage = ProcessingStage.PROFILES_PROCESSED
                    executed = True

                case ProcessingStage.PROFILES_PROCESSED:
                    try:
                        page = await self.context.new_page()
                        await page.goto(CHATGPT_URL)
                        for ind in self.chosen_indices:
                            try:
                                person = self.profiles[ind]
                                await craft_messages(
                                    self.browser,
                                    self.context,
                                    page,
                                    self.domain,
                                    person,
                                    regen=self.rerun_config.get("messages", False),
                                )
                            except Exception as e:
                                print(
                                    f"Error crafting messages for {person.get('name', 'unknown')}: {e}"
                                )
                                notify_user(
                                    "Message Error",
                                    f"Error generating messages for {person.get('name', 'unknown')} in {self.domain}: {e}",
                                )
                                continue
                        self.stage = ProcessingStage.MESSAGES_DRAFTED
                        executed = True
                    except Exception as e:
                        print(f"Error setting up page for message crafting: {e}")
                        notify_user(
                            "Setup Error",
                            f"Error setting up message generation for {self.domain}: {e}",
                        )

                case ProcessingStage.MESSAGES_DRAFTED:
                    missing_emails = []
                    for ind in self.chosen_indices:
                        person = self.profiles[ind]
                        if not person.get("email2"):
                            missing_emails.append(person.get("name", f"person {ind}"))
                    if missing_emails:
                        print(
                            f"Warning: Missing email2 for: {', '.join(missing_emails)}"
                        )
                        notify_user(
                            "Missing Emails",
                            f"Some people in {self.domain} are missing email2: {', '.join(missing_emails)}",
                        )
                        return False
                    self.stage = ProcessingStage.MESSAGES_APPROVED
                    executed = True

                case ProcessingStage.MESSAGES_APPROVED:
                    for ind in self.chosen_indices:
                        try:
                            person = self.profiles[ind]
                            emails = await find_all_permutation_emails(
                                person["name"], self.domain
                            )
                            person["possible_emails"] = emails

                            email_errors = []
                            for email in emails:
                                try:
                                    await send_gmail(
                                        email, person["email"], self.domain
                                    )
                                except Exception as e:
                                    email_errors.append(f"{email}: {str(e)}")
                                    continue

                            if email_errors:
                                print(
                                    f"Errors sending emails for {person['name']}: {', '.join(email_errors)}"
                                )
                                notify_user(
                                    "Email Send Error",
                                    f"Some emails failed for {person['name']} in {self.domain}: {', '.join(email_errors)}",
                                )

                            if person.get("twitter_handle") and person.get(
                                "twitter_message"
                            ):
                                try:
                                    await send_twitter_dm(
                                        person["twitter_handle"],
                                        person["twitter_message"],
                                    )
                                except Exception as e:
                                    print(
                                        f"Error sending Twitter DM to {person['twitter_handle']}: {e}"
                                    )
                                    notify_user(
                                        "Twitter Error",
                                        f"Failed to send Twitter DM to {person['twitter_handle']} in {self.domain}: {e}",
                                    )
                        except Exception as e:
                            print(
                                f"Error processing person {person.get('name', 'unknown')}: {e}"
                            )
                            notify_user(
                                "Processing Error",
                                f"Error processing {person.get('name', 'unknown')} in {self.domain}: {e}",
                            )
                            continue

                    self.stage = ProcessingStage.COMPLETED
                    executed = True

            print(f"Completed stage: {self.stage}")
            self.save_persistent_state()
            return executed

        except Exception as e:
            print(f"Unexpected error processing {self.domain}: {e}")
            notify_user(
                "Processing Error", f"Unexpected error processing {self.domain}: {e}"
            )
            self.error = str(e)
            self.save_persistent_state()
            return False

    def _get_company_data_dir(self):
        return os.path.join("data", self.domain)

    def load_persistent_state(self):
        """
        If partial state is already saved, load it and set appropriate stage.
        """
        # load the indices from state.json. state.json also stores the last step that was completed.
        state_path = os.path.join(self._get_company_data_dir(), "state.json")
        if os.path.exists(state_path):
            with open(state_path, "r") as f:
                state = json.load(f)
                if "chosen_indices" in state:
                    self.chosen_indices = state["chosen_indices"]
                if "stage" in state:
                    self.stage = parse_processing_stage(state["stage"])

        # load all the profiles from the person_cache
        self.profiles = get_all_cached_persons(self.domain)

        print(
            f"LOADED STATE: {self.stage}, CHOSEN INDICES: {self.chosen_indices}, {len(self.profiles)} PROFILES FOUND"
        )

    def save_persistent_state(self):
        """
        Save the current state to a file.
        """
        state_path = os.path.join(self._get_company_data_dir(), "state.json")
        with open(state_path, "w") as f:
            json.dump(
                {"chosen_indices": self.chosen_indices, "stage": self.stage.value}, f
            )
