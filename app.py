# =====================================================
# Jyotir Brahmana Vedanta Q&A API — by Swami’s System
# =====================================================

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from openai import OpenAI
import os, re

# =====================================================
# Initialize FastAPI App
# =====================================================
app = FastAPI(
    title="Jyotir Brahmana Vedanta API",
    description="Ask Vedantic questions based on the Jyotir Brahmana teachings (Jyotir Brāhmaṇa, Bṛhadāraṇyaka Upaniṣad).",
    version="1.0.0"
)

# =====================================================
# Configuration — Cloud Qdrant + OpenAI
# =====================================================
QDRANT_URL = os.getenv("QDRANT_URL", "https://ae186872-a799-4120-94a1-b78a338ea2e6.us-east4-0.gcp.cloud.qdrant.io")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "<your_qdrant_api_key_here>")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "<your_openai_api_key_here>")
COLLECTION_NAME = "jyotir_brahmana_units"

# Initialize clients
qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
embedder = SentenceTransformer("all-MiniLM-L6-v2")
client = OpenAI(api_key=OPENAI_API_KEY)

# =====================================================
# Pydantic model for POST requests
# =====================================================
class Question(BaseModel):
    question: str

# =====================================================
# Routes
# =====================================================

@app.get("/")
def home():
    return {"message": "🕉️ Jyotir Brahmana Vedanta API is live."}


@app.post("/ask")
def ask_vedanta(q: Question):
    try:
        query = q.question
        print(f"🔍 Querying Qdrant for: {query}")

        # Step 1: Embed query
        query_vector = embedder.encode(query).tolist()

        # Step 2: Retrieve top matches from Qdrant
        response = qdrant.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=5
        )
        results = response.points

        if not results:
            return {"answer": "No relevant teachings found in the Qdrant collection."}

        # Step 3: Build context with references
        context_parts, valid_refs = [], []
        for r in results:
            title = r.payload.get("title", "Unknown Source")
            class_num = r.payload.get("class_num", "Unknown")
            content = r.payload.get("content", "")
            ref = f"Class {class_num} – {title}"
            valid_refs.append(ref)
            context_parts.append(f"[{ref}]\n{content}")

        context = "\n\n---\n\n".join(context_parts)
        valid_ref_pattern = "|".join(re.escape(r) for r in valid_refs)

        # Step 4: Build the Vedantic reasoning prompt
        prompt = f"""
You are a Vedānta teacher analyzing the Bṛhadāraṇyaka Upaniṣad — Jyotir Brāhmaṇa teachings of Swami Paramananda Giri.

Question:
{query}

Below are verified lecture extracts. Speak **only** from these sources.
When you cite, use only these verified references:
{', '.join(valid_refs)}

⚖️ Disciplinary Rules:
1. Do not invent class numbers, titles, or teachings not present.
2. Speak only from retrieved material; if not found, say so.
3. When a Sanskrit śabda (e.g. eva, **jyotiḥ**, ātman, prāṇa, sākṣin, upādhi) appears or is implied:
   - **Highlight it in bold and Devanāgarī (if possible)**, e.g. **jyotiḥ (ज्योतिः)**.
   - Briefly explain why that word is crucial — what misunderstanding it blocks or what redirection it performs.
4. Keep reasoning teacher-like, clear, reflective, and faithful to śruti.
5. If multiple meanings are possible, mention that but stay within retrieved sources.

Retrieved materials:
{context}

Now write a concise, integrated explanation with śabda-pivot awareness.
"""

        print("🧘 Generating Vedantic answer with śabda sensitivity...")

        # Step 5: Generate response using GPT
        completion = client.chat.completions.create(
            model="gpt-5.2",
            messages=[{"role": "user", "content": prompt}],
        )

        raw_answer = completion.choices[0].message.content.strip()

        # Step 6: Remove any invented refs (if GPT made them)
        cleaned_answer = re.sub(r"\(Ref:\s*(?!(" + valid_ref_pattern + r"))Class\s*\d+[^)]*\)", "", raw_answer)
        cleaned_answer = re.sub(r"\s+\(\s*\)", "", cleaned_answer).strip()

        return {
            "question": query,
            "answer": cleaned_answer,
            "sources_used": valid_refs
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
