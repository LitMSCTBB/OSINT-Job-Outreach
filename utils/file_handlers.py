import json
import os
import time

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
    ready_file = os.path.join(os.path.dirname(process_step["output_file"]), "ready.json")

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
