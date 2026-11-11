"""PDF question-answering app with per-user saved chat history."""

import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

from src.database import (
    clear_auth_session,
    configured,
    create_conversation,
    create_supabase_client,
    list_conversations,
    load_messages,
    save_auth_session,
    save_message,
    set_user_session,
    update_title,
)
from src.pdf_processor import extract_chunks
from src.rag import generate_answer, retrieve


ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")
try:
    if not os.getenv("GEMINI_API_KEY") and st.secrets.get("GEMINI_API_KEY"):
        os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]
    if not os.getenv("MODEL_NAME") and st.secrets.get("MODEL_NAME"):
        os.environ["MODEL_NAME"] = st.secrets["MODEL_NAME"]
except (KeyError, FileNotFoundError):
    pass

st.set_page_config(page_title="Document Q&A", page_icon="📚", layout="wide")
st.title("📚 RAG-Based Document Search and Q&A")


@st.cache_resource
def load_encoder():
    return SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


def render_auth_gate():
    st.info("Sign in to keep your chat history private and available on your next visit.")
    sign_in, sign_up = st.tabs(["Sign in", "Create account"])
    with sign_in:
        with st.form("sign_in_form"):
            email = st.text_input("Email", key="signin_email")
            password = st.text_input("Password", type="password", key="signin_password")
            submitted = st.form_submit_button("Sign in", type="primary")
        if submitted:
            try:
                response = st.session_state["supabase"].auth.sign_in_with_password(
                    {"email": email, "password": password}
                )
                if response.session:
                    save_auth_session(response.session)
                    st.rerun()
                st.error("Sign-in did not return a session. Check your email verification settings.")
            except Exception as exc:
                st.error(f"Sign-in failed: {exc}")
    with sign_up:
        with st.form("sign_up_form"):
            email = st.text_input("Email", key="signup_email")
            password = st.text_input("Password (at least 8 characters)", type="password", key="signup_password")
            submitted = st.form_submit_button("Create account")
        if submitted:
            if len(password) < 8:
                st.error("Use a password with at least 8 characters.")
            else:
                try:
                    response = st.session_state["supabase"].auth.sign_up(
                        {"email": email, "password": password}
                    )
                    if response.session:
                        save_auth_session(response.session)
                        st.rerun()
                    else:
                        st.success("Account created. Check your email to confirm it, then sign in.")
                except Exception as exc:
                    st.error(f"Account creation failed: {exc}")


if not configured():
    st.warning("Supabase is not configured. Add SUPABASE_URL and SUPABASE_KEY to your local .env or Streamlit secrets.")
    st.stop()

try:
    supabase = create_supabase_client()
    st.session_state["supabase"] = supabase
    set_user_session(supabase)
except Exception:
    clear_auth_session()
    st.session_state["supabase"] = create_supabase_client()

if not st.session_state.get("sb_user_id"):
    render_auth_gate()
    st.stop()

supabase = st.session_state["supabase"]
user_id = st.session_state["sb_user_id"]

with st.sidebar:
    st.caption(f"Signed in as {st.session_state.get('sb_email', '')}")
    if st.button("Sign out"):
        try:
            supabase.auth.sign_out()
        finally:
            clear_auth_session()
            st.session_state.pop("supabase", None)
            st.rerun()

    st.divider()
    if st.button("＋ New chat", type="primary", width="stretch"):
        try:
            chat = create_conversation(supabase, user_id)
            st.session_state["active_conversation"] = chat["id"]
            st.session_state.pop("chunks", None)
            st.rerun()
        except Exception as exc:
            st.error(f"Could not create a chat: {exc}")

    try:
        conversations = list_conversations(supabase)
    except Exception as exc:
        st.error(f"Could not load chat history: {exc}")
        conversations = []
    if conversations:
        st.caption("Your chats")
        for chat in conversations:
            if st.button(chat["title"], key=f"chat_{chat['id']}", width="stretch"):
                st.session_state["active_conversation"] = chat["id"]
                st.session_state.pop("chunks", None)
                st.rerun()

active_id = st.session_state.get("active_conversation")
if not active_id and conversations:
    active_id = conversations[0]["id"]
    st.session_state["active_conversation"] = active_id
if not active_id:
    st.title("Start a conversation")
    st.write("Choose **New chat** in the sidebar, upload a PDF, and ask a question.")
    st.stop()

active_chat = next((c for c in conversations if c["id"] == active_id), None)
st.subheader(active_chat["title"] if active_chat else "Chat")
uploads = st.file_uploader("Upload PDF documents for this session", type="pdf", accept_multiple_files=True)

if st.button("Process documents", type="primary", disabled=not uploads):
    all_chunks = []
    for uploaded_file in uploads or []:
        try:
            chunks = extract_chunks(uploaded_file.getvalue())
            for chunk in chunks:
                chunk["document"] = uploaded_file.name
            all_chunks.extend(chunks)
        except Exception as exc:
            st.error(f"Could not read {uploaded_file.name}: {exc}")
    if all_chunks:
        st.session_state["chunks"] = all_chunks
        st.success(f"Processed {len(uploads)} PDF(s) into {len(all_chunks)} searchable passages.")
    else:
        st.warning("No selectable text was found. Scanned PDF support is not enabled yet.")

try:
    messages = load_messages(supabase, active_id)
except Exception as exc:
    st.error(f"Could not open this chat: {exc}")
    messages = []

for message in messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant" and message.get("sources"):
            with st.expander("View sources"):
                for source in message["sources"]:
                    st.markdown(f"**{source['document']} — page {source['page']}**")
                    st.write(source["text"])

if not st.session_state.get("chunks"):
    st.caption("Upload and process PDFs to ask a question. Previous messages are saved, but PDF passages currently need to be uploaded again after a new visit.")

question = st.chat_input("Ask a question about your documents", disabled=not st.session_state.get("chunks"))
if question:
    try:
        save_message(supabase, active_id, user_id, "user", question)
        if active_chat and active_chat["title"] == "New chat":
            update_title(supabase, active_id, question[:60])
        sources = retrieve(st.session_state["chunks"], question, load_encoder())
        answer = generate_answer(question, sources)
        saved_sources = [{key: source[key] for key in ("document", "page", "text")} for source in sources]
        save_message(supabase, active_id, user_id, "assistant", answer, saved_sources)
        st.rerun()
    except Exception as exc:
        st.error(f"The question could not be answered: {exc}")
