import re
import json
from pathlib import Path

def build_jyotir_json(input_path: str):
    input_file = Path(input_path)
    base = input_file.stem.lower()

    # 🔹 Determine class number automatically
    # e.g. "pasted_class2.txt" → "class2.json"
    # If no number found, default to "class1.json"
    import re
    match = re.search(r'(\d+)', base)
    class_number = match.group(1) if match else "1"

    output_file = Path(f"class{class_number}.json")

    labels = [
        "Invocation & Context of Study",
        "Structure of the Upaniṣad and Jyotir Brāhmaṇa Introduction",
        "Janaka–Yājñavalkya Dialogue – “Kim Jyotiḥ ayam puruṣaḥ?”",
        "Four Activities – Āste, Paryeti, Karma Kurute, Viparyeti",
        "Eka Ślokī Discussion",
        "Purpose of Light – From Gross to Subtle",
        "Ṣaḍ-Liṅga Method – Upakrama to Phala",
    ]

    patterns = [
        r"(?:Om\s+Namah\s+Narayana|Thank you)",
        r"(?:third Brahmana|Jyotir\s+Brahmana|Madhukanda|Munikanda)",
        r"(?:Janaka|Yajnavalkya|Kim\s*Jyoti)",
        r"(?:Aaste|Paryeti|Karma\s*Kurute|Viparyeti|four activities)",
        r"(?:Ekashloki|kimjyoti\s+stava|Guru\s+asks)",
        r"(?:gross\s+to\s+subtle|purpose\s+of\s+the\s+light|Atma\s*Jyoti)",
        r"(?:Shad\s*Linga|Upakrama|Upasamhara|Phala|Sivananda)",
    ]

    # --- Read full text ---
    text = input_file.read_text(encoding="utf-8")

    # --- Find split positions ---
    positions = []
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        positions.append(m.start() if m else None)

    length = len(text)
    for i, p in enumerate(positions):
        if p is None:
            positions[i] = int(i * length / len(patterns))
    positions = sorted(set(positions + [length]))

    # --- Extract segments ---
    segments = [text[positions[i]:positions[i+1]].strip() for i in range(len(positions) - 1)]
    segments = (segments + [""] * 7)[:7]

    data = {str(i+1): {"title": labels[i], "content": seg} for i, seg in enumerate(segments)}

   
# --- Write clean JSON file into /data ---
output_dir = Path("data")
output_dir.mkdir(exist_ok=True)
output_path = output_dir / output_file.name

with output_path.open("w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

# --- Log summary ---
log_file = Path(f"log_class{class_number}.txt")
total_chars = sum(len(v["content"]) for v in data.values())
log_file.write_text(
    f"Created {output_path} with {len(data)} segments ({total_chars} characters total).\n",
    encoding="utf-8"
)

print(f"✅ Created {output_path} ({total_chars} chars)")
