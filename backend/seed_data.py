import json
from pathlib import Path

SEED_RESPONSE = json.loads(
    Path(__file__).with_name("seed_data.json").read_text(encoding="utf-8")
)
