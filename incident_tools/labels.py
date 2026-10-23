"""Readable labels for priorities and standard incident states."""

from .models import IncidentState


def priority_label(priority: int) -> str:
    labels = {1: "Critical", 2: "High", 3: "Moderate", 4: "Low", 5: "Planning"}
    return labels[priority]


def state_label(state: IncidentState) -> str:
    return state.name.replace("_", " ").title()
