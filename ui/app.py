"""
Tax Invoice RAG — Document Intelligence UI
Streamlit frontend for uploading, inspecting, and querying invoices/certificates.
"""


import requests
import streamlit as st

import os

import base64

API_BASE = os.getenv("API_URL", "http://localhost:8000/api/v1")
API_USERNAME = os.getenv("API_USERNAME", "auxis")
API_PASSWORD = os.getenv("API_PASSWORD", "") or os.getenv("UI_PASSWORD", "")
UI_PASSWORD = API_PASSWORD

def _headers() -> dict[str, str]:
    if API_PASSWORD:
        username = API_USERNAME or "auxis"
        usr_pwd = f"{username}:{API_PASSWORD}".encode("utf-8")
        b64_creds = base64.b64encode(usr_pwd).decode("utf-8")
        return {"Authorization": f"Basic {b64_creds}"}
    return {}


st.set_page_config(
    page_title="Tax Invoice RAG — Document Intelligence",
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
                <h3>Tax Invoice RAG — Protected Access</h3>
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
st.sidebar.title("🧾 Tax Invoice RAG")
page = st.sidebar.radio(
    "Navigate",
    ["Upload & Extract", "Browse Documents", "Chat"],
)

# ── Helpers ──────────────────────────────────────────────────────────────────

def fmt_currency(val):
    if val is None:
        return "—"
    return f"${val:,.0f}"


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
                # Normalize double backslashes which can occur from JSON responses
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
    st.caption("Upload one or more PDF invoices/withholding certificates for AI-powered extraction.")

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
                    st.subheader("📋 Identity")
                    field_row("Form type", doc.get("form_type") or "—")
                    field_row("Form number", doc.get("form_number") or "—")
                    field_row("Tax year", doc.get("tax_year") or "—")
                    field_row("Employer (NIT)", doc.get("nit_employer") or "—")
                    field_row("Employer name", doc.get("employer_name") or "—")
                    field_row("Employee ID", doc.get("employee_document_id") or "—")
                    field_row("Employee name", doc.get("employee_name") or "—")
                    field_row("Location", doc.get("location") or "—")
                    field_row("Period start", doc.get("period_start") or "—")
                    field_row("Period end", doc.get("period_end") or "—")

                with col2:
                    st.subheader("💰 Financials")
                    field_row("Total gross income", fmt_currency(doc.get("total_gross_income")), highlight=True)
                    field_row("Salary payments", fmt_currency(doc.get("salary_payments")))
                    field_row("Social benefits", fmt_currency(doc.get("social_benefits")))
                    field_row("Other income", fmt_currency(doc.get("other_income_payments")))
                    field_row("Health contributions", fmt_currency(doc.get("health_contributions")))
                    field_row("Pension contributions", fmt_currency(doc.get("pension_contributions")))
                    field_row("Avg monthly income", fmt_currency(doc.get("average_monthly_income")))
                    field_row("Income tax withheld", fmt_currency(doc.get("income_tax_withheld")), highlight=True)
                    field_row("Total annual withholding", fmt_currency(doc.get("total_annual_withholding")))

                st.markdown("---")
                st.caption(f"Document ID: `{doc.get('id')}`")

# ── Page: Browse Documents ────────────────────────────────────────────────────
elif page == "Browse Documents":
    st.title("📂 Browse & Correct Documents")
    st.caption("Human-in-the-Loop Verification: Select a document to review extracted data side-by-side with the original PDF. Correct any errors and save changes.")

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
            f"🧾 {doc.get('filename')} — {doc.get('employee_name') or 'Unknown'} ({doc.get('tax_year') or '—'})": doc
            for doc in docs
        }
        selected_key = st.selectbox("Select document to review:", list(doc_options.keys()))
        selected_doc = doc_options[selected_key]

        st.markdown("---")

        col1, col2 = st.columns([1, 1])

        with col1:
            st.subheader("📝 Edit Extracted Metadata")

            # Form fields
            form_type = st.text_input("Form Type", value=selected_doc.get("form_type") or "")
            tax_year = st.number_input("Tax Year", value=int(selected_doc.get("tax_year")) if selected_doc.get("tax_year") else 2026, step=1)
            nit_employer = st.text_input("Employer NIT", value=selected_doc.get("nit_employer") or "")
            employer_name = st.text_input("Employer Name", value=selected_doc.get("employer_name") or "")
            employee_name = st.text_input("Employee Name", value=selected_doc.get("employee_name") or "")

            # Financials
            total_gross = st.number_input("Total Gross Income", value=float(selected_doc.get("total_gross_income")) if selected_doc.get("total_gross_income") is not None else 0.0, step=1000.0)
            tax_withheld = st.number_input("Income Tax Withheld", value=float(selected_doc.get("income_tax_withheld")) if selected_doc.get("income_tax_withheld") is not None else 0.0, step=1000.0)

            # Extras
            with st.expander("Secondary Fields & Deductions"):
                form_number = st.text_input("Form Number", value=selected_doc.get("form_number") or "")
                employee_doc_id = st.text_input("Employee Doc ID", value=selected_doc.get("employee_document_id") or "")
                location = st.text_input("Location", value=selected_doc.get("location") or "")
                salary = st.number_input("Salary Payments", value=float(selected_doc.get("salary_payments")) if selected_doc.get("salary_payments") is not None else 0.0)
                benefits = st.number_input("Social Benefits", value=float(selected_doc.get("social_benefits")) if selected_doc.get("social_benefits") is not None else 0.0)
                other_inc = st.number_input("Other Income", value=float(selected_doc.get("other_income_payments")) if selected_doc.get("other_income_payments") is not None else 0.0)
                health = st.number_input("Health Contributions", value=float(selected_doc.get("health_contributions")) if selected_doc.get("health_contributions") is not None else 0.0)
                pension = st.number_input("Pension Contributions", value=float(selected_doc.get("pension_contributions")) if selected_doc.get("pension_contributions") is not None else 0.0)
                avg_inc = st.number_input("Average Monthly Income", value=float(selected_doc.get("average_monthly_income")) if selected_doc.get("average_monthly_income") is not None else 0.0)
                total_withheld = st.number_input("Total Annual Withholding", value=float(selected_doc.get("total_annual_withholding")) if selected_doc.get("total_annual_withholding") is not None else 0.0)

            if st.button("💾 Save Corrections", type="primary"):
                updates = {
                    "form_type": form_type,
                    "tax_year": tax_year,
                    "nit_employer": nit_employer,
                    "employer_name": employer_name,
                    "employee_name": employee_name,
                    "total_gross_income": total_gross,
                    "income_tax_withheld": tax_withheld,
                    "form_number": form_number,
                    "employee_document_id": employee_doc_id,
                    "location": location,
                    "salary_payments": salary,
                    "social_benefits": benefits,
                    "other_income_payments": other_inc,
                    "health_contributions": health,
                    "pension_contributions": pension,
                    "average_monthly_income": avg_inc,
                    "total_annual_withholding": total_withheld,
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
                        st.success("✅ Changes saved successfully! Reloading page…")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to save corrections: {e}")

        with col2:
            st.subheader("📄 Original Document PDF")
            pdf_url = f"{API_BASE}/documents/{selected_doc.get('id')}/pdf"

            try:
                import base64
                pdf_resp = requests.get(pdf_url, headers=_headers())
                if pdf_resp.status_code == 200:
                    base64_pdf = base64.b64encode(pdf_resp.content).decode("utf-8")
                    pdf_iframe = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="700px" style="border: none;"></iframe>'
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
