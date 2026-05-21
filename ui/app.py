"""
Invoice Hybrid RAG — Document Intelligence UI
Streamlit frontend for uploading, inspecting, and querying invoices/documents.
"""

import base64
import os
import requests
import streamlit as st

API_BASE = os.getenv("API_URL", "http://localhost:8000/api/v1")
API_USERNAME = os.getenv("API_USERNAME", "admin")
API_PASSWORD = os.getenv("API_PASSWORD", "") or os.getenv("UI_PASSWORD", "")
UI_PASSWORD = API_PASSWORD

def _headers() -> dict[str, str]:
    if API_PASSWORD:
        username = API_USERNAME or "admin"
        usr_pwd = f"{username}:{API_PASSWORD}".encode("utf-8")
        b64_creds = base64.b64encode(usr_pwd).decode("utf-8")
        return {"Authorization": f"Basic {b64_creds}"}
    return {}


st.set_page_config(
    page_title="Invoice Hybrid RAG — Document Intelligence",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Password Gate ─────────────────────────────────────────────────────────────
if UI_PASSWORD and not st.session_state.get("authenticated"):
    st.markdown(
        """
        <div style="display:flex;align-items:center;justify-content:center;min-height:60vh">
            <div style="text-align:center;max-width:400px">
                <h1>🔒</h1>
                <h3>Invoice Hybrid RAG — Protected Access</h3>
                <p style="color:#888">Enter the password to continue</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    pwd = st.text_input("Password", type="password", key="login_pwd")
    if st.button("🔓 Enter", type="primary"):
        if pwd == UI_PASSWORD:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("❌ Incorrect password")
    st.stop()

# ── Sidebar nav ───────────────────────────────────────────────────────────────
st.sidebar.title("🧾 Invoice Hybrid RAG")
page = st.sidebar.radio(
    "Navigate",
    ["Upload & Extract", "Browse Documents", "Chat"],
)

# ── Helpers ──────────────────────────────────────────────────────────────────

def fmt_currency(val):
    if val is None:
        return "—"
    return f"${val:,.2f}"


def field_row(label, value, highlight=False):
    color = "#1a9641" if highlight else "#333"
    st.markdown(
        f'<div style="display:flex;justify-content:space-between;padding:4px 0;'
        f'border-bottom:1px solid #f0f0f0">'
        f'<span style="color:#888;font-size:13px">{label}</span>'
        f'<span style="font-weight:600;color:{color};font-size:13px">{value}</span>'
        f"</div>",
        unsafe_allow_html=True,
    )


def render_sources(sources):
    if not sources:
        return
    with st.expander("📚 Sources & Citations", expanded=False):
        for idx, src in enumerate(sources):
            doc_id = src.get('document_id', 'N/A')
            page_num = src.get('page_number', 'N/A')
            text = src.get('text', '')

            if doc_id == "Database":
                st.markdown(f"📊 **Source {idx + 1}**: PostgreSQL Metadata Database")
                text_clean = text.replace("\\n", "\n")
                if "SQL Query executed:" in text_clean and "Result:" in text_clean:
                    parts = text_clean.split("Result:", 1)
                    sql_part = parts[0].replace("SQL Query executed:", "").strip()
                    result_part = parts[1].strip()
                    st.caption("Executed SQL Query:")
                    st.code(sql_part, language="sql")
                    st.caption("Query Output:")
                    st.code(result_part, language="python")
                else:
                    st.info(text_clean)
            else:
                st.markdown(f"📄 **Source {idx + 1}** (Document ID: `{doc_id}` | Page: `{page_num}`)")
                st.info(text)


# ── Page: Upload & Extract ────────────────────────────────────────────────────
if page == "Upload & Extract":
    st.title("📤 Upload & Extract")
    st.caption("Upload one or more PDF business documents (invoices, receipts, etc.) for AI-powered extraction.")

    uploaded = st.file_uploader(
        "Drop PDF files here", type=["pdf"], accept_multiple_files=True
    )

    if uploaded and st.button("🚀 Process Documents", type="primary"):
        with st.spinner("Running LangGraph extraction pipeline…"):
            files = [("files", (f.name, f.read(), "application/pdf")) for f in uploaded]
            try:
                resp = requests.post(f"{API_BASE}/documents/upload", files=files, headers=_headers(), timeout=120)
                resp.raise_for_status()
                docs = resp.json()["data"]
            except Exception as e:
                st.error(f"Upload failed: {e}")
                docs = []

        for doc in docs:
            method_color = {
                "text": "🟢", "hybrid": "🟡", "ocr": "🔴"
            }.get(doc.get("extraction_method", ""), "⚪")

            with st.expander(
                f"{method_color} **{doc.get('filename')}** — "
                f"{doc.get('extraction_method', 'unknown')} extraction | "
                f"{doc.get('chunks_processed', 0)} chunks indexed",
                expanded=True,
            ):
                col1, col2 = st.columns(2)

                with col1:
                    st.subheader("📋 Canonical Data")
                    field_row("Document Type", (doc.get("document_type") or "—").upper())
                    field_row("Document Date", doc.get("doc_date") or "—")
                    field_row("Document Number", doc.get("doc_number") or "—")
                    field_row("Vendor Name", doc.get("vendor_name") or "—")
                    field_row("Client Name", doc.get("client_name") or "—")

                with col2:
                    st.subheader("💰 Financials & Metadata")
                    field_row("Total Amount", fmt_currency(doc.get("total_amount")), highlight=True)
                    field_row("Tax Amount", fmt_currency(doc.get("tax_amount")))
                    field_row("File Size", f"{doc.get('file_size_bytes', 0) / 1024:.1f} KB" if doc.get('file_size_bytes') else "—")
                    field_row("Page Count", str(doc.get("page_count") or "—"))

                # Render dynamic table
                tables = doc.get("tables")
                if tables and isinstance(tables, list):
                    st.subheader("📦 Line Items Table")
                    import pandas as pd
                    df = pd.DataFrame(tables)
                    st.dataframe(df, use_container_width=True)

                # Render dynamic extras
                extras = doc.get("others") or {}
                if extras:
                    st.subheader("🔍 Extra Fields")
                    for k, v in extras.items():
                        field_row(k, str(v))

                st.markdown("---")
                st.caption(f"Document ID: `{doc.get('id')}`")

# ── Page: Browse Documents ────────────────────────────────────────────────────
elif page == "Browse Documents":
    st.title("📂 Browse & Correct Documents")
    st.caption("Human-in-the-Loop Verification: Select a document to review extracted data side-by-side with the original PDF. Correct any errors, edit tables or add/delete custom fields, and save changes.")

    with st.spinner("Loading stored documents…"):
        try:
            resp = requests.get(f"{API_BASE}/documents", params={"limit": 100, "offset": 0}, headers=_headers(), timeout=15)
            resp.raise_for_status()
            docs = resp.json()["data"]
        except Exception as e:
            st.error(f"Failed to fetch documents: {e}")
            docs = []

    if not docs:
        st.info("No documents found. Go to 'Upload & Extract' to add some.")
    else:
        # Create a selectbox to pick a document
        doc_options = {
            f"🧾 {doc.get('filename')} — {doc.get('vendor_name') or 'Unknown'} ({(doc.get('document_type') or 'unknown').upper()} | {doc.get('doc_date') or '—'})": doc
            for doc in docs
        }
        selected_key = st.selectbox("Select document to review:", list(doc_options.keys()))
        selected_doc = doc_options[selected_key]

        st.markdown("---")

        col1, col2 = st.columns([1, 1])

        with col1:
            st.subheader("📝 Edit Extracted Metadata")

            # Canonical Form fields
            document_type = st.text_input("Document Type", value=selected_doc.get("document_type") or "")
            doc_date = st.text_input("Document Date (YYYY-MM-DD)", value=selected_doc.get("doc_date") or "")
            doc_number = st.text_input("Document Number", value=selected_doc.get("doc_number") or "")
            vendor_name = st.text_input("Vendor Name", value=selected_doc.get("vendor_name") or "")
            client_name = st.text_input("Client Name", value=selected_doc.get("client_name") or "")

            # Financials
            total_amount = st.number_input("Total Amount", value=float(selected_doc.get("total_amount")) if selected_doc.get("total_amount") is not None else 0.0, step=0.01)
            tax_amount = st.number_input("Tax Amount", value=float(selected_doc.get("tax_amount")) if selected_doc.get("tax_amount") is not None else 0.0, step=0.01)

            # Editable Line Items (Tables)
            st.subheader("📦 Line Items / Tables")
            import pandas as pd
            tables_list = selected_doc.get("tables") or []
            df_tables = pd.DataFrame(tables_list)
            if df_tables.empty:
                df_tables = pd.DataFrame([{"description": "", "qty": 0, "unit_price": 0.0, "total": 0.0}])
            
            edited_df = st.data_editor(
                df_tables, 
                num_rows="dynamic", 
                use_container_width=True, 
                key=f"tables_editor_{selected_doc.get('id')}"
            )

            # Dynamic Extras
            st.subheader("🔍 Extra Fields")
            others = dict(selected_doc.get("others") or {})
            
            temp_key = f"temp_extras_{selected_doc.get('id')}"
            if temp_key not in st.session_state:
                st.session_state[temp_key] = {}
                
            all_extras = {**others, **st.session_state[temp_key]}
            
            updated_extras = {}
            keys_to_delete = []
            
            if all_extras:
                for key, val in all_extras.items():
                    col_k, col_v, col_del = st.columns([3, 6, 1])
                    with col_k:
                        st.markdown(f"**{key}**")
                    with col_v:
                        updated_extras[key] = st.text_input(
                            f"Value for {key}", 
                            value=str(val), 
                            key=f"val_{key}_{selected_doc.get('id')}", 
                            label_visibility="collapsed"
                        )
                    with col_del:
                        if st.button("🗑️", key=f"del_{key}_{selected_doc.get('id')}"):
                            keys_to_delete.append(key)
            else:
                st.info("No extra fields. Add custom keys below.")

            # Apply deletions
            if keys_to_delete:
                for k in keys_to_delete:
                    if k in updated_extras:
                        del updated_extras[k]
                    if k in st.session_state[temp_key]:
                        del st.session_state[temp_key][k]
                st.rerun()

            st.markdown("**➕ Add Custom Key-Value**")
            add_col1, add_col2, add_col3 = st.columns([3, 6, 1])
            with add_col1:
                new_k = st.text_input("Field Key", key=f"new_k_{selected_doc.get('id')}")
            with add_col2:
                new_v = st.text_input("Field Value", key=f"new_v_{selected_doc.get('id')}")
            with add_col3:
                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                if st.button("➕", key=f"add_btn_{selected_doc.get('id')}"):
                    if new_k:
                        st.session_state[temp_key][new_k] = new_v
                        st.rerun()

            st.markdown("---")

            if st.button("💾 Save Corrections", type="primary"):
                # Construct tables list of dicts from edited_df
                df_cleaned = edited_df.dropna(how='all')
                tables_update = []
                for _, row in df_cleaned.iterrows():
                    row_dict = row.to_dict()
                    if any(str(v).strip() != "" for v in row_dict.values()):
                        # Convert column types if possible
                        if "qty" in row_dict and row_dict["qty"] is not None:
                            try:
                                row_dict["qty"] = int(row_dict["qty"])
                            except ValueError:
                                pass
                        if "unit_price" in row_dict and row_dict["unit_price"] is not None:
                            try:
                                row_dict["unit_price"] = float(row_dict["unit_price"])
                            except ValueError:
                                pass
                        if "total" in row_dict and row_dict["total"] is not None:
                            try:
                                row_dict["total"] = float(row_dict["total"])
                            except ValueError:
                                pass
                        tables_update.append(row_dict)

                updates = {
                    "document_type": document_type,
                    "doc_date": doc_date or None,
                    "doc_number": doc_number or None,
                    "vendor_name": vendor_name or None,
                    "client_name": client_name or None,
                    "total_amount": float(total_amount) if total_amount is not None else None,
                    "tax_amount": float(tax_amount) if tax_amount is not None else None,
                    "tables": tables_update,
                    "extras": updated_extras
                }

                with st.spinner("Saving corrections to database…"):
                    try:
                        patch_resp = requests.patch(
                            f"{API_BASE}/documents/{selected_doc.get('id')}",
                            json=updates,
                            headers=_headers(),
                            timeout=15
                        )
                        patch_resp.raise_for_status()
                        if temp_key in st.session_state:
                            del st.session_state[temp_key]
                        st.success("✅ Changes saved successfully! Reloading page…")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to save corrections: {e}")

        with col2:
            st.subheader("📄 Original Document PDF")
            pdf_url = f"{API_BASE}/documents/{selected_doc.get('id')}/pdf"

            try:
                pdf_resp = requests.get(pdf_url, headers=_headers())
                if pdf_resp.status_code == 200:
                    base64_pdf = base64.b64encode(pdf_resp.content).decode("utf-8")
                    pdf_iframe = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800px" style="border: none;"></iframe>'
                    st.markdown(pdf_iframe, unsafe_allow_html=True)
                else:
                    st.warning("⚠️ Could not load PDF file from API")
            except Exception as e:
                st.error(f"Error loading PDF: {e}")

# ── Page: Chat (Unified) ─────────────────────────────────────────────────────────
elif page == "Chat":
    st.title("💬 Chat with Your Documents & Data")
    st.caption("Ask natural language questions. The AI autonomously decides whether to search vectors or run a SQL query over your structured data.")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sources"):
                render_sources(msg["sources"])

    question = st.chat_input("Ask something about your invoices or aggregated data…")
    if question:
        st.session_state.chat_history.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Thinking (Routing to SQL or Vectors)…"):
                try:
                    resp = requests.post(
                        f"{API_BASE}/documents/chat",
                        json={"question": question},
                        headers=_headers(),
                        timeout=60,
                    )
                    resp.raise_for_status()
                    data = resp.json()["data"]
                    answer = data.get("response", "")
                    sources = data.get("sources", [])
                except Exception as e:
                    answer = f"❌ Error: {e}"
                    sources = []

            st.markdown(answer)
            if sources:
                render_sources(sources)

            st.session_state.chat_history.append({"role": "assistant", "content": answer, "sources": sources})
