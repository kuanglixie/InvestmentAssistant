# Investment Assistant

Consolidated repo for the stock research multi-agent system and related investment-assistant prototypes.

For the folder-level organization, see `REPO_MAP.md`.

The core app is a CLI-first scaffold for a LangGraph/LangChain stock research system focused on deep value-investing research.

V1 target:

- First deep-research company: PDD Holdings
- Watchlist: PDD, Google / Alphabet, Tencent
- Output: Markdown reports and JSON state
- Source policy: official filings and company IR are source of record

## Run The Scaffold

The scaffold runs without installed third-party dependencies by using a local sequential graph runner. When `langgraph` is installed, the same workflow uses LangGraph's `StateGraph`.

```bash
PYTHONPATH=src python3 -m stock_research.cli research --company PDD --market us-adr
```

The command writes artifacts under:

```text
data/runs/<run_id>/
```

Other useful commands:

```bash
PYTHONPATH=src python3 -m stock_research.cli lessons
PYTHONPATH=src python3 -m stock_research.cli monitor
PYTHONPATH=src python3 -m unittest discover -s tests
```

## Install Later

When network access is available:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
stock-research research --company PDD --market us-adr
```

## Current Scope

The current implementation has a working PDD-first V1 scaffold:

- PDD SEC source discovery and local document cache.
- First-pass official XBRL financial extraction and duplicate-fact verification.
- IR annual-report/PDF cross-validation, including supplemental fills for missing official line items when the XBRL mapper misses them.
- V1 metrics for owner earnings, cash conversion, and unlevered ROIC where inputs exist.
- Candidate lesson registry from the user's Drive notes.
- Separate agents for business model/moat, leadership/people, valuation, customer happiness, and competitor comparison; business and leadership agents already collect annual-report evidence markers.
- Weekly watchlist monitor skeleton for PDD, Alphabet/Google, and Tencent.

For the full phase plan, see [docs/implementation-phases.md](docs/implementation-phases.md).
