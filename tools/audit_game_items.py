"""Audit installed ObjectDB items without executing or modifying game code.

Run with Python -m tools.audit_game_items BUNDLE --output REPORT.
Requires the optional UnityPy 1.25.4 research environment, never at app runtime.
The report contains identifiers and numerical compatibility facts, not assets.
"""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from tools.inspect_game_items import stat_coefficients


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def classification(prefab, path, shared, rigidbody):
    """Conservative static eligibility; excluded does not mean unresolvable."""
    if shared is None:
        return "no_itemdrop"
    if shared["m_itemType"] == 10:
        return "customization"
    if not shared["m_icons"] or not any(p["m_PathID"] for p in shared["m_icons"]):
        return "no_inventory_icon"
    if "/Characters/" in path and "/animals/fishes/" not in path and prefab != "TrophyKvastur":
        return "npc_equipment_or_attack"
    if not rigidbody:
        return "placed_object"
    if prefab in {"CapeTest", "PlayerUnarmed", "SledgeCheat", "SwordCheat"}:
        return "internal_or_test"
    if not path:
        return "unresolved_asset_path"
    return "inventory"


def audit(bundle):
    import UnityPy
    from UnityPy.classes import PPtr

    environment = UnityPy.load(str(bundle))
    paths = {(id(r.deref().assets_file), r.path_id): path for path, r in environment.container.items()}
    databases = []
    for path, reader in environment.container.items():
        if not path.endswith("/_NetScene.prefab"):
            continue
        for pair in reader.read().m_Component:
            component = pair.component.deref()
            if component.type.name != "MonoBehaviour":
                continue
            tree = component.read_typetree()
            if all(key in tree for key in ("m_items", "m_recipes", "m_StatusEffects")):
                databases.append((component, tree["m_items"]))
    if len(databases) != 1:
        raise ValueError("Expected exactly one ObjectDB registry")
    component, pointers = databases[0]
    found = {}
    for pointer in pointers:
        reader = PPtr(**pointer, assetsfile=component.assets_file).deref()
        obj = reader.read()
        shared = None
        rigidbody = False
        for pair in obj.m_Component:
            part = pair.component.deref()
            rigidbody |= part.type.name == "Rigidbody"
            if part.type.name != "MonoBehaviour":
                continue
            tree = part.read_typetree()
            if "m_itemData" in tree:
                if shared is not None:
                    raise ValueError(f"Multiple ItemDrops: {obj.m_Name}")
                shared = tree["m_itemData"]["m_shared"]
        path = paths.get((id(reader.assets_file), reader.path_id), "")
        status = classification(obj.m_Name, path, shared, rigidbody)
        row = {"classification": status}
        if shared is not None:
            row.update(max_stack=shared["m_maxStackSize"], max_quality=shared["m_maxQuality"],
                       item_type=shared["m_itemType"], token=shared["m_name"])
            row.update(stat_coefficients(shared))
            if any(type(row[key]) is not int or not 1 <= row[key] <= 65535
                   for key in ("max_stack", "max_quality")):
                raise ValueError(f"Unsupported limits: {obj.m_Name}")
        if obj.m_Name in found:
            raise ValueError(f"Duplicate registered prefab: {obj.m_Name}")
        found[obj.m_Name] = row
    # Ensure scanning the registered graph did not omit an unregistered ItemDrop.
    unregistered = []
    prefab_count = 0
    for path, reader in environment.container.items():
        if not path.lower().endswith(".prefab"):
            continue
        prefab_count += 1
        obj = reader.read()
        if not hasattr(obj, "m_Component"):
            continue
        if obj.m_Name in found:
            continue
        for pair in obj.m_Component:
            part = pair.component.deref()
            if part.type.name == "MonoBehaviour" and "m_itemData" in part.read_typetree():
                unregistered.append(obj.m_Name)
    if unregistered:
        raise ValueError(f"Unregistered ItemDrops need review: {sorted(unregistered)}")
    # UnityPy can resolve dependencies. Record every loaded physical bundle,
    # not just the entry bundle, so the audit's input scope is reproducible.
    inputs = {p.name: digest(p) for name in environment.files
              if (p := bundle.parent / Path(name).name).is_file()}
    return {"schema": 1, "bundle": bundle.name, "sha256": digest(bundle),
            "extractor": f"UnityPy {UnityPy.__version__}", "audit_version": 1,
            "inputs": inputs, "container_prefabs": prefab_count,
            "counts": dict(Counter(row["classification"] for row in found.values())),
            "items": found}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.bundle)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"registered": len(result["items"]), **result["counts"]}, sort_keys=True))
