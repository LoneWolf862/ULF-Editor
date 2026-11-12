"""Read selected vanilla prefab limits from an installed Unity asset bundle.

Research-only dependency: UnityPy 1.25.4 (MIT). Never writes to the game folder.
Usage: python tools/inspect_game_items.py BUNDLE PREFAB [PREFAB ...]
Prints factual metadata only; does not extract artwork, code or character data.
"""

import argparse
import hashlib
import json
from pathlib import Path


def inspect(bundle, prefabs):
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
            found[game_object.m_Name] = {
                "max_stack": shared["m_maxStackSize"],
                "max_quality": shared["m_maxQuality"],
            }
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
    arguments = parser.parse_args()
    print(json.dumps(inspect(arguments.bundle, arguments.prefabs), indent=2, sort_keys=True))
