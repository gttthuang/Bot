# Job Bot

[English](./README.md) | [中文](./README_zh.md)

`jobbot` monitors Google Careers search result pages and sends Discord notifications when matching jobs are created, updated, or closed.

This repository is designed for:

- a public GitHub repository
- scheduled GitHub Actions runs
- config-only changes for new Google search queries
- a dedicated `state` branch that stores `data/jobbot.db`

## Current Setup

The active config is [configs/config.yaml](/Users/hshuang/Downloads/Bot/configs/config.yaml:1).

It currently watches:

- `Google`
- `Software Engineer`
- `FULL_TIME`
- `BACHELORS`
- `target_level=EARLY` for Taiwan and China
- `target_level=MID` for Taiwan and China

The current subscriptions are:

- `google_l3_tw_cn`
- `google_l4_tw_cn`

## How Matching Works

Google Careers does not expose internal levels like `L3/L4/L5`.

This bot uses:

- the Google Careers search URL you configure
- the official Google `Experience` badge when present: `early`, `mid`, `advanced`

## How It Works

Data flow:

`Google Careers URL -> fetch all result pages -> parse jobs -> compare with SQLite state -> emit events -> filter by subscription -> notify Discord`

Main modules:

- `jobbot/sources/`: source-specific fetching and parsing
- `jobbot/service.py`: reconciliation and event generation
- `jobbot/rules.py`: subscription matching
- `jobbot/notifiers.py`: Discord webhook payloads
- `jobbot/store.py`: SQLite state

## Local Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DISCORD_WEBHOOK_URL_L3='https://discord.com/api/webhooks/...'
export DISCORD_WEBHOOK_URL_L4='https://discord.com/api/webhooks/...'
JOBBOT_DRY_RUN=1 JOBBOT_LOG_LEVEL=DEBUG python -m jobbot
```

Remove `JOBBOT_DRY_RUN=1` when you want real Discord notifications.

Optional environment variables:

- `JOBBOT_CONFIG`
  Defaults to `configs/config.yaml`
- `JOBBOT_DRY_RUN`
  Set to `1` for no-op notifications
- `JOBBOT_LOG_LEVEL`
  Example: `DEBUG`, `INFO`

## Public GitHub Actions Setup

1. Push this project to a public GitHub repository.
2. Add repository secrets named `DISCORD_WEBHOOK_URL_L3` and `DISCORD_WEBHOOK_URL_L4`.
3. Enable GitHub Actions.
4. Run the workflow once manually, or wait for the schedule.

The workflow is in [.github/workflows/jobbot.yml](/Users/hshuang/Downloads/Bot/.github/workflows/jobbot.yml:1).

It:

- restores `data/jobbot.db` from the `state` branch
- runs the monitor
- writes the updated `data/jobbot.db` back to the `state` branch

This is how dedupe and close detection persist across scheduled runs.

## State Branch

The workflow writes the SQLite database to a branch named `state`.

Notes:

- this branch is public if your repository is public
- it stores monitor state, not secrets
- the Discord webhooks stay in GitHub repository secrets

## Changing Config

The intended way to expand coverage is to edit [configs/config.yaml](/Users/hshuang/Downloads/Bot/configs/config.yaml:1).

Typical changes:

- add a new Google Careers search URL
- add a new subscription
- split Taiwan and China into separate subscriptions
- add `advanced` monitoring later

You should not need to touch code unless:

- Google changes the page format
- you add a non-Google provider
- you change the notification transport

## Tests

```bash
.venv/bin/python -m unittest discover -s tests -v
```
