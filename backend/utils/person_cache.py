import os
import json


def get_person_cache_path(domain, person_name):
    """Get the path for caching a person's data"""
    cache_dir = os.path.join("data", domain, "person_cache")
    os.makedirs(cache_dir, exist_ok=True)
    # Sanitize person name for filename
    safe_name = (
        "".join(c for c in person_name if c.isalnum() or c in (" ", "-", "_"))
        .strip()
        .replace(" ", "_")
    )
    return os.path.join(cache_dir, f"{safe_name}.json")


def cache_person_data(domain, person):
    """Cache a person's data to a separate file"""
    cache_path = get_person_cache_path(domain, person["name"])
    with open(cache_path, "w") as f:
        json.dump(person, f, indent=2)


def get_person_data(domain=None, person_name=None):
    """Get a person's data from cache

    Args:
        domain: Optional domain to narrow search. If not provided, will search all domains
        person_name: Name of person to find

    Returns:
        Person data dict if found, None otherwise
    """
    if domain and person_name:
        # Original direct lookup if we have both domain and name
        cache_path = get_person_cache_path(domain, person_name)
        if os.path.exists(cache_path):
            with open(cache_path, "r") as f:
                data = json.load(f)
                return make_auto_caching(domain, data)

    elif person_name:
        all_records = get_records()
        for record in all_records:
            # Case insensitive name matching
            print(record["name"], person_name)
            if record["name"].lower() == person_name.lower():
                # Get the domain from the found record
                record_domain = record.get("domain")
                if record_domain:
                    # Use the original cache path lookup with the found domain
                    return get_person_data(record_domain, person_name)

    return None


def get_all_cached_persons(domain):
    """Get all cached person data for a company"""
    cache_dir = os.path.join("data", domain, "person_cache")
    if not os.path.exists(cache_dir):
        return []

    persons = []
    for file in os.listdir(cache_dir):
        if file.endswith(".json"):
            with open(os.path.join(cache_dir, file), "r") as f:
                data = json.load(f)
                persons.append(make_auto_caching(domain, data))
    return persons


def update_person_data(domain, person_name, updates):
    """Update specific fields of a person's data"""
    person = get_person_data(domain, person_name)
    if person:
        person.update(updates)
        cache_person_data(domain, person)
        return person
    return None


def get_records():
    # iterate over all folders in data. if there is a person_cache folder, go through the json files in there.
    records = []
    for folder in os.listdir("data"):
        if os.path.isdir(os.path.join("data", folder)):
            # check if there is a person_cache folder
            if os.path.isdir(os.path.join("data", folder, "person_cache")):
                for file in os.listdir(os.path.join("data", folder, "person_cache")):
                    if file.endswith(".json"):
                        with open(
                            os.path.join("data", folder, "person_cache", file), "r"
                        ) as f:
                            obj = json.load(f)
                            # check if obj has a name and profile_link
                            if "name" in obj and "profile_link" in obj:
                                obj["domain"] = folder
                                records.append(obj)
    return records


class AutoCachingPerson(dict):
    """
    A dict wrapper that automatically caches whenever the person data is modified.
    """

    def __init__(self, domain, person_dict):
        super().__init__(person_dict)
        self.domain = domain

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        cache_person_data(self.domain, self)

    def update(self, *args, **kwargs):
        super().update(*args, **kwargs)
        cache_person_data(self.domain, self)


def make_auto_caching(domain: str, person: dict) -> AutoCachingPerson:
    """Helper function to wrap a person dict with auto-caching"""
    return AutoCachingPerson(domain, person)
