"""Validated edit transactions independent of the desktop interface."""

import copy
import math

from core.fch import FormatError, stable_hash
from core.catalog import CATALOG


def apply_item(character, item, changes):
    """Validate a complete item proposal before replacing any fields."""
    if not character.roundtrip:
        raise FormatError("The original character failed round-trip validation.")
    if not any(existing is item for existing in character.items):
        raise FormatError("Select an existing inventory item.")
    metadata = next(
        (entry for name, entry in CATALOG.items() if stable_hash(name) == item.prefab_hash),
        {},
    )
    maximum = metadata.get("max_stack")
    if maximum is None:
        raise FormatError("This item has unverified metadata and must remain unchanged.")
    allowed = {"quality", "stack", "durability_raw", "equipped"}
    if changes.keys() - allowed:
        raise FormatError("The proposed edit includes a protected item property.")
    proposed = copy.deepcopy(item)
    for name, value in changes.items():
        setattr(proposed, name, value)
    if type(proposed.quality) is not int or not 1 <= proposed.quality <= 65535:
        raise FormatError("Quality must be an integer between 1 and 65,535.")
    if type(proposed.stack) is not int or not 1 <= proposed.stack <= min(maximum,65535):
        raise FormatError(f"Quantity must be an integer between 1 and {maximum}.")
    if "durability_raw" in changes and (
        type(proposed.durability_raw) is not int
        or not 0 <= proposed.durability_raw < 2**31
    ):
        raise FormatError("Durability is outside the supported range.")
    if type(proposed.equipped) is not bool:
        raise FormatError("Equipped must be true or false.")
    proposed.to_bytes()
    for name in changes:
        setattr(item, name, getattr(proposed, name))


def apply_skills(character, changes):
    """Apply (skill ID, optional level, optional XP) proposals atomically."""
    if not character.roundtrip:
        raise FormatError("This character did not pass the original round-trip check.")
    proposed = copy.deepcopy(character.skills)
    seen = set()
    for skill_id, level, experience in changes:
        if skill_id in seen:
            raise FormatError("A skill appears more than once in the proposed changes.")
        seen.add(skill_id)
        if type(skill_id) is not int or not -(2**31) <= skill_id < 2**31:
            raise FormatError("The skill identifier is invalid.")
        if sum(row[0]==skill_id for row in proposed)>1:
            raise FormatError("Duplicate records make this skill ambiguous. Its data is preserved.")
        if level is not None and type(level) not in (int,float):
            raise FormatError("Skill levels must be numbers.")
        if experience is not None and type(experience) not in (int,float):
            raise FormatError("Skill experience must be a number.")
        if level is not None and (not math.isfinite(level) or not 0 <= level <= 100):
            raise FormatError("Skill levels must be finite numbers between 0 and 100.")
        if experience is not None and (
            not math.isfinite(experience) or not 0 <= experience < 1e9
        ):
            raise FormatError("Skill experience must be a finite number from 0 to below one billion.")
        row = next((row for row in proposed if row[0] == skill_id), None)
        if row is None:
            row = [skill_id, 0.0, 0.0]
            proposed.append(row)
        if level is not None:
            row[1] = float(level)
        if experience is not None:
            row[2] = float(experience)
    character.skills = proposed


def remove_item(character, item):
    """Remove one explicitly selected, verified inventory record."""
    if not character.roundtrip:
        raise FormatError("The original character failed round-trip validation.")
    if not any(existing is item for existing in character.items):
        raise FormatError("Select an existing inventory item.")
    metadata=next((entry for name,entry in CATALOG.items() if stable_hash(name)==item.prefab_hash),{})
    if metadata.get("max_stack") is None:
        raise FormatError("Unverified items must be preserved unchanged.")
    character.items=[existing for existing in character.items if existing is not item]
