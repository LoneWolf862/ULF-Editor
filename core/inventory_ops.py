"""Conservative, atomic inventory organization; no GUI dependencies."""

from copy import deepcopy

from core.catalog import CATALOG
from core.editing import apply_item
from core.fch import FormatError, stable_hash
from core.item_stats import calculate_item_stats


_PREFABS = {}
for _prefab in CATALOG:
    _identifier = stable_hash(_prefab)
    _PREFABS[_identifier] = None if _identifier in _PREFABS else _prefab


def legal_position(character, position):
    return (isinstance(position, (tuple, list)) and len(position) == 2
            and all(type(n) is int for n in position)
            and 0 <= position[0] < 8
            and 0 <= position[1] < character.writable_inventory_rows)


def verified_item(character, item):
    if not character.roundtrip or not any(i is item for i in character.items):
        raise FormatError("Select an existing validated item.")
    prefab = _PREFABS.get(item.prefab_hash)
    if not item.has_prefab or prefab is None or CATALOG[prefab].get("max_stack") is None:
        raise FormatError("Unknown or ambiguous items must remain unchanged.")
    if len({(i.x, i.y) for i in character.items}) != len(character.items):
        raise FormatError("Duplicate positions prevent inventory organization.")
    if not legal_position(character, (item.x, item.y)):
        raise FormatError("The source position is outside the supported inventory.")
    return prefab


def move_item(character, item, destination, *, swap=False):
    verified_item(character, item)
    if not legal_position(character, destination):
        raise FormatError("Destination is outside the writable inventory.")
    destination = tuple(destination)
    if destination == (item.x, item.y):
        raise FormatError("Choose a different destination.")
    other = next((i for i in character.items if (i.x, i.y) == destination), None)
    if other is not None:
        if not swap:
            raise FormatError("Destination is occupied. Choose an explicit swap.")
        verified_item(character, other)
    elif swap:
        raise FormatError("Swap requires two occupied slots.")
    # Validate both records before touching either. Only fixed coordinate bytes change.
    original = (item.x, item.y)
    item.x, item.y = destination
    if other is not None:
        other.x, other.y = original


def transferable_item(character, item):
    prefab = verified_item(character, item)
    if character.inventory_version != 110:
        raise FormatError("New copy/replacement policies require inventory v110.")
    if item.custom or item.variant != 0 or item.world_level != 0 or item.tail != 0:
        raise FormatError("Custom metadata, variants, world levels or trailing flags prevent safe copying/replacement.")
    # Validate quality, stack and raw durability without changing the source.
    candidate = deepcopy(character)
    index = next(n for n, i in enumerate(character.items) if i is item)
    apply_item(candidate, candidate.items[index], {"durability_raw": item.durability_raw})
    return prefab


def duplicate_item(character, item, destination):
    transferable_item(character, item)
    if not legal_position(character, destination):
        raise FormatError("Destination is outside the writable inventory.")
    if any((i.x, i.y) == tuple(destination) for i in character.items):
        raise FormatError("Destination is occupied.")
    if len(character.items) >= 65535:
        raise FormatError("Too many inventory items.")
    duplicate = deepcopy(item)
    duplicate.x, duplicate.y = destination
    duplicate.origin_index = None
    duplicate.equipped = False
    # Zero was required above; never scrub an existing flagged item to copy it.
    duplicate.tail = 0
    duplicate.to_bytes()
    character.items.append(duplicate)
    return duplicate


def replacement_item(character, item, prefab, quality, stack):
    transferable_item(character, item)
    candidate = deepcopy(character)
    candidate.items = [i for i in candidate.items if (i.x, i.y) != (item.x, item.y)]
    candidate.add(prefab, item.x, item.y, quality=quality, stack=stack)
    replacement = candidate.items[-1]
    stats = calculate_item_stats(replacement)
    if stats is None:
        raise FormatError("Replacement requires verified item statistics.")
    if stats.maximum_durability is None:
        replacement.durability_raw = 0
    else:
        # Use the same verified float32 encoding even for non-repairable items.
        from dataclasses import replace
        target = replace(stats, repairable=True).repair_raw()
        if target is None:
            raise FormatError("Replacement durability cannot be represented safely.")
        replacement.durability_raw = target
    replacement.to_bytes()
    return replacement


def replace_item(character, item, prefab, quality=1, stack=1):
    replacement = replacement_item(character, item, prefab, quality, stack)
    index = next(n for n, i in enumerate(character.items) if i is item)
    character.items[index] = replacement
    return replacement


def fill_stack(character, item):
    prefab = verified_item(character, item)
    maximum = CATALOG[prefab]["max_stack"]
    if item.stack >= maximum:
        raise FormatError("Stack is already at or above its verified maximum; no automatic reduction.")
    apply_item(character, item, {"stack": maximum})
