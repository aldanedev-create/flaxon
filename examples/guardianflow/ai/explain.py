def explain(kind: str) -> str:
    messages = {
        "package_delivery": "A person and a package were detected at the front door, then the person left. Delivery confirmed.",
        "package_removal": "A package was previously detected and later disappeared after a person was detected. Review recommended.",
        "after_hours_activity": "A person was detected outside the configured hours. Review the activity if it was unexpected.",
    }
    return messages.get(kind, "Related camera activity was detected and grouped for review.")
