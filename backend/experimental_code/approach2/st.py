import os
import time
import json
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from CONSTANTS import ProcessingStage, parse_processing_stage
from utils.person_cache import get_all_cached_persons, make_auto_caching

data_dir = os.path.join(os.getcwd(), "data")
companies = json.load(open(os.path.join(data_dir, "task_state.json")))["companies"]
companies = [c["domain"] for c in companies]


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load_company_state(company):
    """Load company state and profiles"""
    company_data_dir = os.path.join(os.getcwd(), "data", company)

    # Load state.json for chosen indices and stage
    state_path = os.path.join(company_data_dir, "state.json")
    state = {}
    if os.path.exists(state_path):
        with open(state_path, "r") as f:
            state = json.load(f)

    # Get all profiles from person cache
    all_profiles = get_all_cached_persons(company)

    # Get chosen profiles if indices exist
    chosen_indices = state.get("indices", [])
    chosen_profiles = (
        [all_profiles[i] for i in chosen_indices] if chosen_indices else []
    )

    return state, all_profiles, chosen_profiles


def save_company_state(company, state_data):
    """Save company state"""
    company_data_dir = os.path.join(os.getcwd(), "data", company)
    os.makedirs(company_data_dir, exist_ok=True)

    state_path = os.path.join(company_data_dir, "state.json")
    with open(state_path, "w") as f:
        json.dump(state_data, f)


st.set_page_config(page_title="Cold Email Workflow", layout="wide")
st.title("📬 Cold Email Workflow")
st.caption("Live-updating interface that reflects backend progress")

# Auto-refresh every 5 seconds (limit to 100 refreshes to avoid infinite loop in dev)
st_autorefresh(interval=5000, limit=100, key="refresh")

for company in companies:
    st.header(f"Company: {company}")

    try:
        state, all_profiles, chosen_profiles = load_company_state(company)
        current_stage = parse_processing_stage(
            state.get("stage", ProcessingStage.NOT_STARTED.value)
        )

        st.subheader(f"🧑‍💼 {company}")

        # STEP 1: User chooses profiles
        st.header("Step 1: Choose Profiles")

        if current_stage >= ProcessingStage.PROFILES_SCRAPED:

            with st.expander("Step 1: Choose Profiles", expanded=(current_stage < ProcessingStage.PROFILES_SELECTED)):
                st.markdown("Select the people you'd like to reach out to:")
                selected_indices = []

                for i, p in enumerate(all_profiles):
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
                    state["stage"] = ProcessingStage.PROFILES_SELECTED.value
                    save_company_state(company, state)
                    st.success("Saved selected profiles and marked ready.")

        # STEP 2: Show messages for editing
        if current_stage >= ProcessingStage.MESSAGES_DRAFTED:
            st.header("Step 2: Edit Messages")

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

            for person in chosen_profiles:
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

                if email_content != person.get("email", ""):
                    person["email2"] = email_content
                    person["twitter_message"] = email_content

                person["possible_emails"] = [
                    email.strip()
                    for email in email_addresses.split("\n")
                    if email.strip()
                ]

            if st.button("📨 Finalize Emails"):
                state["stage"] = ProcessingStage.MESSAGES_APPROVED.value
                st.success("Revised emails saved and marked ready.")
                save_company_state(company, state)

    except Exception as e:
        st.info("Waiting for generated email drafts...")
        continue
