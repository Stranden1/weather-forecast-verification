"""Local read-only Project HQ. Launch with project_hq/run.py."""
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HQ = Path(__file__).resolve().parent
sys.path.insert(0, str(HQ))
from readers import (ROOT, PRIMARY, discover, read_document, sections, latest_section,
                     display_markdown, document_url, context_text, contained_file)

import streamlit as st


st.set_page_config(page_title="WeatherApp · Project HQ", page_icon="📚", layout="wide")
st.markdown("""<style>
.block-container {max-width:1180px; padding-top:2.5rem; padding-bottom:2rem;}
[data-testid="stVerticalBlock"] {gap:0.65rem;}
h1 {font-size:1.85rem !important;} h2 {font-size:1.4rem !important;}
h3 {font-size:1.12rem !important;}
[data-testid="stMarkdownContainer"] {line-height:1.65;}
[data-testid="stMarkdownContainer"] table {display:block; overflow-x:auto; font-size:0.9rem;}
[data-testid="stMarkdownContainer"] th {text-align:left;}
[data-testid="stMarkdownContainer"] tr:nth-child(even) {background:rgba(128,128,128,.07);}
[data-testid="stCaptionContainer"] {font-variant-numeric:tabular-nums;}
[data-testid="stSidebar"] .block-container {padding-top:1rem;}
.stAppDeployButton {display:none;}
.stCode > div {opacity:1 !important; visibility:visible !important;}
pre {font-size:0.84rem !important;}
</style>""", unsafe_allow_html=True)  # Constant style only; source HTML is never enabled.

catalog = discover()


def load(doc_id):
    try:
        return read_document(doc_id, catalog)
    except (OSError, ValueError, UnicodeError):
        st.warning(f"Cannot read {doc_id}. It may be missing, changed, or outside the allowed sources. Refresh to retry.")
        return None


def render(text, doc_id):
    st.markdown(display_markdown(text, doc_id, catalog), unsafe_allow_html=False)


def source_caption(doc):
    st.caption(f"Source: {doc.id} · File modified {doc.modified:%Y-%m-%d %H:%M UTC}")


def excerpt(label, doc_id, section=None):
    doc = load(doc_id)
    if not doc:
        return
    with st.container(border=True):
        st.markdown(f"**{label}**")
        source_caption(doc)
        parts = sections(doc.text)
        title, body = (next(((t, b) for t, b in parts if t.casefold() == section.casefold()),
                           parts[0] if parts else ("", "")) if section else latest_section(doc.text))
        # Compact source excerpts; dated section titles remain visible as captions.
        st.caption(title)
        if body.startswith("## "):
            body = body.split("\n", 1)[-1].lstrip()
        clipped = body[:700]
        if len(body) > 700:
            clipped = clipped.rsplit("\n", 1)[0] + "\n\n… (excerpt continues in source)"
        render(clipped, doc_id)
        st.markdown(f"[Open source document]({document_url(doc_id)})")


def document_view(doc_id):
    doc = load(doc_id)
    if not doc:
        return
    st.title(next((label for label, name in PRIMARY.items() if name == doc_id), Path(doc_id).stem.replace("_", " ")))
    source_caption(doc)
    parts = sections(doc.text)
    choice = st.selectbox("Jump to a section", range(len(parts) + 1),
                          format_func=lambda i: "Full document" if i == 0 else parts[i - 1][0],
                          key="section:" + doc_id)
    render(doc.text if choice == 0 else parts[choice - 1][1], doc_id)
    with st.expander("Original Markdown · read-only"):
        st.code(doc.text, language="markdown", height=360)


def health_view():
    st.title("System / Collection Health")
    st.caption("Local collection · read at " + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
    st.markdown("Collection status comes from completed outcomes in `data/background.log`.")
    try:
        log = contained_file(ROOT, ROOT / "data" / "background.log")
        if log.stat().st_size > 4_000_000:
            raise ValueError("Log exceeds HQ's bounded reading limit")
        # Audited module: stdlib-only imports, no startup actions. Use its reader,
        # never its append_source_event writer. No app/database/collector imports.
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from collection_health import load_collection_health, yr_stale_warning
        health = load_collection_health(log)
        rows = []
        for source in health["sources"].values():
            rows.append({"Source": source["label"], "State": source["status"],
                         "Last success (UTC)": source["last_success"].strftime("%Y-%m-%d %H:%M") if source["last_success"] else "Unknown",
                         "Age": source["age"], "Latest outcome": source["latest_outcome"] or "Unknown"})
        st.dataframe(rows, hide_index=True, width="stretch")
        warning = yr_stale_warning(health)
        if warning:
            st.warning(warning)
        if health["yr_gap"]:
            gap = health["yr_gap"]
            st.warning(f"Recorded Yr gap: {gap['hours']:.1f} hours, {gap['start']:%Y-%m-%d %H:%M} to {gap['end']:%Y-%m-%d %H:%M} UTC.")
        st.caption("Existing health rules: OK ≤8 h; Delayed >8–12 h or a latest error; Stale >12 h or no recorded success. This does not inspect the Windows task itself.")
    except (OSError, ValueError, ImportError):
        st.info("Local collection health unavailable. The log is missing, inaccessible, linked, or too large. No collection was triggered.")
    st.divider()
    st.subheader("Cloud pipeline")
    st.info("Live cloud health is not queried by this local viewer. Cloud deployment and collection notes are available in the source documents.")
    st.markdown(f"[Cloud plan]({document_url('PLAN_WEBPAGE.md')}) · [Next steps]({document_url('NEXT_STEPS.md')})")
    st.subheader("Validation recorded in the documents")
    st.caption("These are dated reports, not tests run by Project HQ.")
    excerpt("Latest work checkpoint", "WORK_STATUS.md")


pages = ["Overview", *PRIMARY, "Research / Documentation", "System / Collection Health", "Copy AI Context"]
incoming = st.query_params.get("doc")
if incoming != st.session_state.get("last_query_doc"):
    st.session_state.last_query_doc = incoming
    if incoming:
        st.session_state.page = next((label for label, name in PRIMARY.items() if name == incoming), "Research / Documentation")
        if incoming in catalog:
            st.session_state.document = incoming


def navigate():
    st.query_params.clear()
    st.session_state.last_query_doc = None


with st.sidebar:
    st.markdown("## Project HQ")
    st.caption("WEATHERAPP · LOCAL · READ ONLY")
    page = st.radio("Navigation", pages, key="page", on_change=navigate, label_visibility="collapsed")
    st.divider()
    st.caption(f"{len(catalog)} Markdown sources · no database access")
    if st.button("Refresh sources", width="stretch"):
        st.rerun()
    st.caption("Files are read on each interaction. Theme: app menu → Settings. Stop the server with Ctrl+C.")

if incoming and incoming not in catalog:
    st.warning("That document is not in the allowed catalog. Choose an available source below.")

if page == "Overview":
    st.title("WeatherApp · Project HQ")
    st.write("Project notes, next steps, and collection health in one local view.")
    st.caption("Excerpts come directly from existing files. Historical notes can disagree with later updates; dates and source links are retained.")
    left, right = st.columns(2)
    with left:
        excerpt("Project summary", "PROJECT_STATUS.md", "Summary")
        excerpt("Latest decisions", "DECISIONS.md")
    with right:
        excerpt("Latest dated next steps", "NEXT_STEPS.md")
        excerpt("Latest work checkpoint", "WORK_STATUS.md")
elif page in PRIMARY:
    document_view(PRIMARY[page])
elif page == "Research / Documentation":
    st.title("Research / Documentation")
    query = st.text_input("Search filenames and document text", placeholder="Try precipitation, sampling, or collection")
    matches = []
    for name in catalog:
        if not query or query.casefold() in name.casefold():
            matches.append(name)
        else:
            doc = load(name)
            if doc and query.casefold() in doc.text.casefold():
                matches.append(name)
    st.caption(f"{len(matches)} matching sources · root Markdown and documentation under work, outputs, docs, research, cloud, site")
    if matches:
        if st.session_state.get("document") not in matches:
            st.session_state.document = matches[0]
        selected = st.selectbox("Document", matches, key="document")
        st.divider()
        document_view(selected)
    else:
        st.info("No documents match. Try a shorter search.")
elif page == "System / Collection Health":
    health_view()
else:
    st.title("Copy AI Context")
    st.write("Select existing sources. Copy the Markdown with the copy button at the top right of the code block.")
    picked = []
    for label, name in PRIMARY.items():
        shown = "Recent Decisions (latest dated section)" if name == "DECISIONS.md" else "Full Work Status" if name == "WORK_STATUS.md" else label
        if st.checkbox(shown, value=name != "WORK_STATUS.md"):
            doc = load(name)
            if doc:
                picked.append(doc)
    if picked:
        context = context_text(picked)
        st.caption(f"{len(context):,} characters · generated in memory · no context file saved")
        st.code(context, language="markdown", wrap_lines=True, height=420)
    else:
        st.info("Select at least one source to assemble context.")
