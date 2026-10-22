"""Fetch active incidents, export a CSV, and print counts by priority and state."""

import argparse
from collections import Counter
import csv
import os
from pathlib import Path
import sys

from dotenv import load_dotenv
from pydantic import ValidationError
import requests
import truststore

from incident_tools import (
    AssigneeReference,
    IncidentModel,
    ServiceNowClient,
    priority_label,
    state_label,
)
from incident_tools.client import OPEN_INCIDENTS_QUERY


ROOT = Path(__file__).resolve().parent
CSV_FIELDS = [
    "number", "short_description", "priority", "priority_label",
    "state", "state_label", "assigned_to", "sys_id",
]


def load_settings() -> tuple[str, str, str]:
    load_dotenv(ROOT / ".env")
    instance = os.getenv("SN_INSTANCE", "").strip()
    user = os.getenv("SN_USER", "").strip()
    password = os.getenv("SN_PASSWORD", "")
    missing = [
        name for name, value in (
            ("SN_INSTANCE", instance), ("SN_USER", user), ("SN_PASSWORD", password)
        )
        if not value
    ]
    if missing:
        raise ValueError(f"Set {', '.join(missing)} in the project .env or environment.")
    return instance, user, password


def write_csv(incidents: list[IncidentModel], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for incident in incidents:
            assignee = incident.assigned_to
            if isinstance(assignee, AssigneeReference):
                assignee = assignee.display_value or assignee.value
            writer.writerow({
                "number": incident.number,
                "short_description": incident.short_description,
                "priority": incident.priority,
                "priority_label": priority_label(incident.priority),
                "state": incident.state,
                "state_label": state_label(incident.state),
                "assigned_to": assignee or "",
                "sys_id": incident.sys_id or "",
            })


def print_summary(incidents: list[IncidentModel], destination: Path) -> None:
    print(f"Incidents retrieved: {len(incidents)}")
    print("\nBy priority:")
    for priority, count in sorted(Counter(item.priority for item in incidents).items()):
        print(f"  P{priority} ({priority_label(priority)}): {count}")
    print("\nBy state:")
    counts = Counter(item.state for item in incidents)
    for state, count in sorted(counts.items(), key=lambda pair: str(pair[0])):
        print(f"  {state_label(state)} [{state}]: {count}")
    print(f"\nCSV: {destination}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", default=OPEN_INCIDENTS_QUERY, help="ServiceNow encoded query")
    parser.add_argument("--output", type=Path, default=ROOT / "output" / "incidents.csv")
    parser.add_argument("--page-size", type=int, default=100, help="records per API request (1–1000)")
    args = parser.parse_args()
    if not 1 <= args.page_size <= 1000:
        parser.error("--page-size must be between 1 and 1000")

    try:
        instance, user, password = load_settings()
        truststore.inject_into_ssl()
        with requests.Session() as session:
            session.auth = (user, password)
            session.headers.update({"Accept": "application/json"})
            client = ServiceNowClient(instance, session)
            incidents = client.get_all_incidents(args.query, args.page_size)
        # Fetch and validate all records before writing the report.
        write_csv(incidents, args.output)
        print_summary(incidents, args.output)
        return 0
    except requests.exceptions.HTTPError as error:
        status = error.response.status_code if error.response is not None else "unknown"
        messages = {
            401: "Authentication rejected. Check credentials and Basic Auth API access.",
            403: "Access denied. Check incident table and field permissions.",
        }
        print(f"HTTP {status}: {messages.get(status, 'ServiceNow request failed.')}", file=sys.stderr)
    except requests.exceptions.RequestException:
        print("Request failed. Check connectivity, HTTPS trust, and the instance URL.", file=sys.stderr)
    except ValidationError:
        print("Incident data did not match the model. Check the requested fields and schema.", file=sys.stderr)
    except ValueError as error:
        print(error, file=sys.stderr)
    except OSError:
        print("Could not write the CSV. Check the output path and permissions.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
