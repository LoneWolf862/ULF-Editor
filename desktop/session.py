"""Desktop working copy and review, backed by the Alpha 0.1.1 domain operations."""

from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import math
import struct

from core.editing import apply_item, apply_skills, remove_item
from core.fch import Character, FormatError, SKILLS
from desktop.item_catalog import item_entry


ITEM_FIELDS = {
    "stack": "Quantity", "quality": "Quality", "durability_raw": "Durability",
    "equipped": "Equipped",
}


def load_character(path):
    with path.open("rb") as source:
        data = source.read(256 * 1024 * 1024 + 1)
    character = Character(data)
    if not character.roundtrip:
        raise FormatError("The untouched file did not round-trip byte-for-byte.")
    return character


def float32(value):
    return struct.unpack("<f", struct.pack("<f", value))[0]


def same_number(left, right):
    return left == right or (math.isnan(left) and math.isnan(right))


def display_number(value):
    # Use the shortest display that maps to the same saved float32.
    if math.isfinite(value):
        if abs(value) < 1e7 and float(value).is_integer():
            return "-0" if value == 0 and math.copysign(1, value) < 0 else str(int(value))
        for digits in range(1, 10):
            text = format(value, f".{digits}g")
            try:
                candidate = float32(float(text))
            except OverflowError:
                continue
            if candidate == value:
                return text
    return str(value)


def durability_text(raw):
    return f"{'-' if raw < 0 else ''}{abs(raw) // 100}.{abs(raw) % 100:02d}"


def item_value(field, value):
    if value is None:
        return "—"
    if field == "durability_raw":
        return durability_text(value)
    if field == "equipped":
        return "Yes" if value else "No"
    return str(value)


def item_name(item):
    entry = item_entry(item)
    return entry.name if entry else f"Unknown item #{item.prefab_hash}"


def slot_name(position):
    x, y = position
    return f"Row {y + 1}, column {x + 1}"


@dataclass(frozen=True)
class Command:
    key: tuple
    action: str
    values: tuple


@dataclass(frozen=True)
class Change:
    key: tuple
    title: str
    details: tuple
    position: tuple | None = None
    warning: str = ""


class Session:
    def __init__(self, character, path):
        self.baseline = character
        self.working = deepcopy(character)
        self.path = path
        self.commands = []
        self.items = self.original_items(self.working)
        self.item_drafts = {}
        self.skill_drafts = {}
        self.next_item = 0
        self.revision = self.exported_revision = sha256(character.original).digest()
        self.export_path = None

    @staticmethod
    def original_items(character):
        return {("item", item.origin_index): item for item in character.items}

    @property
    def has_drafts(self):
        return bool(self.item_drafts or self.skill_drafts)

    @property
    def unsaved(self):
        return self.has_drafts or self.revision != self.exported_revision

    @property
    def duplicate_positions(self):
        return {position for position, count in self.position_counts().items() if count > 1}

    def position_counts(self):
        return Counter((item.x, item.y) for item in self.items.values())

    def free_slots(self):
        occupied = self.position_counts()
        return [(x, y) for y in range(6) for x in range(8) if (x, y) not in occupied]

    @staticmethod
    def run_command(character, items, command):
        key, action, values = command.key, command.action, command.values
        if action == "edit":
            apply_item(character, items[key], dict(values))
        elif action == "remove":
            remove_item(character, items[key])
            del items[key]
        elif action == "add":
            prefab, x, y, stack, quality, extra = values
            character.add(prefab, x, y, quality=quality, stack=stack)
            item = character.items[-1]
            if extra:
                apply_item(character, item, dict(extra))
            items[key] = item
        else:
            apply_skills(character, [values])

    def publish(self, character, items, commands):
        # Verify serialization before exposing the candidate to any widget.
        revision = sha256(character.serialize()).digest()
        self.working, self.items, self.commands = character, items, commands
        self.revision = revision

    def apply(self, command):
        character, items = deepcopy((self.working, self.items))
        self.run_command(character, items, command)
        self.publish(character, items, [*self.commands, command])
        self.item_drafts.pop(command.key, None)

    def edit_item(self, key, changes):
        item = self.items[key]
        if item.x >= 8 or (item.x, item.y) in self.duplicate_positions:
            raise FormatError("This inventory record cannot be edited at its saved position.")
        if changes:
            self.apply(Command(key, "edit", tuple(changes.items())))
        self.item_drafts.pop(key, None)

    def remove_item(self, key):
        item = self.items[key]
        if item.x >= 8 or (item.x, item.y) in self.duplicate_positions:
            raise FormatError("This inventory record cannot be removed from its saved position.")
        self.apply(Command(key, "remove", ()))

    def add_item(self, prefab, position, stack, quality, extra):
        key = ("new", self.next_item)
        self.apply(Command(key, "add", (prefab, *position, stack, quality, tuple(extra.items()))))
        self.next_item += 1

    def apply_skill_batch(self, changes):
        character, items = deepcopy((self.working, self.items))
        if changes:
            apply_skills(character, changes)
            commands = [Command(("skill", row[0]), "skill", row) for row in changes]
            self.publish(character, items, [*self.commands, *commands])
        self.skill_drafts.clear()

    def changes(self):
        originals = self.original_items(self.baseline)
        changes = []
        for key in dict.fromkeys([*originals, *self.items]):
            before, after = originals.get(key), self.items.get(key)
            item = after if after is not None else before
            position = (item.x, item.y)
            entry = item_entry(item)
            title = f"{item_name(item)} · {slot_name(position)}"
            details = []
            warning = ""
            for field, label in ITEM_FIELDS.items():
                old = getattr(before, field, None)
                new = getattr(after, field, None)
                if old != new:
                    details.append(f"{label}  {item_value(field, old)} → {item_value(field, new)}")
            if not details:
                continue
            if after is None:
                title = f"Remove {title}"
            elif before is None:
                title = f"Add {title}"
            if after and (before is None or after.quality != before.quality):
                if entry and entry.maximum_quality is not None and after.quality > entry.maximum_quality:
                    warning = f"Quality exceeds the vanilla maximum ({entry.maximum_quality}). Gameplay may differ."
                elif entry and entry.maximum_quality is None:
                    warning = "Vanilla quality maximum unavailable. Gameplay may differ."
            changes.append(Change(key, title, tuple(details), position, warning))
        before_skills = {row[0]: row[1:] for row in self.baseline.skills}
        current_skills = {row[0]: row[1:] for row in self.working.skills}
        for key in dict.fromkeys(command.key for command in self.commands if command.action == "skill"):
            skill_id = key[1]
            old = before_skills.get(skill_id, (0.0, 0.0))
            new = current_skills[skill_id]
            details = tuple(
                f"{label}  {display_number(left)} → {display_number(right)}"
                for label, left, right in zip(("Level", "Experience"), old, new)
                if not same_number(left, right)
            )
            if skill_id not in before_skills:
                details = ("New skill record", *details)
            if details:
                changes.append(Change(key, SKILLS[skill_id], details))
        return changes

    def discard_dependencies(self, change):
        # Replay must also skip additions later removed from the same slot.
        if change.key[0] == "item" and change.key not in self.items:
            return {
                command.key for command in self.commands
                if command.action == "add" and command.values[1:3] == change.position
            }
        return set()

    def discard(self, keys):
        character = deepcopy(self.baseline)
        items = self.original_items(character)
        commands = [command for command in self.commands if command.key not in keys]
        for command in commands:
            self.run_command(character, items, command)
        self.publish(character, items, commands)
        for kind, identifier in keys:
            if kind == "skill":
                self.skill_drafts.pop(identifier, None)
            else:
                self.item_drafts.pop((kind, identifier), None)

    def discard_all(self):
        character = deepcopy(self.baseline)
        self.publish(character, self.original_items(character), [])
        self.item_drafts.clear()
        self.skill_drafts.clear()
