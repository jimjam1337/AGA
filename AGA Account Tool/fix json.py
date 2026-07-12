import json
from pathlib import Path

file_path = Path("gift_card_codes.json")

raw = file_path.read_text(encoding="utf-8").strip()

fixed = {
    "codes": json.loads(f"[{raw}]")
}

file_path.write_text(json.dumps(fixed, indent=2), encoding="utf-8")
print("gift_card_codes.json fixed")