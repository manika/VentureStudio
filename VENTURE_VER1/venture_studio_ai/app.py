import base64
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

import streamlit as st

from config import APP_TITLE, DATA_DIR, PARENT_COMPANY_RAW_DIR
from modules import (
    file_utils,
    document_loader,
    retrieval,
    llm_client,
    prompt_builder,
    advisor_engine,
    fast_indexer,
    smart_advisor,
    web_search,
)
from modules.vector_store import ChromaStore
from modules.pdf_generator import (
    generate_pdf,
    generate_comprehensive_pdf,
    generate_word_doc,
    generate_excel_doc,
    DOC_TYPES,
    DOC_REFERENCE_PATHS,
    IMBED_QM_PATH,
)

# ---------------------------------------------------------------------------
# Page config + global CSS
# ---------------------------------------------------------------------------
st.set_page_config(page_title=APP_TITLE, layout="wide")

st.markdown("""
<style>
/* ═══════════════════════════════════════════════════════════════════════════
   DESIGN TOKENS
   Accent : #6366F1 indigo   Hover: #4F46E5   Light: #EEF2FF
   Surface: #F1F5F9 slate    Cards: #ffffff
   Sidebar: #0F172A slate-900
   Text   : #0F172A / #64748B / #94A3B8
   Border : #E2E8F0
   ═══════════════════════════════════════════════════════════════════════════ */

/* ── Global ──────────────────────────────────────────────────────────────── */
.stApp, [data-testid="stAppViewContainer"] { background: #F1F5F9; }
.main .block-container { max-width: 1100px; padding: 1.5rem 2rem 3rem; }

/* ── Single unified page scroller ───────────────────────────────────────── */
.stApp { overflow-y: auto !important; height: auto !important; }
[data-testid="stAppViewContainer"] { height: auto !important; overflow: visible !important; }
/* Remove the main content area's independent scroll */
section[data-testid="stMain"],
[data-testid="stAppViewBlockContainer"] {
    overflow: visible !important;
    height: auto !important;
    max-height: none !important;
}
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] > div:first-child {
    height: auto !important;
    max-height: none !important;
    overflow-y: visible !important;
    position: sticky !important;
    top: 0 !important;
    align-self: flex-start !important;
}

/* ── Top nav ─────────────────────────────────────────────────────────────── */
.top-nav {
    background: #0F172A;
    padding: 14px 24px;
    display: flex;
    align-items: center;
    gap: 18px;
    margin-bottom: 20px;
    border-radius: 10px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.18);
}
.top-nav img { height: 80px; object-fit: contain; }
.top-nav-sep { width: 1px; height: 38px; background: #1E293B; flex-shrink: 0; }
.top-nav-text { display: flex; flex-direction: column; gap: 3px; }
.top-nav-title { color: #ffffff; font-weight: 700; font-size: 1.3rem; letter-spacing: 0.12em; }
.top-nav-sub   { color: #94A3B8; font-size: 1.1rem; letter-spacing: 0.04em; }
.top-nav-fallback {
    width: 46px; height: 46px; background: #6366F1; border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    color: #ffffff; font-weight: 800; font-size: 1rem; flex-shrink: 0;
}

/* ── Breadcrumb ──────────────────────────────────────────────────────────── */
.breadcrumb {
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #94A3B8;
    margin-bottom: 10px;
    margin-top: 2px;
}

/* ── Profile chip ────────────────────────────────────────────────────────── */
.profile-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.55rem;
    background: #ffffff;
    border: 1px solid #C7D2FE;
    border-radius: 999px;
    padding: 0.38rem 1.1rem;
    font-size: 0.84rem;
    color: #374151;
    margin-bottom: 1.4rem;
    box-shadow: 0 1px 4px rgba(99,102,241,0.1);
}
.profile-chip .chip-dot { width: 8px; height: 8px; background: #6366F1; border-radius: 50%; flex-shrink: 0; }
.profile-chip strong { color: #0F172A; font-weight: 700; }

/* ── Section label ───────────────────────────────────────────────────────── */
.section-label {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    color: #94A3B8;
    margin-bottom: 0.6rem;
}

/* ── Page header ─────────────────────────────────────────────────────────── */
.page-header { margin-bottom: 1.5rem; }
.page-header h2 { font-size: 1.3rem; font-weight: 700; color: #0F172A; margin: 0 0 0.25rem; }
.page-header p  { font-size: 0.85rem; color: #64748B; margin: 0; line-height: 1.55; }

/* ── Tabs ────────────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    border-bottom: 2px solid #E2E8F0;
    background: transparent;
    padding-bottom: 0;
    margin-bottom: 0;
}
.stTabs [data-baseweb="tab"] {
    padding: 0.75rem 1.75rem;
    font-size: 0.9rem;
    font-weight: 600;
    color: #64748B;
    background: transparent;
    border-radius: 0;
    border-bottom: 3px solid transparent;
    margin-bottom: -2px;
    letter-spacing: 0.01em;
}
.stTabs [aria-selected="true"] {
    color: #FF7F6E !important;
    border-bottom: 3px solid #FF7F6E !important;
    font-weight: 700 !important;
    background: transparent !important;
}
.stTabs [data-baseweb="tab-panel"] {
    background: #ffffff;
    border: 1px solid #E2E8F0;
    border-top: none;
    border-radius: 0 0 16px 16px;
    padding: 2rem 2.25rem 2.25rem;
    box-shadow: 0 4px 24px rgba(0,0,0,0.07);
    margin-top: 0;
}

/* ── Buttons ─────────────────────────────────────────────────────────────── */
.stButton > button {
    border-radius: 8px;
    font-weight: 600;
    font-size: 0.875rem;
    letter-spacing: 0.01em;
    transition: all 0.15s ease;
    padding: 0.5rem 1.4rem;
    height: auto;
}
.stButton > button[kind="primary"] {
    background: #FF7F6E;
    border: none;
    color: #ffffff;
    box-shadow: 0 2px 8px rgba(255,127,110,0.35);
}
.stButton > button[kind="primary"]:hover {
    background: #E85C4A;
    transform: translateY(-1px);
    box-shadow: 0 5px 16px rgba(255,127,110,0.4);
}
.stButton > button:not([kind="primary"]) {
    background: #ffffff;
    border: 1.5px solid #E2E8F0;
    color: #374151;
}
.stButton > button:not([kind="primary"]):hover {
    border-color: #FF7F6E;
    color: #D94A38;
    background: #FFF5F3;
    box-shadow: 0 2px 6px rgba(255,127,110,0.15);
}

/* ── Download button ─────────────────────────────────────────────────────── */
.stDownloadButton > button {
    border-radius: 8px;
    font-weight: 600;
    background: #FFF5F3;
    border: 1.5px solid #FF7F6E;
    color: #D94A38;
    transition: all 0.15s ease;
    padding: 0.4rem 1rem;
}
.stDownloadButton > button:hover {
    background: #FF7F6E;
    color: #ffffff;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(255,127,110,0.35);
}

/* ── Expanders ───────────────────────────────────────────────────────────── */
.streamlit-expanderHeader {
    background: #F8FAFF;
    border: 1px solid #E2E8F0 !important;
    border-radius: 8px;
    font-weight: 700;
    font-size: 0.78rem;
    color: #374151;
    text-transform: uppercase;
    letter-spacing: 0.07em;
}
.streamlit-expanderContent {
    background: #ffffff;
    border: 1px solid #E2E8F0;
    border-top: none;
    border-radius: 0 0 8px 8px;
}
.main details summary,
.main [data-testid="stExpander"] summary {
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.07em;
}

/* ── Metric cards — indigo top band ──────────────────────────────────────── */
[data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    overflow: hidden;
    padding: 0 !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}
[data-testid="stMetric"]::before {
    content: "";
    display: block;
    background: #6366F1;
    height: 4px;
    width: 100%;
}
[data-testid="stMetricLabel"] {
    padding: 0.6rem 1.1rem 0 !important;
    color: #64748B !important;
    font-size: 0.68rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.09em !important;
}
[data-testid="stMetricValue"] {
    padding: 0.1rem 1.1rem 0.75rem !important;
    color: #0F172A !important;
    font-weight: 700 !important;
    font-size: 1.6rem !important;
}
[data-testid="stMetricDelta"] { padding: 0 1.1rem 0.6rem !important; }

/* ── Inputs ──────────────────────────────────────────────────────────────── */
.main input, .main textarea {
    background-color: #ffffff !important;
    color: #0F172A !important;
    -webkit-text-fill-color: #0F172A !important;
    border: 1.5px solid #E2E8F0 !important;
    border-radius: 8px !important;
    font-size: 0.9rem !important;
}
.main input:focus, .main textarea:focus {
    border-color: #6366F1 !important;
    box-shadow: 0 0 0 3px rgba(99,102,241,0.12) !important;
}
.main [data-baseweb="select"],
.main [data-baseweb="select"] > div,
.main [data-baseweb="select"] > div > div,
.main [data-baseweb="select"] > div > div > div,
.main [data-baseweb="select"] > div > div > div > div {
    background-color: #ffffff !important;
    color: #0F172A !important;
    -webkit-text-fill-color: #0F172A !important;
}
.main [data-baseweb="select"] > div:first-child {
    border: 1.5px solid #E2E8F0 !important;
    border-radius: 8px !important;
    min-height: 42px;
}
.main [data-baseweb="select"] svg { color: #64748B !important; fill: #64748B !important; }
[data-baseweb="popover"] ul, [data-baseweb="popover"] li,
[data-baseweb="menu"] ul,   [data-baseweb="menu"] li {
    background-color: #ffffff !important;
    color: #0F172A !important;
    -webkit-text-fill-color: #0F172A !important;
}
[data-baseweb="popover"] li:hover, [data-baseweb="menu"] li:hover {
    background-color: #EEF2FF !important;
}

/* ── Radio / labels ──────────────────────────────────────────────────────── */
.main .stRadio label p, .main .stRadio label { color: #374151 !important; }
.main .stRadio [data-testid="stWidgetLabel"] p { color: #0F172A !important; font-weight: 600; }
.main [data-testid="stWidgetLabel"] p,
.main .stTextInput label,
.main .stTextArea label,
.main .stSelectbox label {
    font-weight: 600 !important;
    color: #1E293B !important;
    font-size: 0.85rem !important;
}

/* ── Captions / alerts ───────────────────────────────────────────────────── */
.stCaption p, [data-testid="stCaptionContainer"] p, .muted-caption {
    color: #64748B !important;
    font-size: 0.8rem;
}
[data-testid="stAlert"] { border-radius: 10px; }

/* ── Previously Generated rows ──────────────────────────────────────────── */
[data-testid="stMarkdown"]:has(.doc-history-marker) ~ [data-testid="stHorizontalBlock"] {
    background: #ffffff;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 0.4rem 0.6rem;
    margin-bottom: 0.4rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    transition: border-color 0.15s, box-shadow 0.15s;
    align-items: center;
}
[data-testid="stMarkdown"]:has(.doc-history-marker) ~ [data-testid="stHorizontalBlock"]:hover {
    border-color: #6366F1;
    box-shadow: 0 2px 10px rgba(99,102,241,0.12);
}
.doc-table-header {
    display: grid;
    grid-template-columns: 1fr 130px 60px 110px;
    gap: 0.5rem;
    padding: 0.35rem 0.75rem 0.5rem;
    font-size: 0.69rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: #94A3B8;
    border-bottom: 2px solid #E2E8F0;
    margin-bottom: 0.5rem;
}

/* ── Sidebar — deep slate ────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background-color: #0F172A !important;
    min-width: 240px !important;
    max-width: 260px !important;
}
[data-testid="stSidebar"] > div:first-child { width: 260px !important; }
[data-testid="stSidebar"] * { color: #CBD5E1 !important; }
[data-testid="stSidebar"] hr { border-color: #1E293B !important; }
[data-testid="stSidebar"] .stMarkdown strong {
    color: #94A3B8 !important;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.07em;
}
[data-testid="stSidebar"] input, [data-testid="stSidebar"] textarea {
    background-color: #1E293B !important;
    border-color: #334155 !important;
    color: #E2E8F0 !important;
    -webkit-text-fill-color: #E2E8F0 !important;
}
[data-testid="stSidebar"] [data-baseweb="select"],
[data-testid="stSidebar"] [data-baseweb="select"] > div,
[data-testid="stSidebar"] [data-baseweb="select"] > div > div,
[data-testid="stSidebar"] [data-baseweb="select"] > div > div > div,
[data-testid="stSidebar"] [data-baseweb="select"] > div > div > div > div {
    background-color: #1E293B !important;
    color: #E2E8F0 !important;
    -webkit-text-fill-color: #E2E8F0 !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] > div:first-child { border-color: #334155 !important; }
[data-testid="stSidebar"] [data-baseweb="select"] svg { color: #94A3B8 !important; fill: #94A3B8 !important; }
[data-testid="stSidebar"] .stCheckbox label,
[data-testid="stSidebar"] .stRadio label { color: #CBD5E1 !important; }
[data-testid="stSidebar"] .stButton > button {
    background: #1E293B; border: 1px solid #334155; color: #CBD5E1;
}
[data-testid="stSidebar"] .stButton > button:hover { border-color: #818CF8; color: #818CF8; }
[data-testid="stSidebar"] .streamlit-expanderHeader,
[data-testid="stSidebar"] [data-testid="stExpander"] summary,
[data-testid="stSidebar"] details summary {
    background-color: #1E293B !important;
    border: 1px solid #334155 !important;
    border-radius: 8px !important;
    color: #CBD5E1 !important;
    -webkit-text-fill-color: #CBD5E1 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.07em !important;
    font-size: 0.72rem !important;
    font-weight: 700 !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary:hover,
[data-testid="stSidebar"] details summary:hover { background-color: #273549 !important; }
[data-testid="stSidebar"] [data-testid="stExpander"] summary span,
[data-testid="stSidebar"] [data-testid="stExpander"] summary p,
[data-testid="stSidebar"] details summary span {
    color: #CBD5E1 !important; -webkit-text-fill-color: #CBD5E1 !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary svg,
[data-testid="stSidebar"] details summary svg { color: #94A3B8 !important; fill: #94A3B8 !important; }
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"],
[data-testid="stSidebar"] [data-testid="stFileUploader"] section,
[data-testid="stSidebar"] [data-testid="stFileUploader"] > div {
    background-color: #1E293B !important;
    border-color: #334155 !important;
    border-radius: 8px !important;
}
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] *,
[data-testid="stSidebar"] [data-testid="stFileUploader"] button {
    color: #94A3B8 !important; -webkit-text-fill-color: #94A3B8 !important;
}
[data-testid="stSidebar"] [data-testid="stFileUploader"] button {
    background-color: #1E293B !important; border-color: #334155 !important;
}
[data-testid="stSidebar"] .sidebar-section-header {
    font-size: 0.67rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.11em !important;
    color: #475569 !important;
    -webkit-text-fill-color: #475569 !important;
    padding: 0.75rem 0 0.35rem !important;
    border-top: 1px solid #1E293B !important;
    margin: 0 !important;
}

/* ── Advisory Response card ──────────────────────────────────────────────── */
.response-header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    border-top: 2px solid #E2E8F0;
    margin: 1.75rem 0 0;
    padding-top: 1.1rem;
}
.response-header::before {
    content: "";
    display: block;
    width: 4px;
    height: 18px;
    background: #6366F1;
    border-radius: 2px;
    flex-shrink: 0;
}
.response-label {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #6366F1;
}
[data-testid="stMarkdown"]:has(.response-header) + [data-testid="stMarkdown"] {
    background: #FAFBFF;
    border: 1px solid #E2E8F0;
    border-left: 4px solid #6366F1;
    border-radius: 0 12px 12px 0;
    padding: 1.4rem 1.75rem 1.5rem;
    margin-top: 0.6rem;
    margin-bottom: 0.5rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar — Title fallback (logo moved to main top nav)
# ---------------------------------------------------------------------------
_logo_path = Path(__file__).parent / "assets" / "venture_logo.png"
_logo_b64 = base64.b64encode(_logo_path.read_bytes()).decode() if _logo_path.exists() else None

# ---------------------------------------------------------------------------
# Sidebar — Company selector
# ---------------------------------------------------------------------------
_COMPANY_DISPLAY_NAMES = {
    "company_a": "Kytosan Bio",
}
_companies_dir = DATA_DIR / "companies"
_discovered = sorted([d.name for d in _companies_dir.iterdir() if d.is_dir()]) if _companies_dir.exists() else []
_company_options = _discovered
_company_labels = [_COMPANY_DISPLAY_NAMES.get(c, c) for c in _company_options]
_company_label = st.sidebar.selectbox("Company", options=_company_labels)
company = _company_options[_company_labels.index(_company_label)]

if st.session_state.get("_last_company") != _company_label:
    st.session_state["_last_company"] = _company_label
    st.session_state["profile_company_name"] = _company_label

# ---------------------------------------------------------------------------
# Sidebar — Company Profile (shared across all tabs)
# ---------------------------------------------------------------------------
st.sidebar.markdown('<div class="sidebar-section-header">Company Profile</div>', unsafe_allow_html=True)

if "profile_company_name" not in st.session_state:
    st.session_state["profile_company_name"] = _company_label

company_name = st.sidebar.text_input("Company name", key="profile_company_name")
stage = st.sidebar.selectbox(
    "Stage", options=["Idea", "Prototype", "Seed", "Growth"], index=1, key="profile_stage"
)
product_type = st.sidebar.text_input(
    "Product type", "Medical Device", key="profile_product_type"
)
regulatory = st.sidebar.text_input("Regulatory area", "FDA / Quality System", key="profile_regulatory")
notes = st.sidebar.text_area(
    "Notes/context", "Small team preparing early quality documentation",
    key="profile_notes", height=80,
)

_profile = {
    "name": company_name,
    "stage": stage,
    "product_type": product_type,
    "regulatory": regulatory,
    "notes": notes,
}
_profile_banner = (
    f'<div class="profile-chip">'
    f'<span class="chip-dot"></span>'
    f'<span>Profile &nbsp;·&nbsp; <strong>{company_name}</strong>'
    f' &nbsp;·&nbsp; {stage} &nbsp;·&nbsp; {product_type}</span>'
    f'</div>'
)

# ---------------------------------------------------------------------------
# Sidebar — Knowledge Sources
# ---------------------------------------------------------------------------
st.sidebar.markdown('<div class="sidebar-section-header">Knowledge &amp; Documents</div>', unsafe_allow_html=True)
with st.sidebar.expander("Knowledge Sources", expanded=True):
    use_founder = st.checkbox("Founder Startup Knowledge", value=True)
    use_company = st.checkbox("Selected Company Data", value=True)
    use_templates = st.checkbox("Shared Templates", value=True)
    use_internet = st.checkbox("Search Internet", value=False, help="Live DuckDuckGo search — adds top web results as context")
    _upload_dest = st.selectbox(
        "Upload destination",
        ["Knowledgebase", "Founder Startup", "Templates", "Company"],
        key="upload_dest",
    )
    if _upload_dest == "Company":
        _existing_companies = sorted([d.name for d in _companies_dir.iterdir() if d.is_dir()]) if _companies_dir.exists() else []
        _upload_company = st.selectbox("Select company", _existing_companies, key="upload_company") if _existing_companies else None
    uploaded_file = st.file_uploader("Upload a document", type=["pdf", "txt", "docx", "pptx", "rtf", "xlsx"])
    if uploaded_file is not None:
        if _upload_dest == "Knowledgebase":
            _upload_dir = DATA_DIR / "parent_company_raw" / "Knowledgebase"
        elif _upload_dest == "Founder Startup":
            _upload_dir = DATA_DIR / "founder_startup"
        elif _upload_dest == "Templates":
            _upload_dir = DATA_DIR / "shared_templates"
        else:
            _upload_dir = _companies_dir / _upload_company if (_upload_dest == "Company" and _upload_company) else DATA_DIR
        _upload_dir.mkdir(parents=True, exist_ok=True)
        saved = file_utils.save_uploaded_file(uploaded_file, _upload_dir)
        st.success(f"Saved to {_upload_dest}: {uploaded_file.name}")
    _index_store = ChromaStore()
    _index_stats = _index_store.get_stats()
    _index_chunk_count = _index_stats.get("chunks", _index_stats.get("documents", 0))
    if _index_chunk_count > 0:
        st.caption(f"Search index: {_index_chunk_count} chunks · {_index_stats.get('type', 'unknown')}")

# ---------------------------------------------------------------------------
# Sidebar — Index Management
# ---------------------------------------------------------------------------
with st.sidebar.expander("Index Management", expanded=False):
    if st.button("Rebuild Document Index"):
        with st.spinner("Rebuilding..."):
            document_loader.build_index(DATA_DIR)
            st.success("Document index rebuilt")

    index_folder = st.text_input("Folder to index", value=str(PARENT_COMPANY_RAW_DIR))
    if st.button("Rebuild Search Index"):
        _index_messages = []

        def _index_progress(msg: str):
            _index_messages.append(msg)

        with st.spinner("Building search index..."):
            _index_result = fast_indexer.index_folder(index_folder, progress_callback=_index_progress)

        st.success(
            f"{_index_result.get('files_processed', 0)} files, "
            f"{_index_result.get('chunks_added', 0)} chunks added, "
            f"{_index_result.get('files_skipped', 0)} skipped"
        )
        with st.expander("Index log"):
            st.text("\n".join(_index_messages))

# ---------------------------------------------------------------------------
# Sidebar — Advanced
# ---------------------------------------------------------------------------
st.sidebar.markdown('<div class="sidebar-section-header">Model Settings</div>', unsafe_allow_html=True)
_llm_choice = st.sidebar.radio(
    "LLM Backend",
    ["Qwen (local)", "Claude (cloud)", "OpenAI (cloud)"],
    index=0,
    help="Qwen runs privately on your machine. Claude and OpenAI are faster but send data to their respective APIs.",
)
_backend_map = {"Qwen (local)": "qwen", "Claude (cloud)": "claude", "OpenAI (cloud)": "openai"}
llm_client.set_backend(_backend_map[_llm_choice])
if _llm_choice == "Claude (cloud)":
    st.sidebar.caption("Model: claude-sonnet-4-6\nRequires ANTHROPIC_API_KEY in .env")
elif _llm_choice == "OpenAI (cloud)":
    st.sidebar.caption("Model: gpt-4o\nRequires OPENAI_API_KEY in .env")
else:
    st.sidebar.caption("Fast model: qwen2.5:3b\nReasoning model: qwen3.5:latest")

debug_mode = st.sidebar.checkbox("Debug Mode", value=False)

# ---------------------------------------------------------------------------
# Main — Tabs
# ---------------------------------------------------------------------------
_logo_el = (
    f'<img src="data:image/png;base64,{_logo_b64}">'
    if _logo_b64
    else '<div class="top-nav-fallback">VS</div>'
)
st.markdown(
    f'<div class="top-nav">'
    f'{_logo_el}'
    f'<div class="top-nav-sep"></div>'
    f'<div class="top-nav-text">'
    f'<span class="top-nav-title">VENTURE STUDIO</span>'
    f'<span class="top-nav-sub">AI Advisor</span>'
    f'</div>'
    f'</div>',
    unsafe_allow_html=True,
)
tab_standard, tab_smart, tab_docs = st.tabs(["Standard Advisor", "Smart Advisor", "Generate Documents"])

# ===== TAB 1: Standard Advisor =====
with tab_standard:
    st.markdown(_profile_banner, unsafe_allow_html=True)
    st.markdown('<div class="breadcrumb">Advisor &rsaquo; Standard</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-header">'
        '<h2>Standard Advisor</h2>'
        '<p>Ask questions and get AI-powered guidance grounded in your company and founder knowledge.</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    user_query = st.text_area(
        "Describe your question or task",
        "Create a first draft checklist for setting up a basic quality management process using my prior startup experience as reference.",
        key="std_query",
        height=100,
    )

    if st.button("Run", key="std_run", type="primary"):
        logger.info("Standard Advisor query: %s", user_query[:80])
        import time

        with st.spinner("Running advisor..."):
            _t0 = time.perf_counter()
            docs = retrieval.retrieve_context(
                query=user_query,
                DATA_DIR=DATA_DIR,
                use_founder=use_founder,
                use_company=use_company,
                use_templates=use_templates,
                selected_company=company,
            )
            if use_internet:
                docs = docs + web_search.search_web(user_query)
            _t_retrieval = time.perf_counter() - _t0

            _t1 = time.perf_counter()
            prompt = prompt_builder.build_prompt(
                company_profile=_profile,
                user_query=user_query,
                retrieved_docs=docs,
            )
            _t_prompt = time.perf_counter() - _t1

            _t2 = time.perf_counter()
            response = llm_client.generate_response(prompt)
            _t_llm = time.perf_counter() - _t2

            output = advisor_engine.format_output(response, docs)

        st.markdown(
            '<div class="response-header"><span class="response-label">Advisory Response</span></div>',
            unsafe_allow_html=True,
        )
        st.markdown(output)

        def _source_category(doc: dict) -> str:
            p = doc.get("path", "").lower()
            if doc.get("_web"):
                return "Web"
            if "founder_startup" in p:
                return "Founder Docs"
            if "shared_templates" in p:
                return "Templates"
            if "companies" in p:
                return "Company Docs"
            return "Other"

        grouped: dict[str, list[str]] = {}
        for d in docs:
            cat = _source_category(d)
            name = d.get("source", d.get("path", "unknown"))
            grouped.setdefault(cat, [])
            if name not in grouped[cat]:
                grouped[cat].append(name)

        if grouped:
            with st.expander("Sources Used", expanded=False):
                for cat, names in grouped.items():
                    st.markdown(f"**{cat}**")
                    for name in names:
                        st.markdown(f"- {name}")

        if debug_mode:
            st.markdown("---")
            st.markdown("**Debug Info**")
            dbg_cols = st.columns(4)
            dbg_cols[0].metric("Docs Retrieved", len(docs))
            dbg_cols[1].metric("Retrieval (s)", f"{_t_retrieval:.1f}")
            dbg_cols[2].metric("Prompt Build (s)", f"{_t_prompt:.1f}")
            dbg_cols[3].metric("LLM (s)", f"{_t_llm:.1f}")
            with st.expander("Prompt sent to LLM", expanded=False):
                st.code(prompt, language="text")
            if docs:
                with st.expander("Raw retrieved chunks", expanded=False):
                    for i, d in enumerate(docs):
                        st.markdown(f"**Chunk {i + 1}** — `{d.get('source', 'unknown')}` ({_source_category(d)})")
                        st.text(d.get("text", "")[:500] + ("…" if len(d.get("text", "")) > 500 else ""))

# ===== TAB 2: Smart Advisor =====
with tab_smart:
    st.markdown(_profile_banner, unsafe_allow_html=True)
    st.markdown('<div class="breadcrumb">Advisor &rsaquo; Smart</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-header">'
        '<h2>Smart Advisor</h2>'
        '<p>Semantic search over the indexed knowledge base. All data is redacted before LLM processing.</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    gr_query = st.text_area(
        "Describe your question or task",
        "What quality management practices from prior experience can we adapt for our new startup?",
        key="gr_query",
        height=100,
    )

    if st.button("Ask Smart Advisor", key="gr_run", type="primary"):
        _sa_response = None
        _sa_meta = None
        logger.info("Smart Advisor query: %s", gr_query[:80])

        with st.status("Running Smart Advisor...", expanded=True) as _sa_status:
            _sa_log = st.empty()

            def _sa_progress(msg: str):
                _sa_log.markdown(f"⏳ {msg}")

            _sa_log.markdown("⏳ Loading documents...")
            _extra_chunks: list = []
            if use_company and company:
                _company_dir = DATA_DIR / "companies" / company
                if _company_dir.exists():
                    for _c in document_loader.load_documents(_company_dir):
                        _c["_category"] = "company"
                        _extra_chunks.append(_c)
            if use_founder:
                _founder_dir = DATA_DIR / "founder_startup"
                if _founder_dir.exists():
                    for _c in document_loader.load_documents(_founder_dir):
                        _c["_category"] = "founder"
                        _extra_chunks.append(_c)
            if use_templates:
                for _c in retrieval.retrieve_context(
                    query=gr_query,
                    DATA_DIR=DATA_DIR,
                    use_founder=False,
                    use_company=False,
                    use_templates=True,
                    selected_company="",
                ):
                    _c["_category"] = "template"
                    _extra_chunks.append(_c)
            if use_internet:
                _sa_log.markdown("⏳ Searching the web...")
                for _c in web_search.search_web(gr_query):
                    _c["_category"] = "web"
                    _extra_chunks.append(_c)

            _sa_response, _sa_meta = smart_advisor.ask(
                gr_query,
                _profile,
                progress_callback=_sa_progress,
                extra_chunks=_extra_chunks,
            )
            _sa_log.markdown("✅ Done")
            _sa_status.update(label="Smart Advisor complete", state="complete", expanded=False)

        st.markdown(
            '<div class="response-header"><span class="response-label">Advisory Response</span></div>',
            unsafe_allow_html=True,
        )
        st.markdown(_sa_response)

        if _sa_meta.get("sources_used"):
            with st.expander(f"Files used ({len(_sa_meta['sources_used'])})", expanded=True):
                for src in _sa_meta["sources_used"]:
                    st.markdown(f"📄 {src}")

        if debug_mode:
            st.markdown("---")
            st.markdown("**Debug Info**")
            debug_cols = st.columns(3)
            debug_cols[0].metric("Chunks Retrieved", _sa_meta["chunks_retrieved"])
            debug_cols[1].metric("Input Chars", _sa_meta["input_chars"])
            debug_cols[2].metric("Compression Applied", str(_sa_meta["compression_applied"]))

# ===== TAB 3: Generate Documents =====
with tab_docs:
    st.markdown(_profile_banner, unsafe_allow_html=True)
    st.markdown('<div class="breadcrumb">Documents &rsaquo; Generate</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-header">'
        '<h2>Generate Documents</h2>'
        '<p>Create regulatory and operational documents using local parent-company knowledge.</p>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="section-label">Document Configuration</div>', unsafe_allow_html=True)

    dc1, dc2 = st.columns(2)
    with dc1:
        doc_type = st.selectbox("Document Type", options=list(DOC_TYPES.keys()), key="doc_type")
        output_format = st.selectbox(
            "Output Format", ["PDF", "Word (.docx)", "Excel (.xlsx)"], key="output_format"
        )
    with dc2:
        gen_mode = st.radio(
            "Generation Mode",
            ["Quick Template (30 sec)", "Comprehensive Document (8–12 min)"],
            key="gen_mode",
        )

    if gen_mode == "Comprehensive Document (8–12 min)":
        st.warning(
            "Comprehensive mode generates each section individually using the parent company "
            "knowledgebase as reference. This takes 8–12 minutes. Keep this tab open."
        )

    if st.button("Generate Document", key="doc_generate", type="primary"):
        progress_placeholder = st.empty()
        progress_log = []
        _doc_sources: list[str] = []

        def _doc_progress(msg):
            progress_log.append(msg)
            progress_placeholder.info(msg)

        is_comprehensive = gen_mode == "Comprehensive Document (8–12 min)"

        # Build extra context from company/founder docs (same as Smart Advisor)
        _doc_extra: list[str] = []
        _doc_extra_sources: list[str] = []
        if use_company and company:
            _company_dir = DATA_DIR / "companies" / company
            if _company_dir.exists():
                for _dc in document_loader.load_documents(_company_dir):
                    if _dc.get("text", "").strip():
                        _doc_extra.append(_dc["text"])
                        _src = _dc.get("source", "")
                        if _src and _src not in _doc_extra_sources:
                            _doc_extra_sources.append(_src)
        if use_founder or use_templates:
            for _dc in retrieval.retrieve_context(
                query=doc_type,
                DATA_DIR=DATA_DIR,
                use_founder=use_founder,
                use_company=False,
                use_templates=use_templates,
                selected_company="",
            ):
                if _dc.get("text", "").strip():
                    _doc_extra.append(_dc["text"])
                    _src = _dc.get("source", "")
                    if _src and _src not in _doc_extra_sources:
                        _doc_extra_sources.append(_src)
        if use_internet:
            for _dc in web_search.search_web(f"{doc_type} {company} medical device regulatory"):
                if _dc.get("text", "").strip():
                    _doc_extra.append(_dc["text"])
                    _src = _dc.get("source", "")
                    if _src and _src not in _doc_extra_sources:
                        _doc_extra_sources.append(_src)

        if output_format == "Word (.docx)":
            with st.spinner(f"Generating {doc_type} as Word document..."):
                doc_bytes, filename = generate_word_doc(
                    doc_type=doc_type,
                    company_profile=_profile,
                    comprehensive=is_comprehensive,
                    progress_callback=_doc_progress,
                    extra_context=_doc_extra or None,
                )
            mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            _doc_sources = [DOC_REFERENCE_PATHS.get(doc_type, IMBED_QM_PATH)] + _doc_extra_sources

        elif output_format == "Excel (.xlsx)":
            with st.spinner(f"Generating {doc_type} as Excel workbook..."):
                doc_bytes, filename = generate_excel_doc(
                    doc_type=doc_type,
                    company_profile=_profile,
                    progress_callback=_doc_progress,
                )
            mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            _doc_sources = ["Static regulatory tables (FDA 21 CFR Part 820, ISO 13485:2016, EU MDR 2017/745)"] + _doc_extra_sources

        else:  # PDF
            if is_comprehensive:
                with st.spinner(f"Generating comprehensive {doc_type} — please wait..."):
                    doc_bytes, filename = generate_comprehensive_pdf(
                        doc_type=doc_type,
                        company_profile=_profile,
                        progress_callback=_doc_progress,
                        extra_context=_doc_extra or None,
                    )
            else:
                with st.spinner(f"Generating {doc_type}..."):
                    doc_bytes, filename = generate_pdf(
                        doc_type=doc_type,
                        company_profile=_profile,
                        context_chunks=[],
                        progress_callback=_doc_progress,
                        extra_context=_doc_extra or None,
                    )
            _doc_sources = [DOC_REFERENCE_PATHS.get(doc_type, IMBED_QM_PATH)] + _doc_extra_sources
            mime_type = "application/pdf"

        progress_placeholder.empty()
        st.success(f"Generated: {filename}")
        st.download_button(
            label=f"Download {doc_type} ({output_format})",
            data=doc_bytes,
            file_name=filename,
            mime=mime_type,
            key="doc_download",
        )

        if _doc_sources:
            with st.expander("Source Documents Referenced", expanded=True):
                for src in _doc_sources:
                    label = Path(src).name if not src.startswith("Static") else src
                    parent = str(Path(src).parent) if not src.startswith("Static") else ""
                    st.markdown(f"**{label}**")
                    if parent:
                        st.caption(parent)
        else:
            st.info("No indexed parent documents were retrieved for this generation.")

    # Previously generated files
    st.markdown(
        '<div style="margin-top:2rem; border-top:2px solid #E5E7EB; padding-top:1.5rem; margin-bottom:0.5rem;">'
        '<div class="section-label">Previously Generated</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    # Header row — must use the same column ratios as the data rows below
    _h_name, _h_date, _h_badge, _h_dl = st.columns([4, 2, 1, 2])
    _h_name.markdown('<p class="section-label" style="margin:0 0 0.25rem;">File Name</p>', unsafe_allow_html=True)
    _h_date.markdown('<p class="section-label" style="margin:0 0 0.25rem;">Created</p>', unsafe_allow_html=True)
    _h_badge.markdown('<p class="section-label" style="margin:0 0 0.25rem;">Type</p>', unsafe_allow_html=True)
    _h_dl.markdown('<p class="section-label" style="margin:0 0 0.25rem;">Download</p>', unsafe_allow_html=True)
    # Marker placed AFTER the header row so card styling only applies to data rows
    st.markdown('<div class="doc-history-marker"></div>', unsafe_allow_html=True)
    report_dir = Path(__file__).parent / "outputs" / "advisor_reports"
    all_files = sorted(
        list(report_dir.glob("*.pdf")) + list(report_dir.glob("*.docx")) + list(report_dir.glob("*.xlsx")),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    if all_files:
        _mime_map = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }
        _type_badge = {".pdf": "PDF", ".docx": "DOCX", ".xlsx": "XLSX"}
        for doc_path in all_files:
            mime = _mime_map.get(doc_path.suffix, "application/octet-stream")
            badge = _type_badge.get(doc_path.suffix, doc_path.suffix.upper())
            date_str = datetime.fromtimestamp(doc_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            col_name, col_date, col_badge, col_dl = st.columns([4, 2, 1, 2])
            col_name.markdown(f"**{doc_path.name}**")
            col_date.caption(date_str)
            col_badge.caption(badge)
            with open(doc_path, "rb") as f:
                col_dl.download_button(
                    label="Download",
                    data=f.read(),
                    file_name=doc_path.name,
                    mime=mime,
                    key=f"prev_{doc_path.name}",
                )
    else:
        st.info("No generated documents yet.")
