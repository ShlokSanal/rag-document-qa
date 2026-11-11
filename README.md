# RAG-Based Intelligent Document Search and Question Answering System

A learning project that lets users upload PDF documents, retrieve relevant passages, and ask questions with page references.

## First version

- Streamlit user interface
- PDF text extraction with page numbers
- Semantic retrieval with Sentence Transformers
- Answer generation with Google Gemini
- Source passages shown with answers

This version handles text-based PDFs. OCR for scanned PDFs is planned as a later feature.

## Run on Windows

1. Install Python 3.10 or newer.
2. Open PowerShell in this project folder.
3. Create and activate a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

4. Install the packages:

   ```powershell
   pip install -r requirements.txt
   ```

5. Copy `.env.example` to `.env`, then add your Gemini API key to `.env`.
6. Start the app:

   ```powershell
   streamlit run app.py
   ```

Keep `.env` private. Never commit an API key to GitHub.

## Deploy and share

1. Push this project to a GitHub repository.
2. In Streamlit Community Cloud, create an app from that repository and select `app.py` as the entry point.
3. In the app's **Settings → Secrets**, add:

   ```toml
   GEMINI_API_KEY = "your-key"
   MODEL_NAME = "gemini-3.8-flash"
   ```

4. Deploy. Streamlit will provide a shareable URL for the running app.

The `.streamlit/secrets.toml.example` file shows the required format. Do not upload a real key to GitHub. Anyone with the public app link can use the app, and their requests will use your Gemini API key and its quota.

## Reference and attribution

This project is being developed for learning with reference to [ki11e6/pdf-chatbot-rag](https://github.com/ki11e6/pdf-chatbot-rag). Review its MIT license and retain required notices if reusing its code. This implementation is being built as a separate learning project.
