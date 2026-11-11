"""Basic retrieval and grounded answer generation."""

import os

import numpy as np
from google import genai
from sentence_transformers import SentenceTransformer


def retrieve(chunks: list[dict], question: str, encoder: SentenceTransformer, top_k: int = 4) -> list[dict]:
    """Find the chunks whose embeddings are closest to the question."""
    texts = [chunk["text"] for chunk in chunks]
    vectors = encoder.encode(texts, normalize_embeddings=True)
    query_vector = encoder.encode([question], normalize_embeddings=True)[0]
    scores = np.asarray(vectors) @ np.asarray(query_vector)
    best_indices = np.argsort(scores)[::-1][:top_k]
    return [{**chunks[i], "score": float(scores[i])} for i in best_indices]


def generate_answer(question: str, sources: list[dict]) -> str:
    """Ask Gemini to answer only from the retrieved source passages."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "replace_with_your_key":
        raise ValueError("Add your Gemini API key to the .env file first.")

    model_name = os.getenv("MODEL_NAME", "gemini-3.8-flash")
    client = genai.Client(api_key=api_key)
    context = "\n\n".join(
        f"[Source {i}, page {item['page']}]\n{item['text']}"
        for i, item in enumerate(sources, start=1)
    )
    prompt = (
        "Answer the question using only the source passages below. "
        "If the passages do not contain the answer, say that you could not find it in the uploaded documents. "
        "Keep the answer clear and cite supporting source labels such as [Source 1].\n\n"
        f"Passages:\n{context}\n\nQuestion: {question}"
    )
    response = client.models.generate_content(model=model_name, contents=prompt)
    return response.text or "I could not generate an answer. Please try again."
