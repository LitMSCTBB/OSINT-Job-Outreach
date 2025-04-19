import os
import time
import json
import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from utils.CONSTANTS import get_transmission_ready, get_process

global transmission_ready, process
transmission_ready = None
process = None

def load_json(path):
    with open(path, "r") as f:
        return json.load(f)

def write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

# this is different from the file handler functions because we let streamlit autorefresh so that we're just doing one-time checks of the files each time

def signal_done(step_key):
    # read from data/current.json to get the company domain
    global transmission_ready, process
    if transmission_ready is None:
        with open("data/current.json", "r") as f:
            current = json.load(f)
        domain = current["company"]
        transmission_ready = get_transmission_ready(domain)
        process = get_process(domain)
    if os.path.exists(transmission_ready):
        with open(transmission_ready, "r") as f:
            ready_data = json.load(f)
    else:
        ready_data = {}
    ready_data[step_key] = True
    with open(transmission_ready, "w") as f:
        json.dump(ready_data, f, indent=2)


def is_step_ready(step_key):
    # read from data/current.json to get the company domain
    global transmission_ready, process
    if transmission_ready is None:
        with open("data/current.json", "r") as f:
            current = json.load(f)
        domain = current["company"]
        transmission_ready = get_transmission_ready(domain)
        process = get_process(domain)
    if os.path.exists(transmission_ready):
        with open(transmission_ready, "r") as f:
            ready_data = json.load(f)
            return ready_data.get(step_key, False)
    return False


st.set_page_config(page_title="Cold Email Workflow", layout="wide")
st.title("📬 Cold Email Workflow")
st.caption("Live-updating interface that reflects backend progress")

# Auto-refresh every 5 seconds (limit to 100 refreshes to avoid infinite loop in dev)
st_autorefresh(interval=5000, limit=100, key="refresh")

# STEP 1: User chooses profiles
st.header("Step 1: Choose Profiles")

if is_step_ready("profiles_ready"):
    profiles_path = process["scrape_company_people"]["output_file"]
    profiles = load_json(profiles_path)["profiles"]

    # Only show Step 1 expanded if we're not on Step 2
    step1_expanded = not is_step_ready("drafts_ready")
    with st.expander("Step 1: Choose Profiles", expanded=step1_expanded):
        st.markdown("Select the people you'd like to reach out to:")
        selected_indices = []

        for i, p in enumerate(profiles):
            with st.container():
                # One row per person
                cols = st.columns([0.05, 0.95])
                checked = cols[0].checkbox("", key=f"check_{i}", value=(i < 4))
                with cols[1]:
                    st.markdown(f"**[{p['name']}]({p['profile_link']})**")
                    st.markdown(
                        p["linkedin_relevant"]
                    )  # full summary, can handle multi-line
                if checked:
                    selected_indices.append(i)

        st.markdown("\n")
        if st.button("✅ Confirm Selection"):
            write_json(process["user_choose_profiles"]["output_file"], selected_indices)
            signal_done(process["user_choose_profiles"]["done_key"])
            st.success("Saved selected profiles and marked ready.")
else:
    st.info("Waiting for scraped profiles...")

# STEP 2: User reviews and edits email drafts
st.header("Step 2: Review Email Drafts")
if is_step_ready("drafts_ready"):
    drafts_path = process["scrape_internet_content_and_craft_email"]["output_file"]
    people = load_json(drafts_path)
    edited = []

    # Add CSS for text area styling
    st.markdown(
        """
        <style>
            .stTextArea textarea {
                border: 1px solid #ccc !important;
                border-radius: 5px !important;
            }
        </style>
    """,
        unsafe_allow_html=True,
    )

    for person in people:
        st.subheader(f"[{person['name']}]({person['profile_link']})")

        # Create two equal width columns
        col1, col2 = st.columns([0.5, 0.5])

        with col1:
            # Email section
            st.markdown("### Email / Twitter Message")
            email_content = st.text_area(
                f"Email content for {person['name']}",
                f"{person['email']}",
                key=f"email_{person['name']}",
                height=700,
            )

            # Email addresses section
            st.markdown("### Email Addresses")
            email_addresses = st.text_area(
                f"Email addresses for {person['name']} (one per line)",
                "\n".join(person.get("possible_emails", [])),
                key=f"emails_{person['name']}",
                height=100,
            )

            # Twitter section (if available)
            if not person.get("twitter_handle") == "NONE":
                st.markdown("### Twitter")
                st.markdown(
                    f"**Twitter handle found so also sending to [{person['twitter_handle']}](https://x.com/{person['twitter_handle']})**"
                )
                # twitter_message = st.text_area(
                #     f"Twitter message for {person['name']}",
                #     person.get("twitter_message", ""),
                #     key=f"twitter_{person['name']}",
                #     height=300,
                # )

        with col2:
            # Insights section in a scrollable container
            st.markdown("### Insights")
            st.markdown(
                f'<div style="height: 1200px; overflow-y: auto; padding: 10px; border: 1px solid #ccc; border-radius: 5px;">{person.get("insights", "No insights available")}</div>',
                unsafe_allow_html=True,
            )

        # Update person object with edited values
        person["email"] = email_content
        person["twitter_message"] = person["email"]
        person["possible_emails"] = [
            email.strip() for email in email_addresses.split("\n") if email.strip()
        ]
        edited.append(person)

    if st.button("📨 Finalize Emails"):
        write_json(process["user_revisions"]["output_file"], edited)
        signal_done(process["user_revisions"]["done_key"])
        st.success("Revised emails saved and marked ready.")
else:
    st.info("Waiting for generated email drafts...")
