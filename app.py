# =====================================================
# Jyotir Brahmana Vedanta Q&A API — Lightweight ONNX Version (Cached + Health)
# =====================================================

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from qdrant_client import QdrantClient
from transformers import AutoTokenizer
import onnxruntime as ort
import numpy as np
import os, re, urllib.request
from openai import OpenAI

# =====================================================
# Initialize FastAPI
# =====================================================
app = FastAPI(
    title="Jyotir Brahmana Vedanta API (Lightweight)",
    description="Ask Vedantic questions based on Swami Paramananda Giri’s Jyotir Brāhmaṇa teachings.",
    version="2.2.0"
)

# =====================================================
# Config — Qdrant + OpenAI
# =====================================================
QDRANT_URL = os.getenv("QDRANT_URL", "https://your-qdrant-instance-url")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "<your_qdrant_api_key_here>")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "<your_openai_api_key_here>")
COLLECTION_NAME = "jyotir_brahmana_units"

qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
client = OpenAI(api_key=OPENAI_API_KEY)

# =====================================================
# Embedding Setup — ONNX Cached
# =====================================================
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
CACHE_DIR = os.path.join("/tmp", "onnx_cache")
os.makedirs(CACHE_DIR, exist_ok=True)
onnx_model_path = os.path.join(CACHE_DIR, "model.onnx")

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

if not os.path.exists(onnx_model_path):
    url = f"https://huggingface.co/{MODEL_NAME}/resolve/main/model.onnx"
    print(f"🔽 Downloading ONNX model from {url}")
    urllib.request.urlretrieve(url, onnx_model_path)
else:
    print("✅ Using cached ONNX model.")

session = ort.InferenceSession(onnx_model_path)

def embed_text(text: str):
    """Generate embedding using ONNX model."""
    inputs = tokenizer(text, return_tensors="np", truncation=True, padding=True)
    ort_inputs = {k: v for k, v in inputs.items()}
    outputs = session.run(None, ort_inputs)
    embeddings = outputs[0].mean(axis=1)
    return embeddings[0].tolist()

# =====================================================
# Schemas
# =====================================================
class Question(BaseModel):
    question: str

# =====================================================
# Routes
# =====================================================

@app.get("/")
def home():
    return {"message": "🕉️ Jyotir Brahmana Vedanta API is live (ONNX cached mode)."}

@app.get("/health")
def health_check():
    """Render will ping this to verify container is alive."""
    try:
        _ = embed_text("health check")
        return {"status": "ok", "embedding_test": True}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@app.post("/ask")
def ask_vedanta(q: Question):
    try:
        query = q.question
        print(f"🔍 Querying Qdrant for: {query}")

        # Step 1 – Embed query
        query_vector = embed_text(query)

        # Step 2 – Query Qdrant
        response = qdrant.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=5
        )
        results = response.points
        if not results:
            return {"answer": "No relevant teachings found in the Qdrant collection."}

        # Step 3 – Assemble context
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

        # Step 4 – Compose prompt
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
3. When a Sanskrit śabda (e.g. eva, **jyotiḥ**, ātman, prāṇa, sākṣin, upādhi) appears, **highlight and explain it**.  
4. Be clear, reflective, faithful to śruti.

Retrieved materials:
{context}

Now write a concise, integrated explanation with śabda-pivot awareness.
"""

        # Step 5 – Generate response
        completion = client.chat.completions.create(
            model="gpt-5.2",
            messages=[{"role": "user", "content": prompt}],
        )

        raw_answer = completion.choices[0].message.content.strip()

        # Step 6 – Clean invented refs
        cleaned_answer = re.sub(
            r"\(Ref:\s*(?!(" + valid_ref_pattern + r"))Class\s*\d+[^)]*\)", "", raw_answer
        )
        cleaned_answer = re.sub(r"\s+\(\s*\)", "", cleaned_answer).strip()

        return {
            "question": query,
            "answer": cleaned_answer,
            "sources_used": valid_refs
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
