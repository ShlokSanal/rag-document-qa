"""Streamlit interface for the PDF question-answering project."""

import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

from src.pdf_processor import extract_chunks
from src.rag import generate_answer, retrieve


ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")
try:
    # Streamlit Community Cloud injects deployed secrets through st.secrets.
    if not os.getenv("GEMINI_API_KEY") and st.secrets.get("GEMINI_API_KEY"):
        os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]
    if not os.getenv("MODEL_NAME") and st.secrets.get("MODEL_NAME"):
        os.environ["MODEL_NAME"] = st.secrets["MODEL_NAME"]
except (KeyError, FileNotFoundError):
    # Local runs can use the ignored .env file instead.
    pass

st.set_page_config(page_title="Document Q&A", page_icon="📚", layout="wide")
st.title("📚 RAG-Based Document Search and Q&A")
st.write("Upload text-based PDF documents, then ask questions grounded in their content.")

@st.cache_resource
def load_encoder():
    return SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


uploads = st.file_uploader("Choose one or more PDF files", type="pdf", accept_multiple_files=True)

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
        st.warning("No selectable text was found. Scanned PDF support will be added in a later step.")

if st.session_state.get("chunks"):
    st.caption(f"Ready: {len(st.session_state['chunks'])} passages indexed for this session.")
    question = st.chat_input("Ask a question about your documents")
    if question:
        with st.spinner("Searching documents and preparing an answer..."):
            try:
                passages = retrieve(st.session_state["chunks"], question, load_encoder())
                answer = generate_answer(question, passages)
                st.markdown(answer)
                with st.expander("View retrieved sources"):
                    for source in passages:
                        st.markdown(f"**{source['document']} — page {source['page']}**")
                        st.write(source["text"])
            except Exception as exc:
                st.error(f"The question could not be answered: {exc}")

with st.sidebar:
    st.header("Setup status")
    st.write("Gemini API key:", "✅ detected" if os.getenv("GEMINI_API_KEY") else "❌ missing")
    st.info("This first version supports PDFs with selectable text. OCR for scanned PDFs is a later step.")
