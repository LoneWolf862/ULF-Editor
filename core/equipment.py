"""Conservative saved equipment-slot rules from Valheim 1.0.21.

Humanoid.EquipItem, assembly SHA-256 and exclusions are documented in the
Alpha 0.4 report. These validate saved slot conflicts, not live player state.
"""

from copy import deepcopy

from core.fch import FormatError, stable_hash
from core.editing import apply_item
from core.inventory_ops import verified_item
from core.item_stats import SNAPSHOT


ROWS = {stable_hash(p): (p, r) for p, r in SNAPSHOT["items"].items()}
SLOTS = {3: frozenset({"right hand"}), 5: frozenset({"left hand"}),
         4: frozenset({"right hand", "left hand"}),
         14: frozenset({"right hand", "left hand"}),
         19: frozenset({"right hand", "left hand"}),
         22: frozenset({"right hand", "left hand"}),
         6: frozenset({"helmet"}), 7: frozenset({"chest"}),
         11: frozenset({"legs"}), 17: frozenset({"cape"}),
         18: frozenset({"utility"}), 24: frozenset({"trinket"}),
         9: frozenset({"ammo"}), 23: frozenset({"ammo"})}


def equipment_slots(item):
    if not item.has_prefab:
        return None
    prefab, row = ROWS.get(item.prefab_hash, (None, {}))
    return SLOTS.get(row.get("item_type"))


def equipment_changes(character, item, equipped):
    """Return exact index/flag proposals; no mutation until fully validated."""
    verified_item(character, item)
    if character.inventory_version != 110 or type(equipped) is not bool:
        raise FormatError("Equipment management requires inventory v110 and a boolean state.")
    index = next(n for n, i in enumerate(character.items) if i is item)
    if not equipped:
        return ((index, False),) if item.equipped else ()
    slots = equipment_slots(item)
    if not slots:
        raise FormatError("Equipment slots are unverified for this item (including context-dependent torches).")
    prefab, row = ROWS[item.prefab_hash]
    if prefab in {"HelmetOdin", "CapeOdin"}:
        raise FormatError("DLC ownership cannot be verified offline; equipping this item is disabled.")
    if item.custom or item.world_level != 0:
        raise FormatError("Custom metadata or world-level equipment context is unverified.")
    if row["uses_durability"] and item.durability_raw <= 0:
        raise FormatError("Repair the broken item before equipping it.")
    changes = []
    for n, other in enumerate(character.items):
        if other is item or not other.equipped:
            continue
        other_slots = equipment_slots(other)
        if other_slots is None or other.custom or other.world_level != 0:
            raise FormatError("An equipped item has unsupported rules. Unequip supported records explicitly first.")
        if slots & other_slots:
            verified_item(character, other)
            changes.append((n, False))
    if not item.equipped:
        changes.append((index, True))
    # Validate every flag change before publishing any of them.
    candidate = deepcopy(character)
    for n, value in changes:
        apply_item(candidate, candidate.items[n], {"equipped": value})
    return tuple(changes)


def equip_item(character, item, equipped):
    changes = equipment_changes(character, item, equipped)
    for index, value in changes:
        character.items[index].equipped = value
