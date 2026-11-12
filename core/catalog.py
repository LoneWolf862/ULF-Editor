"""Bundled offline catalog and verified stack metadata."""
import json
from pathlib import Path


CATALOG = json.loads(Path(__file__).with_name("catalog.json").read_text(encoding="utf-8"))
