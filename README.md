# sn-incident-summary

Fetch active incidents from a ServiceNow instance, count them by priority and
state, and write a CSV with one command:

```bash
python summarize.py
```

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
python summarize.py --page-size 25 --output output/small-pages.csv
python summarize.py --query 'active=true^priority=1^ORDERBYDESCsys_created_on^ORDERBYsys_id'
```

The default query defines **open** as `active=true` and sorts newest-created first,
with `sys_id` as a tie-breaker. All result pages are read. `--page-size` controls
the number requested per page, not the total report size. Table and field ACLs
still determine what the account can read.

The default CSV is `output/incidents.csv` beside the script, even if the command
is run from another folder. An explicit relative `--output` path is relative to
the terminal's working directory. Re-running replaces the chosen output file.
An empty result produces a header-only CSV and a total of zero.

The command only reads from ServiceNow. It does not create incidents or add work
notes. Credentials and generated reports are ignored by Git. `sample_output.csv`
contains fictional data and is included as a versioned example.

## Layout

```text
incident_tools/
  __init__.py       Public imports
  models.py         Pydantic models reused from Days 4–5
  labels.py         Priority and state labels
  client.py         Requests, pagination, and validation
summarize.py        CLI, configuration, CSV output, and counts
output/            Generated reports (only .gitkeep is tracked)
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

## Data conventions

- Raw API values are requested so numeric strings such as priority `"2"` can
  become integers. Reference objects become `AssigneeReference` instances.
- CSV `assigned_to` contains a user ID when raw data supplies one, or a display
  name if one is available. An unassigned value is blank.
- The reused model still supports the Day 4 `"open"`/`"closed"` examples as well
  as numeric states. Actual API state codes are retained, not collapsed into
  those two words. Unknown numeric state codes are shown as `State <code>`.
- Priority labels retain the Day 3 rule: P1 Critical, P2 High, others Normal.
  Counts remain separate for each priority number.
- State labels use the standard incident choices; adjust them if your instance
  customizes those choices.
