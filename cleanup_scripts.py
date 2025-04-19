signature = """
Best,
Arnav Adhikari
Electrical Engineering & Computer Science @ MIT
arnavadhikari.com | linkedin.com/in/arnavwad | +1 (713) 614-1793
"""

# append the signature to the end of all the emais in revisions.json

import json

with open("data/hebbia.com/transmissions/revisions.json", "r") as f:
    data = json.load(f)

for person in data:
    if "Arnav Adhikari" not in person["email"]:
        person["email"] += signature
        person["twitter_message"] += signature

with open("data/hebbia.com/transmissions/revisions.json", "w") as f:
    json.dump(data, f, indent=2)

