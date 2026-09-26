# Project HQ — Phase 1

A local, read-only viewer of WeatherApp's existing documentation. No new packages.

From `E:\WeatherApp` in PowerShell:

```powershell
.\.venv\Scripts\python.exe -B project_hq\run.py
```

Open **http://127.0.0.1:8510**. Stop with Ctrl+C. The launcher binds only to
loopback, disables usage telemetry, filesystem watching and static file serving,
and suppresses Python bytecode writes. It uses the existing Streamlit installation.
It starts a separate server; it does not restart the weather dashboard or collectors.
If port 8510 is occupied, stop only the previous HQ instance before relaunching.

## Views

- Overview: literal source excerpts, with source paths and file modification times.
- Project Status, Next Steps, Decisions, Work Status: full Markdown and section picker.
- Research / Documentation: automatic Markdown discovery and filename/content search.
- System / Collection Health: existing local log-based health rules; no SQLite access.
- Copy AI Context: selected documents combined in memory. Use the code block's copy
  icon. Decisions defaults to its latest dated H2 section; Work Status is opt-in.

Tables, lists, checklists, code blocks and headings use Streamlit's Markdown renderer.
App menu → Settings controls the theme, including dark mode. Markdown checkboxes
are display only. Refresh sources rereads files; no background polling is added.
Document links open other catalogued Markdown sources. Links to other local files
are displayed as paths. Image embeds are converted to links to avoid automatic
external requests; source HTML is disabled. The original Markdown is also viewable.

## Boundaries

Project files stay where they are. HQ has no editor, save endpoint, collection
button, shell command UI, database connection, migration, or cloud integration.
It does not load `.env`, application startup code, database code or collectors.
Only the existing stdlib-only `collection_health` module's reader is reused.
The health view reads its fixed log path and displays parsed outcomes, never raw
log/error text. It does not verify the Windows scheduled task or live cloud state.

Discovery covers root `*.md` and Markdown under `work/`, `outputs/`, `docs/`,
`research/`, `cloud/`, `site/`. Hidden subdirectories, environments and dependencies
are excluded. Symlinks/junctions and sources outside the project are rejected.
Only discovered document IDs can be opened. Markdown over 1 MB is excluded; health
logs over 4 MB are not read by HQ. Missing/unreadable sources degrade to a message.

The documents contain historical statements and sometimes conflicting updates.
HQ preserves them. “Latest” means greatest ISO date in an H2 heading, with document
order breaking ties. File modification time is not a claim of fresh validation.
Test counts are reported documentation, not freshly run project tests.

Everything delivered for HQ lives here. Deleting `project_hq/` after stopping its
server removes HQ without affecting the original project. No root handoff documents
were edited; this task's checkpoint is `project_hq/WORK_STATUS.md`.

## Validation

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s project_hq -p "test_*.py" -v
```

Tests create disposable fixtures only in a temporary directory. The UI tests guard
against writes to existing project files and all SQLite connections. No live project
test/collector is launched from HQ. Phase 2 editing has deliberately not been built;
it would need preview, explicit Confirm & Save, allowlist checks, conflict detection,
isolated backups and atomic writes as specified in the request.
