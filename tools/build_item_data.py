"""Build reviewed offline data from the pinned 1.0.21 local audit.

python -m tools.build_item_data AUDIT --output-dir DIRECTORY
Writes three data files and the coverage report under DIRECTORY. Review the diff
before promoting them; this never fetches data or modifies installed game files.
"""

import argparse
import json
from pathlib import Path
import re

from core.fch import stable_hash


ROOT = Path(__file__).resolve().parents[1]
BUILD_HASH = "84f55cfb24af51b9f0494fd9d1a355bf009e08545ff8ccf607c7d88d2e4e1ec8"


def build(audit, baseline, reference):
    if audit["sha256"] != BUILD_HASH or audit["audit_version"] != 1:
        raise ValueError("This builder requires the reviewed 1.0.21 audit")
    labels = {}
    for line in reference.splitlines():
        fields = line.split("|")
        if len(fields) >= 7 and re.fullmatch("[a-f0-9]{32}", fields[2]):
            labels[fields[1].split("<br>")[0]] = fields[4:6]
    rows = audit["items"]
    eligible = {name for name, row in rows.items() if row["classification"] == "inventory"}
    selected = set(baseline) | eligible
    if selected - rows.keys() or selected - labels.keys():
        raise ValueError("Missing verified metadata or attributed label")
    hashes = [stable_hash(name) for name in selected]
    if len(hashes) != len(set(hashes)):
        raise ValueError("Ambiguous prefab hashes")
    source = "Valheim 1.0.21 build 26249040 · local ObjectDB/ItemDrop audit · " + BUILD_HASH
    catalog = {name: {"name": name, "max_stack": rows[name]["max_stack"],
                      "max_quality": rows[name]["max_quality"], "source": source}
               for name in selected}
    # Independently checked against resources.assets, SHA-256 recorded in the
    # milestone report. The pinned 1.0.7 label was changed in this installed build.
    catalog["FaderDrop"]["display_name"] = "Kindled Ribs"
    catalog["FaderDrop"]["display_name_source"] = "Valheim 1.0.21 resources.assets · item_fader_drop"
    snapshot = {key: audit[key] for key in ("schema", "bundle", "sha256", "extractor")}
    snapshot.update(game_version="1.0.21", steam_build=26249040,
                    verification="verified-prefab-coefficients", audit_version=1,
                    items={name: {k: v for k, v in rows[name].items() if k != "classification"}
                           for name in eligible})
    report = {key: audit[key] for key in ("counts", "container_prefabs", "inputs", "audit_version")}
    report.update(game_version="1.0.21", steam_build=26249040,
                  registered_prefabs=len(rows), catalog_entries=len(catalog),
                  inventory_prefabs=sorted(eligible),
                  excluded={name: row["classification"] for name, row in rows.items()
                            if name not in eligible},
                  retained_legacy_entries=sorted(set(baseline) - eligible))
    return {"core/catalog.json": catalog, "core/item_stats_1_0_21.json": snapshot,
            "desktop/item_labels.json": {name: labels[name] for name in selected},
            "docs/references/item-coverage-1.0.21.json": report}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audit", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    outputs = build(json.loads(args.audit.read_text(encoding="utf-8")),
                    json.loads((ROOT / "core/catalog.json").read_text(encoding="utf-8")),
                    (ROOT / "docs/references/jotunn-item-list.md").read_text(encoding="utf-8"))
    for relative, content in outputs.items():
        destination = args.output_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if relative == "desktop/item_labels.json":
            rendered = "{\n" + ",\n".join(
                "  " + json.dumps(key) + ": " + json.dumps(content[key], ensure_ascii=False)
                for key in sorted(content)) + "\n}\n"
        else:
            rendered = json.dumps(content, indent=2, sort_keys=True) + "\n"
        destination.write_text(rendered, encoding="utf-8")
