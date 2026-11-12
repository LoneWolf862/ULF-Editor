"""Read selected vanilla prefab limits from an installed Unity asset bundle.

Research-only dependency: UnityPy 1.25.4 (MIT). Never writes to the game folder.
Usage: python tools/inspect_game_items.py BUNDLE PREFAB [PREFAB ...]
Prints factual metadata only; does not extract artwork, code or character data.
"""

import argparse
import hashlib
import json
from pathlib import Path


STAT_FIELDS = {
    "durability": ("m_maxDurability", "m_durabilityPerLevel"),
    "armor": ("m_armor", "m_armorPerLevel"),
    "block": ("m_blockPower", "m_blockPowerPerLevel"),
    "deflection": ("m_deflectionForce", "m_deflectionForcePerLevel"),
    "parry": "m_timedBlockBonus",
    "movement": "m_movementModifier",
    "uses_durability": "m_useDurability",
    "repairable": "m_canBeReparied",
}


def stat_coefficients(shared):
    row = {
        key: [shared[field] for field in fields] if isinstance(fields, tuple) else shared[fields]
        for key, fields in STAT_FIELDS.items()
    }
    base, growth = shared["m_damages"], shared["m_damagesPerLevel"]
    row["damage"] = {key.removeprefix("m_"): [base[key], growth[key]]
                     for key in base if base[key] or growth[key]}
    for key in ("uses_durability", "repairable"):
        row[key] = bool(row[key])
    return row


def inspect(bundle, prefabs, *, statistics=False):
    import UnityPy

    requested = set(prefabs)
    environment = UnityPy.load(str(bundle))
    found = {}
    for path, reader in environment.container.items():
        if not path.lower().endswith(".prefab") or Path(path).stem not in requested:
            continue
        game_object = reader.read()
        for pair in game_object.m_Component:
            component = pair.component.deref()
            if component.type.name != "MonoBehaviour":
                continue
            tree = component.read_typetree()
            if "m_itemData" not in tree:
                continue
            shared = tree["m_itemData"]["m_shared"]
            if game_object.m_Name in found:
                raise ValueError(f"Ambiguous ItemDrop metadata for {game_object.m_Name}")
            found[game_object.m_Name] = {
                "max_stack": shared["m_maxStackSize"],
                "max_quality": shared["m_maxQuality"],
            }
            if statistics:
                found[game_object.m_Name].update(stat_coefficients(shared))
    missing = requested - found.keys()
    if missing:
        raise ValueError(f"No ItemDrop metadata for: {', '.join(sorted(missing))}")
    with bundle.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"bundle": bundle.name, "sha256": digest,
            "extractor": f"UnityPy {UnityPy.__version__}", "items": found}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("prefabs", nargs="+")
    parser.add_argument("--statistics", action="store_true")
    arguments = parser.parse_args()
    print(json.dumps(inspect(arguments.bundle, arguments.prefabs, statistics=arguments.statistics),
                     indent=2, sort_keys=True))
