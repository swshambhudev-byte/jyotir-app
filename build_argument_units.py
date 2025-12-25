import os
import re
import json
from datetime import datetime
from openai import OpenAI
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

# ==========================
# CONFIGURATION
# ==========================
INPUT_FILE = "pasted.txt"
OUTPUT_DIR = "Data"

GPT_MODEL = os.getenv("GPT_MODEL", "gpt-5.2")  # reasoning model
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")  # for Qdrant
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ==========================
# HELPERS
# ==========================
def log(msg: str):
    print(f"🪶 {msg}")

def detect_class_info(text):
    """Extract lecture title and class number from the pasted text."""
    match = re.search(r'Class\s*(\d+)', text)
    class_num = match.group(1) if match else "unknown"
    title_line = text.strip().splitlines()[0] if text.strip() else "Untitled"
    return title_line.strip(), class_num

def generate_argument_units(text):
    """Use GPT model to segment the lecture into structured units."""
    log("🎯 Generating structured text with GPT model...")
    prompt = f"""
    Segment the following Vedanta lecture text into structured argument units.
    Each unit should include: Topic, Shabda pivot, Purvapaksha, Siddhanta, and Quotation.

    Lecture:
    {text}
    """
    response = client.chat.completions.create(
        model=GPT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()

def embed_and_upload_to_qdrant(title, class_num, text):
    """Generate embeddings and upload to Qdrant memory."""
    log("🧠 Uploading structured knowledge to Qdrant memory...")
    model = SentenceTransformer(EMBEDDING_MODEL)
    embeddings = model.encode([text])
    collection_name = "jyotir_bramana_memory"

    qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    qdrant.recreate_collection(
        collection_name=collection_name,
        vectors_config={"size": len(embeddings[0]), "distance": "Cosine"}
    )
    qdrant.upsert(
        collection_name=collection_name,
        points=[{
            "id": int(datetime.now().timestamp()),
            "vector": embeddings[0],
            "payload": {
                "title": title,
                "class_num": class_num,
                "content": text
            }
        }]
    )
    log("✅ Uploaded to Qdrant successfully.")

# ==========================
# CORE LOGIC
# ==========================
def build_argument_units(input_path: str):
    """Main process: read text, segment, save JSON, and upload to Qdrant."""
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    log(f"📖 Processing {input_path} – please wait...")

    with open(input_path, "r", encoding="utf-8") as f:
        text = f.read()

    title, class_num = detect_class_info(text)
    log(f"📘 Detected lecture: {title}")

    structured_text = generate_argument_units(text)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    safe_title = re.sub(r"[^A-Za-z0-9_]+", "_", title)
    output_file = os.path.join(OUTPUT_DIR, f"class_{class_num}_{safe_title}.json")

    result = {
        "title": title,
        "class_num": class_num,
        "content":
}