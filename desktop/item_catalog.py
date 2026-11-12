"""Offline presentation metadata for the verified core catalog."""

from dataclasses import dataclass
import json
from pathlib import Path

from core.catalog import CATALOG
from core.fch import stable_hash


CATALOG_VERSION = "Valheim 1.0.21 evidence · Jötunn 1.0.7 names and categories"
LABELS = json.loads(Path(__file__).with_name("item_labels.json").read_text(encoding="utf-8"))
CATEGORY_NAMES = {
    "AmmoNonEquipable": "Ammo", "OneHandedWeapon": "Weapon",
    "TwoHandedWeapon": "Weapon", "TwoHandedWeaponLeft": "Weapon",
    "Chest": "Armor", "Helmet": "Armor", "Legs": "Armor", "Shoulder": "Armor",
    "Bow": "Weapon", "Fish": "Food", "Consumable": "Food", "Torch": "Tool",
}


@dataclass(frozen=True)
class CatalogEntry:
    prefab: str
    name: str
    category: str
    maximum_stack: int | None
    maximum_quality: int | None
    source: str


def build_catalog():
    for prefab, metadata in CATALOG.items():
        name, category = LABELS.get(prefab, (metadata["name"], "Misc"))
        yield CatalogEntry(prefab, name, CATEGORY_NAMES.get(category, category),
                           metadata.get("max_stack"), metadata.get("max_quality"),
                           metadata.get("source", "Source unavailable"))


ENTRIES = tuple(build_catalog())
BY_PREFAB = {entry.prefab: entry for entry in ENTRIES}
BY_HASH = {stable_hash(entry.prefab): entry for entry in ENTRIES}


def item_entry(item):
    return BY_HASH.get(item.prefab_hash) if item.has_prefab else None


def search_catalog(query, category):
    query = query.strip().casefold()
    results = []
    for entry in ENTRIES:
        name, prefab = entry.name.casefold(), entry.prefab.casefold()
        if (category is None or category == entry.category) and (query in name or query in prefab):
            rank = 0 if query in (name, prefab) else 1 if name.startswith(query) or prefab.startswith(query) else 2
            results.append((rank, name, prefab, entry))
    return [entry for _, _, _, entry in sorted(results)]
