# sn-incident-summary

Summarize active ServiceNow incidents by priority and state, print totals, and
export grouped counts to CSV.

```bash
python summarize.py
```

## Why this exists

A ServiceNow incident backlog can span several list pages. For triage or a
team status update, this tool retrieves matching incidents from the Table API,
validates their data, and produces a repeatable summary without manually
counting records. The CSV can be opened in Excel or Numbers.

## Setup

Use Python 3.10 or later. From this project folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env` locally:

- `SN_INSTANCE`: your HTTPS instance URL, without an API or UI path.
- `SN_USER`: your instance account's login ID.
- `SN_PASSWORD`: that same account's password.

Quote the password if it contains spaces or special characters. Existing
environment variables take precedence over `.env`. The account needs incident
read access and permission to use Basic Authentication. A successful browser
login alone does not establish API access.

`truststore` enables HTTPS verification using the operating system's trusted
certificates. It resolved the certificate issue encountered in the Day 5
exercises; certificate verification remains enabled.

## Run

```bash
python summarize.py
python summarize.py --limit 25 --output output/my-summary.csv
python summarize.py --limit 250 --page-size 50
python summarize.py --limit 10 --query 'active=true^priority=1^ORDERBYDESCsys_created_on^ORDERBYsys_id'
python summarize.py --help
```

The default query defines **open** as `active=true` and sorts newest-created first,
with `sys_id` as a tie-breaker. `--limit` is a positive integer and defaults to
**100 total incidents**. The client reads pages until it reaches that limit or
exhausts the results. `--page-size` controls the number requested per page, not
the total report size. The printed counts describe the retrieved records, which
may be a subset of the matching incidents. Table and field ACLs still determine
what the account can read.

The default CSV is `output/summary_YYYY-MM-DD.csv`, using today's local date,
beside the script even if the command is run from another folder. An explicit
relative `--output` path is relative to the terminal's working directory.
Re-running on the same date replaces that day's default report when incidents
are returned. An empty result prints
`No incidents matched the query. Total: 0. No CSV was written.`
and exits successfully. No output file or directory is created, and an existing
CSV at the destination is left untouched.

The command only reads from ServiceNow. It does not create incidents or add work
notes. Credentials and generated reports are ignored by Git. `sample_output.csv`
contains fictional data and is included as a versioned example.

## Layout

```text
incident_tools/
  __init__.py       Public imports
  models.py         Pydantic models and the IncidentState IntEnum
  labels.py         Priority and state labels
  client.py         Requests, pagination, and validation
summarize.py        CLI, configuration, CSV output, and counts
output/            Generated reports (created on export; ignored by Git)
sample_output.csv  Fictional example
.env.example       Empty configuration template
.gitignore
requirements.txt
README.md
```

The client receives a configured `requests.Session`; it doesn't load credentials
or alter them. There is no `wrong_password` parameter. A separate test can supply
a mock session returning HTTP 401 or configure invalid credentials before
calling the normal client.

## Counting and labels

`collections.Counter` counts priorities and states separately. A third counter
uses `(priority, state)` tuples as keys, so P1 + New and P1 + In Progress remain
separate groups. Only combinations present in the retrieved records are printed.
Each of the three sets of counts adds up to the number of retrieved incidents.

The CSV contains exactly `priority,state,count`, with one row per combination.
Rows are sorted by numeric priority (P1 first), then by the underlying state
code. Priority and state values are readable labels. The fictional sample is:

```csv
priority,state,count
P1 (Critical),New,2
P1 (Critical),In Progress,3
P2 (High),On Hold,1
```

The terminal prints the same grouped rows as an aligned table, followed by the
total and compact counts by priority and by state. The sample above totals six
incidents across three combinations.

The model converts raw state `"2"` into `IncidentState.IN_PROGRESS`. The console
prints `In Progress` rather than the state code. We use an `IntEnum` instead of
`sysparm_display_value=true` to keep a consistent, validated state type and
stable numeric API values. Display mode also changes priority `"1"` to a label
such as `"1 - Critical"`, which would require different parsing.

## Data conventions

- Raw API values are requested so numeric strings such as priority `"2"` can
  become integers. Reference objects become `AssigneeReference` instances.
- State is required and has one representation: `IncidentState`. Missing states,
  booleans, unsupported codes, and the old `"open"`/`"closed"` teaching strings
  fail validation. The original Day 4 exercises remain in the separate
  `ai-sprint` project.
- Priority labels are Critical, High, Moderate, Low, and Planning for P1–P5.
- The CSV contains aggregated counts and labels rather than individual records.
- `IncidentState` uses the standard incident choices. If your instance
  customizes those choices, update the enum and label function to match. These
  local English labels do not automatically follow instance customizations or
  user language settings.

## Dependencies

`requirements.txt` lists the four packages the application imports directly:
`requests`, `python-dotenv`, `pydantic`, and `truststore`.

A hand-maintained list is appropriate here because it explains what this small
application needs. `pip freeze` lists everything installed in the environment,
including dependencies such as `urllib3` and `pydantic_core`, and can include
unrelated development tools. Freezing a clean environment can capture exact
transitive versions, but the direct-dependency list is easier to maintain for
this project. Its pinned versions do not lock all transitive dependencies.

## What I learned

I learned the fundamentals of Python, including variables, lists, dictionaries, classes, and dataclasses.
I gained an understanding of how these concepts help organize and manage data efficiently.
I also explored how Python can connect with a ServiceNow Personal Developer Instance (PDI) to interact with ServiceNow data and APIs.
This knowledge provides a foundation for building Python-based integrations and AI agents with ServiceNow.
