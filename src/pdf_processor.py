"""Read PDF pages and split their text into overlapping chunks."""

from io import BytesIO

from pypdf import PdfReader


def extract_chunks(pdf_bytes: bytes, chunk_size: int = 900, overlap: int = 150) -> list[dict]:
    """Return text chunks with their original PDF page numbers."""
    reader = PdfReader(BytesIO(pdf_bytes))
    chunks = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if not text:
            continue

        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            content = text[start:end].strip()
            if content:
                chunks.append({"text": content, "page": page_number})
            if end == len(text):
                break
            start = end - overlap

    return chunks
