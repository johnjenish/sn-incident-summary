"""Fetch incidents, export a CSV, and count priorities, states, and their combinations."""

import argparse
from collections import Counter
import csv
from datetime import date
import os
from pathlib import Path
import sys

from dotenv import load_dotenv
from pydantic import ValidationError
import requests
import truststore

from incident_tools import (
    IncidentModel,
    ServiceNowClient,
    priority_label,
    state_label,
)
from incident_tools.client import OPEN_INCIDENTS_QUERY


ROOT = Path(__file__).resolve().parent
CSV_FIELDS = ["priority", "state", "count"]


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


def summary_rows(incidents: list[IncidentModel]) -> list[dict[str, str | int]]:
    # Tuple keys keep each priority/state combination separate.
    counts = Counter((item.priority, item.state) for item in incidents)
    return [
        {
            "priority": f"P{priority} ({priority_label(priority)})",
            "state": state_label(state),
            "count": count,
        }
        for (priority, state), count in sorted(counts.items())
    ]


def write_csv(incidents: list[IncidentModel], destination: Path) -> None:
    rows = summary_rows(incidents)
    if not rows:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def print_summary(incidents: list[IncidentModel], destination: Path) -> None:
    if not incidents:
        print("No incidents matched the query. Total: 0. No CSV was written.")
        return

    priority_counts = Counter(item.priority for item in incidents)
    state_counts = Counter(item.state for item in incidents)

    print(f"{'Priority':<16} {'State':<14} {'Count':>6}")
    print("-" * 38)
    for row in summary_rows(incidents):
        print(f"{row['priority']:<16} {row['state']:<14} {row['count']:>6}")
    print("-" * 38)
    print(f"{'Total':<31} {len(incidents):>6}")
    print("\nBy priority: " + " | ".join(
        f"P{priority} ({priority_label(priority)}): {count}"
        for priority, count in sorted(priority_counts.items())
    ))
    print("By state: " + " | ".join(
        f"{state_label(state)}: {count}" for state, count in sorted(state_counts.items())
    ))
    print(f"\nCSV: {destination}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--limit", type=int, default=100, help="maximum total incidents to retrieve")
    parser.add_argument("--query", default=OPEN_INCIDENTS_QUERY, help="ServiceNow encoded query")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "output" / f"summary_{date.today().isoformat()}.csv",
        help="destination CSV path",
    )
    parser.add_argument("--page-size", type=int, default=100, help="records per API request (1–1000)")
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be at least 1")
    if not 1 <= args.page_size <= 1000:
        parser.error("--page-size must be between 1 and 1000")

    try:
        instance, user, password = load_settings()
        truststore.inject_into_ssl()
        with requests.Session() as session:
            session.auth = (user, password)
            session.headers.update({"Accept": "application/json"})
            client = ServiceNowClient(instance, session)
            incidents = client.get_all_incidents(args.query, args.page_size, limit=args.limit)
        # Fetch and validate the selected records before writing the report.
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
