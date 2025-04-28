from enum import Enum
from functools import total_ordering
import os
from dotenv import load_dotenv
# to keep the imports the same
from PROMPTS import (
    MY_BACKGROUND,
    MY_VALUES,
    CHOOSE_PROFILE_PROMPT,
    GATHER_PROMPT,
    ASK_PROMPT,
    SCRAPING_INSTRUCTIONS,
    GATHER_PROMPT,
    ASK_PROMPT,
    COLD_EMAIL_PROMPTS,
)

DEEP_DIVE = False

load_dotenv()

CHROME_PATH = os.getenv("CHROME_PATH")
EDGE_PATH = os.getenv("EDGE_PATH")
CHROME_USER_DATA_DIR = os.getenv("CHROME_USER_DATA_DIR")
CHROME_PROFILE_DIRECTORY = os.getenv("CHROME_PROFILE_DIRECTORY")
EDGE_USER_DATA_DIR = os.getenv("EDGE_USER_DATA_DIR")
EDGE_PROFILE_DIRECTORY = os.getenv("EDGE_PROFILE_DIRECTORY")
RESUME_PATH = os.getenv("RESUME_PATH")
CHATGPT_URL = os.getenv("CHATGPT_URL")


@total_ordering
class ProcessingStage(Enum):
    NOT_STARTED = "not_started"
    PROFILES_SCRAPED = "profiles_scraped"
    PROFILES_SELECTED = "profiles_selected"
    PROFILES_PROCESSED = "profiles_processed"
    MESSAGES_DRAFTED = "messages_drafted"
    MESSAGES_APPROVED = "messages_approved"
    MESSAGES_SENT = "messages_sent"
    COMPLETED = "completed"
    ERROR = "error"

    def __lt__(self, other):
        order = list(self.__class__)
        return order.index(self) < order.index(other)


STAGE_LOOKUP = {stage.name.lower(): stage for stage in ProcessingStage}
STAGE_LOOKUP.update({stage.value: stage for stage in ProcessingStage})


def parse_processing_stage(s: str) -> ProcessingStage:
    return STAGE_LOOKUP[s.strip().lower()]

