# Legacy PC collector (retired)

Retired on 2026-10-11. Kept for reference only; not part of the live system.

This folder holds the old local Streamlit dashboard (`app.py`), the SQLite layer
(`database.py`), the local collectors and scorer, their root-level tests and the
Windows task scripts. It read `data/weather.db`, which was deleted on 2026-10-11 and
is lost, so none of it can run against real data. Paths inside these files still
assume they sit in the repository root; they were moved here unchanged on
2026-11-12 so reviews and assistants focus on the live code.

The live pipeline is `cloud/` (collection and scoring), `site/` (public page),
`history/` (encrypted scored days, never edited) and `.github/workflows/`.
Do not restart or "fix" anything here as part of cloud maintenance.
