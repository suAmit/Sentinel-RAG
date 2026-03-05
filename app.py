import os

import requests
import streamlit as st
from dotenv import load_dotenv

from src.ai_agents import SOCAnalyst

load_dotenv()

# --- PAGE CONFIG ---
st.set_page_config(page_title="Sentinel SOC Dashboard", layout="wide", page_icon="🛡️")

# --- SIDEBAR: CONFIGURATION ---
with st.sidebar:
    st.title("🛡️ Sentinel Settings")

    # Provider Selection
    ai_mode = st.radio("AI Provider", ["Cloud (Gemini)", "Local (Ollama)"])
    mode_key = "cloud" if "Cloud" in ai_mode else "local"

    grounding_threshold = st.slider(
        "Grounding Threshold (Similarity)",
        min_value=0.0,
        max_value=1.0,
        value=0.50,
        step=0.05,
        help="Higher values require closer matches to the log database.",
    )

    # Get API Key from .env or manual input
    env_key = os.getenv("GEMINI_API_KEY", "")
    gemini_key = env_key
    # gemini_key = st.text_input("Gemini API Key", value=env_key, type="password")

    # st.divider()

    # # LOG UPLOADER
    # st.subheader("📥 Data Ingestion")
    # uploaded_file = st.file_uploader(
    #     "Upload Security Logs (JSON/LOG)", type=["json", "log"]
    # )
    #
    # if uploaded_file:
    #     if st.button("Index Uploaded File"):
    #         with st.spinner("Triggering background worker..."):
    #             # Save file to disk
    #             save_path = os.path.join("data/raw_logs", uploaded_file.name)
    #             os.makedirs("data/raw_logs", exist_ok=True)
    #             with open(save_path, "wb") as f:
    #                 f.write(uploaded_file.getbuffer())
    #
    #             # Trigger Inngest Event via FastAPI worker
    #             try:
    #                 # Pointing to your FastAPI/Inngest worker port
    #                 payload = {
    #                     "name": "logs/uploaded",
    #                     "data": {"file_path": save_path},
    #                 }
    #                 # Send event to the Inngest local server
    #                 response = requests.post(
    #                     "http://localhost:8288/e/EVENT_KEY_NOT_NEEDED_IN_DEV",
    #                     json=payload,
    #                 )
    #
    #                 if response.status_code == 200:
    #                     st.success(f"Started indexing: {uploaded_file.name}")
    #                     st.info("Check Inngest Dashboard (Port 8288) for progress.")
    #                 else:
    #                     st.error(
    #                         "Failed to trigger worker. Is the Inngest Dev Server running?"
    #                     )
    #             except Exception as e:
    #                 st.error(f"Error connecting to worker: {e}")

# --- MAIN DASHBOARD ---
st.title("Sentinel RAG Intelligence")
query = st.text_input(
    "Investigate security event...",
    placeholder="e.g., Show me brute force attempts on admin",
)

if st.button("Run Investigation"):
    if mode_key == "cloud" and not gemini_key:
        st.error("Missing Gemini API Key!")
    else:
        with st.spinner("Searching logs and generating report..."):
            try:
                analyst = SOCAnalyst(mode=mode_key, api_key=gemini_key)

                # Get Context & Score
                raw_context, score = analyst._get_context_with_score(
                    query, threshold=grounding_threshold
                )

                # Generate AI Report
                report = analyst.investigate(query, threshold=grounding_threshold)

                # --- DISPLAY UI COMPONENTS ---
                col_report, col_stats = st.columns([3, 1])
                with col_report:
                    st.markdown("### 🤖 AI Forensic Report")
                    st.markdown(report)

                with col_stats:
                    st.markdown("### 📊 Metrics")
                    color = "normal" if score >= grounding_threshold else "inverse"
                    st.metric(
                        label="Match Confidence",
                        value=f"{score:.2%}",
                        delta=f"{score - grounding_threshold:+.2f} vs Threshold",
                        delta_color=color,
                    )

                    st.markdown("### 📄 Source Logs")
                    if raw_context:
                        st.caption(f"```\n{raw_context[:500]}...\n```")
                    else:
                        st.warning("No logs passed the threshold.")

                # --- TRIGGER INNGEST AUDIT EVENT ---
                audit_payload = {
                    "name": "audit/question_asked",
                    "data": {
                        "question": query,
                        "answer": report[:1000],  # Capture more of the answer for audit
                        "score": float(score),  # Ensure it's a standard float for JSON
                        "has_context": bool(raw_context),
                        "metadata": "Extracted from Qdrant",
                    },
                }

                try:
                    requests.post(
                        "http://localhost:8288/e/NON_PROD_KEY",
                        json=audit_payload,
                        timeout=1,
                    )
                except Exception:
                    # We pass silently so the user doesn't see a "Logging failed" error
                    pass

            except Exception as e:
                st.error(f"Traceback error: {e}")
                st.info("Ensure Qdrant is running and data is indexed.")
