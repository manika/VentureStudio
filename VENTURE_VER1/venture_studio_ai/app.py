import base64
from pathlib import Path

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
# Logo
# ---------------------------------------------------------------------------
_logo_path = Path(__file__).parent / "assets" / "logo.svg"
if _logo_path.exists():
    _logo_b64 = base64.b64encode(_logo_path.read_bytes()).decode()
    _logo_html = (
        f'<img src="data:image/svg+xml;base64,{_logo_b64}" '
        f'style="width:100%; max-width:320px; margin-bottom:8px;">'
    )
else:
    _logo_html = f"<h2>{APP_TITLE}</h2>"

st.set_page_config(page_title=APP_TITLE, layout="wide")
st.markdown(_logo_html, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar — Settings (original)
# ---------------------------------------------------------------------------
st.sidebar.header("Settings")

# Auto-discover company folders; map folder names to display names
_COMPANY_DISPLAY_NAMES = {
    "company_a": "Kytosan Bio",
    "Example Med Device Co": "Example Med Device Co",
}
_companies_dir = DATA_DIR / "companies"
_discovered = sorted([d.name for d in _companies_dir.iterdir() if d.is_dir()]) if _companies_dir.exists() else []
_company_options = ["Example Med Device Co"] + _discovered
_company_labels = [_COMPANY_DISPLAY_NAMES.get(c, c) for c in _company_options]
_company_label = st.sidebar.selectbox("Company", options=_company_labels)
company = _company_options[_company_labels.index(_company_label)]

# When the selected company changes, reset the company name fields so they
# reflect the new selection rather than keeping a stale manually-typed value.
if st.session_state.get("_last_company") != _company_label:
    st.session_state["_last_company"] = _company_label
    st.session_state["std_company_name"] = _company_label
    st.session_state["gr_company_name"] = _company_label
    st.session_state["doc_company_name"] = _company_label
use_founder = st.sidebar.checkbox("Founder Startup Knowledge", value=True)
use_company = st.sidebar.checkbox("Selected Company Data", value=True)
use_templates = st.sidebar.checkbox("Shared Templates", value=True)
mode = st.sidebar.selectbox(
    "Mode",
    options=["Ask a Question", "Generate Template", "Analyze Document", "Strategic Advice"],
)
uploaded_file = st.sidebar.file_uploader("Upload a document", type=["pdf", "txt", "docx"])
if uploaded_file is not None:
    saved = file_utils.save_uploaded_file(uploaded_file, DATA_DIR)
    st.sidebar.success(f"Saved {saved}")

if st.sidebar.button("Rebuild Index"):
    with st.spinner("Rebuilding index..."):
        document_loader.build_index(DATA_DIR)
        st.sidebar.success("Index rebuilt")

# ---------------------------------------------------------------------------
# Sidebar — Search Index
# ---------------------------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.header("Search Index")
index_folder = st.sidebar.text_input("Folder to Index", value=str(PARENT_COMPANY_RAW_DIR))

if st.sidebar.button("Build / Rebuild Index"):
    _index_messages = []

    def _index_progress(msg: str):
        _index_messages.append(msg)

    with st.spinner("Building search index..."):
        _index_result = fast_indexer.index_folder(index_folder, progress_callback=_index_progress)

    st.sidebar.success(
        f"Index built: {_index_result.get('files_processed', 0)} files, "
        f"{_index_result.get('chunks_added', 0)} chunks added, "
        f"{_index_result.get('files_skipped', 0)} skipped"
    )
    with st.sidebar.expander("Index log"):
        st.text("\n".join(_index_messages))

# Show index stats (chunk count from ChromaStore)
_index_store = ChromaStore()
_index_stats = _index_store.get_stats()
_index_chunk_count = _index_stats.get("chunks", _index_stats.get("documents", 0))
if _index_chunk_count > 0:
    st.sidebar.markdown(f"**Index:** {_index_chunk_count} chunks | {_index_stats.get('type', 'unknown')}")

debug_mode = st.sidebar.checkbox("Debug Mode", value=False)


# ---------------------------------------------------------------------------
# Main — Tabs
# ---------------------------------------------------------------------------
tab_standard, tab_smart, tab_docs = st.tabs(["Standard Advisor", "Smart Advisor", "Generate Documents"])

# ===== TAB 1: Standard Advisor (original content) =====
with tab_standard:
    st.subheader("Company Info")
    col1, col2 = st.columns(2)
    with col1:
        if "std_company_name" not in st.session_state:
            st.session_state["std_company_name"] = _company_label
        company_name = st.text_input("Company name", key="std_company_name")
        stage = st.selectbox(
            "Stage", options=["Idea", "Prototype", "Seed", "Growth"], index=1, key="std_stage"
        )
    with col2:
        product_type = st.text_input(
            "Product type", "Software-enabled medical device", key="std_product_type"
        )
        regulatory = st.text_input("Regulatory area", "FDA / Quality System", key="std_regulatory")

    notes = st.text_area(
        "Notes/context", "Small team preparing early quality documentation", key="std_notes"
    )

    st.subheader("User Question / Task")
    user_query = st.text_area(
        "Describe your question or task",
        "Create a first draft checklist for setting up a basic quality management process using my prior startup experience as reference.",
        key="std_query",
    )

    if st.button("Run", key="std_run"):
        with st.spinner("Running advisor..."):
            docs = retrieval.retrieve_context(
                query=user_query,
                DATA_DIR=DATA_DIR,
                use_founder=use_founder,
                use_company=use_company,
                use_templates=use_templates,
            )
            prompt = prompt_builder.build_prompt(
                company_profile={
                    "name": company_name,
                    "stage": stage,
                    "product_type": product_type,
                    "regulatory": regulatory,
                    "notes": notes,
                },
                user_query=user_query,
                retrieved_docs=docs,
            )
            response = llm_client.generate_response(prompt)
            output = advisor_engine.format_output(response, docs)
            st.markdown(output)

# ===== TAB 2: Smart Advisor =====
with tab_smart:
    st.subheader("Smart Advisor")
    st.caption(
        "Semantic search over the indexed parent company knowledge base. "
        "All data is redacted before LLM processing. Single Qwen call per query."
    )

    # Company profile for Smart Advisor
    st.markdown("#### Company Profile")
    gc1, gc2 = st.columns(2)
    with gc1:
        if "gr_company_name" not in st.session_state:
            st.session_state["gr_company_name"] = _company_label
        gr_company_name = st.text_input("Company name", key="gr_company_name")
        gr_stage = st.selectbox(
            "Stage", options=["Idea", "Prototype", "Seed", "Growth"], index=1, key="gr_stage"
        )
    with gc2:
        gr_product_type = st.text_input(
            "Product type", "Software-enabled medical device", key="gr_product_type"
        )
        gr_regulatory = st.text_input(
            "Regulatory area", "FDA / Quality System", key="gr_regulatory"
        )

    gr_notes = st.text_area(
        "Notes/context", "Small team preparing early quality documentation", key="gr_notes"
    )

    st.markdown("#### Advisory Question")
    gr_query = st.text_area(
        "Describe your question or task",
        "What quality management practices from prior experience can we adapt for our new startup?",
        key="gr_query",
    )

    if st.button("Ask Smart Advisor", key="gr_run"):
        with st.spinner("Searching knowledge base and generating response..."):
            gr_profile = {
                "name": gr_company_name,
                "stage": gr_stage,
                "product_type": gr_product_type,
                "regulatory": gr_regulatory,
                "notes": gr_notes,
            }
            sa_response, sa_meta = smart_advisor.ask(gr_query, gr_profile)

        st.markdown(sa_response)

        if debug_mode:
            st.markdown("---")
            st.markdown("**Debug Info**")
            debug_cols = st.columns(3)
            debug_cols[0].metric("Chunks Retrieved", sa_meta["chunks_retrieved"])
            debug_cols[1].metric("Input Chars", sa_meta["input_chars"])
            debug_cols[2].metric("Compression Applied", str(sa_meta["compression_applied"]))
            if sa_meta["sources_used"]:
                st.caption("Sources: " + ", ".join(sa_meta["sources_used"]))

# ===== TAB 3: Generate Documents =====
with tab_docs:
    st.subheader("Generate Documents")
    st.caption("Generate professional regulatory documents as downloadable PDFs using parent company knowledge + AI.")

    dc1, dc2 = st.columns(2)
    with dc1:
        if "doc_company_name" not in st.session_state:
            st.session_state["doc_company_name"] = _company_label
        doc_company_name = st.text_input("Company name", key="doc_company_name")
        doc_stage = st.selectbox("Stage", options=["Idea", "Prototype", "Seed", "Growth"],
                                  index=1, key="doc_stage")
        doc_type = st.selectbox("Document Type", options=list(DOC_TYPES.keys()), key="doc_type")
        output_format = st.selectbox(
            "Output Format", ["PDF", "Word (.docx)", "Excel (.xlsx)"], key="output_format"
        )
    with dc2:
        doc_product = st.text_input("Product type", "Antimicrobial wound dressing (Chitosan)",
                                     key="doc_product")
        doc_regulatory = st.text_input("Regulatory scope",
                                        "FDA 21 CFR Part 820 / ISO 13485 / EU MDR",
                                        key="doc_regulatory")

    doc_notes = st.text_area("Additional context",
                              "Class II medical device. Sterile, single-use wound dressing.",
                              key="doc_notes")

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
        profile = {
            "name": doc_company_name,
            "stage": doc_stage,
            "product_type": doc_product,
            "regulatory": doc_regulatory,
            "notes": doc_notes,
        }

        progress_placeholder = st.empty()
        progress_log = []
        _doc_sources: list[str] = []  # source files used during generation

        def _doc_progress(msg):
            progress_log.append(msg)
            progress_placeholder.info(msg)

        is_comprehensive = gen_mode == "Comprehensive Document (8–12 min)"

        if output_format == "Word (.docx)":
            with st.spinner(f"Generating {doc_type} as Word document..."):
                doc_bytes, filename = generate_word_doc(
                    doc_type=doc_type,
                    company_profile=profile,
                    comprehensive=is_comprehensive,
                    progress_callback=_doc_progress,
                )
            mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            if is_comprehensive:
                _doc_sources = [DOC_REFERENCE_PATHS.get(doc_type, IMBED_QM_PATH)]

        elif output_format == "Excel (.xlsx)":
            with st.spinner(f"Generating {doc_type} as Excel workbook..."):
                doc_bytes, filename = generate_excel_doc(
                    doc_type=doc_type,
                    company_profile=profile,
                    progress_callback=_doc_progress,
                )
            mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            _doc_sources = ["Static regulatory tables (FDA 21 CFR Part 820, ISO 13485:2016, EU MDR 2017/745)"]

        else:  # PDF
            if is_comprehensive:
                with st.spinner(f"Generating comprehensive {doc_type} — please wait..."):
                    doc_bytes, filename = generate_comprehensive_pdf(
                        doc_type=doc_type,
                        company_profile=profile,
                        progress_callback=_doc_progress,
                    )
                _doc_sources = [DOC_REFERENCE_PATHS.get(doc_type, IMBED_QM_PATH)]
            else:
                with st.spinner(f"Generating {doc_type}..."):
                    _chroma_results = []
                    try:
                        store = ChromaStore()
                        _chroma_results = store.query(
                            f"{doc_type} {doc_product} {doc_regulatory}", top_k=5
                        )
                    except Exception:
                        pass
                    context_chunks = [r.get("text", "") for r in _chroma_results if r.get("text")]
                    doc_bytes, filename = generate_pdf(
                        doc_type=doc_type,
                        company_profile=profile,
                        context_chunks=context_chunks,
                        progress_callback=_doc_progress,
                    )
                # Collect unique source paths from ChromaStore results
                seen = set()
                for r in _chroma_results:
                    src = r.get("source") or r.get("path", "")
                    if src and src not in seen:
                        seen.add(src)
                        _doc_sources.append(src)
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

        # Show referenced source documents
        if _doc_sources:
            with st.expander("Source Documents Referenced", expanded=True):
                for src in _doc_sources:
                    from pathlib import Path as _Path
                    label = _Path(src).name if not src.startswith("Static") else src
                    parent = str(_Path(src).parent) if not src.startswith("Static") else ""
                    st.markdown(f"**{label}**")
                    if parent:
                        st.caption(parent)
        else:
            st.info("No indexed parent documents were retrieved for this generation.")

    # Previously generated files
    st.markdown("---")
    st.markdown("#### Previously Generated")
    report_dir = Path(__file__).parent / "outputs" / "advisor_reports"
    all_files = sorted(
        list(report_dir.glob("*.pdf")) + list(report_dir.glob("*.docx")) + list(report_dir.glob("*.xlsx")),
        reverse=True,
    )
    if all_files:
        _mime_map = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }
        for doc_path in all_files:
            mime = _mime_map.get(doc_path.suffix, "application/octet-stream")
            with open(doc_path, "rb") as f:
                st.download_button(
                    label=f"Download: {doc_path.name}",
                    data=f.read(),
                    file_name=doc_path.name,
                    mime=mime,
                    key=f"prev_{doc_path.name}",
                )
    else:
        st.info("No generated documents yet.")
