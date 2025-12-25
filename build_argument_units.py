import os
import json
from datetime import datetime
from openai import OpenAI
import re
import subprocess

# ===== CONFIGURATION =====
OUTPUT_DIR = "Data"
INPUT_FILE = "pasted.txt"

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def log(message):
    print(f"🌿 {message}")


def detect_class_info(text):
    """Detects lecture title and class number (e.g. 'Class 3')."""
    match = re.search(r"(Brihad.*?Class\s*(\d+))", text, re.IGNORECASE)
    if match:
        title = match.group(1).strip()
        class_num = match.group(2).strip()
    else:
        title = "Unknown Lecture"
        class_num = datetime.now().strftime("%Y%m%d_%H%M")
    return title, class_num


def generate_argument_units(text):
    """Use GPT to segment and structure the lecture intelligently."""
    log("🪶 Generating structured argument units...")

    prompt = f"""
You are a Vedānta discourse analyst working on Swami Paramananda Giri’s
Jyotir Brāhmaṇa lectures.

Segment the following lecture transcript into *argument-units*.
Each unit must have:

- **Topic**
- **Śabda Pivot**  (key word or linguistic hinge)
- **Pūrvapakṣa**   (misunderstanding or opposing stance)
- **Siddhānta**    (resolution or intended meaning)
- **Quotation**    (if present)
- **Layer**        one of: Śruti | Bhāṣya | Vārttika | Ṭīkā | Footnote | Modern exposition
- **Expands**      which prior layer it elaborates (e.g. Bhāṣya expands Śruti)
- **Function**     short phrase describing the interpretive role, such as:
                   "makes explicit what was implicit",
                   "clarifies hidden assumption",
                   "illustrates with example", etc.

Detect these layers using textual cues:
- Mentions of Śaṅkara, “in the Bhāṣya” → Layer = Bhāṣya, Expands = Śruti.
- Mentions of Sureśvara, “in the Vārttika” → Layer = Vārttika, Expands = Bhāṣya.
- Mentions of Ṭīkākāra or “in the Ṭīkā” → Layer = Ṭīkā, Expands = Vārttika or Bhāṣya.
- Explicit quotations from the Upaniṣad → Layer = Śruti.
- Teacher’s own clarifying explanation → Layer = Modern exposition, Expands = preceding layer.

If no layer is clear, leave those three fields blank.

Keep the writing in readable Markdown, with clear numbering and spacing.
Preserve exact Sanskrit words in IAST where present.

Lecture text:
{text}
"""

    response = client.responses.create(
        model="gpt-5.2"
        input=prompt
    )

    return response.output[0].content[0].text.strip()


def git_push(file_path, title, class_num):
    """Automatically adds, commits, and pushes new lecture data to GitHub."""
    try:
        log("📂 Staging files...")
        subprocess.run(["git", "add", "."], check=True)

        log("🪵 Committing changes...")
        commit_message = f"✨ Added {title} (Class {class_num}) structured JSON with layered annotations"
        subprocess.run(["git", "commit", "-m", commit_message], check=True)

        log("☁️ Pushing to GitHub...")
        subprocess.run(["git", "push", "-u", "origin", "main"], check=True)

        log("🌸 Successfully pushed and triggered Render deploy.")
    except subprocess.CalledProcessError as e:
        log(f"⚠️ Git push failed: {e}")


def build_argument_units(input_path):
    """Core process: read text, segment, save JSON, push to GitHub."""
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    log(f"💫 Processing {input_path} – please wait...")

    with open(input_path, "r", encoding="utf-8") as f:
        text = f.read()

    title, class_num = detect_class_info(text)
    log(f"📘 Detected: {title}")

    structured_text = generate_argument_units(text)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    safe_title = re.sub(r"[^A-Za-z0-9_]+", "_", title)
    output_file = os.path.join(OUTPUT_DIR, f"class_{class_num}_{safe_title}.json")

    result = {
        "title": title,
        "class_num": class_num,
        "content": structured_text
    }

    with open(output_file, "w", encoding="utf-8") as out:
        json.dump(result, out, ensure_ascii=False, indent=2)

    log(f"💾 Saved structured file: {output_file}")

# --- QDRANT UPLOAD SECTION ---
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer
import os, json

try:
    QDRANT_URL = os.getenv("QDRANT_URL")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    model = SentenceTransformer("all-MiniLM-L6-v2")
    collection_name = "jyotir_brahmana_memory"

    # Create or update collection
    client.recreate_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE),
    )

    # Load generated content
    with open(output_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    text = data.get("content", "")
    if text.strip():
        vector = model.encode(text).tolist()

        client.upsert(
            collection_name=collection_name,
            points=[
                models.PointStruct(
                    id=None,
                    vector=vector,
                    payload={
                        "title": data.get("title"),
                        "class_num": data.get("class_num"),
                        "text": text,
                    },
                )
            ],
        )
        log(f"🧠 Uploaded '{data.get('title')}' to Qdrant memory.")

except Exception as e:
    log(f"⚠️ Qdrant upload skipped or failed: {e}")

# Push to GitHub + Render
git_push(output_file, title, class_num)


    # Push to GitHub + Render
    git_push(output_file, title, class_num)


if __name__ == "__main__":
    build_argument_units(INPUT_FILE)
