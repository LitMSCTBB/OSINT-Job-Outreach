import json
import os
import time

from CONSTANTS import ProcessingStage, parse_processing_stage

READY_FILE = "data/"


def write_step_output(process_step: dict, data: dict):
    """Write output file and mark step as ready in transmissions/ready.json"""
    output_path = process_step["output_file"]
    ready_key = process_step["done_key"]
    # the ready file is going to be ready.json in the same directory as the output file
    ready_file = os.path.join(os.path.dirname(output_path), "ready.json")

    # Write actual output file
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    # Mark as ready in transmissions/ready.json
    if os.path.exists(ready_file):
        with open(ready_file, "r") as f:
            ready_data = json.load(f)
    else:
        ready_data = {}

    ready_data[ready_key] = True

    with open(ready_file, "w") as f:
        json.dump(ready_data, f, indent=2)


def wait_until_ready(process_step: dict):
    """Block until step's done_key is marked True in transmissions/ready.json"""
    ready_key = process_step["done_key"]
    ready_file = os.path.join(
        os.path.dirname(process_step["output_file"]), "ready.json"
    )

    print(f"👀 Waiting for key '{ready_key}' == true in {ready_file}...")

    while True:
        try:
            if os.path.exists(ready_file):
                with open(ready_file, "r") as f:
                    ready_data = json.load(f)
                    if ready_data.get(ready_key) is True:
                        print(f"✅ Found key '{ready_key}' == true in {ready_file}")
                        return json.load(open(process_step["output_file"]))
        except Exception as e:
            print(f"⚠️ Error reading {ready_file}: {e}")

        time.sleep(0.5)


def is_step_complete(company: str, stage_name: str) -> bool:
    """Check if a processing stage is complete by checking state.json"""
    try:
        target_stage = parse_processing_stage(stage_name)
    except ValueError:
        raise ValueError(f"Unknown stage: {stage_name}")

    state_path = os.path.join("data", company, "state.json")
    if not os.path.exists(state_path):
        return False

    with open(state_path, "r") as f:
        state = json.load(f)
        current_stage = parse_processing_stage(
            state.get("stage", ProcessingStage.NOT_STARTED.value)
        )
        return current_stage >= target_stage


def mark_step_complete(company: str, stage_name: str):
    """Mark a processing stage as complete in state.json"""
    try:
        stage = parse_processing_stage(stage_name)
    except ValueError:
        raise ValueError(f"Unknown stage: {stage_name}")

    state_path = os.path.join("data", company, "state.json")
    state = {}
    if os.path.exists(state_path):
        with open(state_path, "r") as f:
            state = json.load(f)

    state["stage"] = stage.value

    os.makedirs(os.path.dirname(state_path), exist_ok=True)
    with open(state_path, "w") as f:
        json.dump(state, f)
