"""Readable labels for priorities and standard incident states."""


def priority_label(priority: int) -> str:
    """Keep the priority labels from Day 3."""
    if priority == 1:
        return "Critical"
    elif priority == 2:
        return "High"
    else:
        return "Normal"


def state_label(state: int | str | None) -> str:
    labels = {
        1: "New",
        2: "In Progress",
        3: "On Hold",
        6: "Resolved",
        7: "Closed",
        8: "Canceled",
        "open": "Open",
        "closed": "Closed",
        None: "Unknown",
    }
    return labels.get(state, f"State {state}")
