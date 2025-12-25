import os, re, json, time
from datetime import datetime
from openai import OpenAI
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

# ==========================
# CONFIGURATION
# ==========================
INPUT_FILE = "pasted.txt"
OUTPUT_DIR = "Data"

GPT_MODEL = os.getenv("GPT_MODEL", "gpt-4o-mini")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# ==========================
# HELPERS
# ==========================
def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def detect_class_info(text):
    match = re.search(r'Class\s*(\d+)', text)
    class_num = match.group(1) if match else "unknown"
    title_line = text.strip().splitlines()[0] if text.strip() else "Untitled"
    return title_line.strip(), class_num

def generate_argument_units(text):
    """Use GPT model to segment lecture text."""
    log("🎯 Generating structured text with GPT...")
    prompt = f"""
    Segment the following Vedanta lecture into structured argument units.
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

# ==========================
# QDRANT UPLOAD
# ==========================
def embed_and_upload_to_qdrant(title, class_num, structured_text):
    """Embed structured text and upload to Qdrant."""
    log("🚀 Entered embed_and_upload_to_qdrant()")
    log(f"Connecting to Qdrant at: {QDRANT_URL}")
    model = SentenceTransformer(EMBEDDING_MODEL)
    embeddings = model.encode([structured_text])

    collection_name = "jyotir_brahmana_units"
    qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

    try:
        info = qdrant.get_collections()
        log(f"✅ Connected to Qdrant. {len(info.collections)} collections found.")
    except Exception as e:
        log(f"❌ Could not connect to Qdrant: {e}")
        return

    # Create or overwrite collection
    try:
        qdrant.recreate_collection(
            collection_name=collection_name,
            vectors_config={"size": len(embeddings[0]), "distance": "Cosine"}
        )
        log(f"📁 Collection '{collection_name}' recreated.")
    except Exception as e:
        log(f"⚠️ Could not recreate collection: {e}")

    # Upload vector
    try:
        qdrant.upsert(
            collection_name=collection_name,
            points=[{
                "id": int(datetime.now().timestamp()),
                "vector": embeddings[0],
                "payload": {
                    "title": title,
                    "class_num": class_num,
                    "content": structured_text
                }
            }]
        )
        log(f"📦 Uploaded 1 vector to Qdrant collection '{collection_name}'.")
    except Exception as e:
        log(f"❌ Upload failed: {e}")

# ==========================
# MAIN LOGIC
# ==========================
def build_argument_units(input_path):
    log("🚀 Starting jyotir-app argument unit builder")

    if not os.path.exists(input_path):
        log(f"❌ Input file not found: {input_path}")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        text = f.read()

    log(f"📄 Loaded {len(text.split())} words from {input_path}")
    title, class_num = detect_class_info(text)
    log(f"🎓 Processing: {title} (Class {class_num})")

    structured_text = generate_argument_units(text)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    safe_title = re.sub(r"[^A-Za-z0-9_]+", "_", title)
    output_file = os.path.join(OUTPUT_DIR, f"class_{class_num}_{safe_title}.json")

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "title": title,
            "class_num": class_num,
            "content": structured_text
        }, f, ensure_ascii=False, indent=2)

    log(f"💾 Saved structured data → {output_file}")

    # ✅ This ensures Qdrant upload runs
    log("🧭 Moving to Qdrant upload step...")
    embed_and_upload_to_qdrant(title, class_num, structured_text)

    log("✅ Task complete. Going idle.")

# ==========================
# EXECUTION
# ==========================
if __name__ == "__main__":
    log("✅ Script started")
    build_argument_units(INPUT_FILE)
    log("💤 Task finished. Keeping Render worker alive...")
    while True:
        time.sleep(300)


