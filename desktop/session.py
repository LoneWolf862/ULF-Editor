"""Desktop working copy and review, backed by the Alpha 0.1.1 domain operations."""

from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import math
import struct

from core.editing import apply_item, apply_skills, remove_item
from core.fch import Character, FormatError, SKILLS
from core.item_stats import calculate_item_stats
from core.history import History
from core.inventory_ops import move_item, duplicate_item, replace_item, fill_stack
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


@dataclass(frozen=True)
class RepairPlan:
    revision: bytes
    keys: tuple
    changes: tuple
    skipped: tuple


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
        self.history = History()

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
        return [(x, y) for y in range(self.working.writable_inventory_rows) for x in range(8)
                if (x, y) not in occupied]

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
        elif action in ("move", "swap"):
            move_item(character, items[key], values, swap=action == "swap")
        elif action == "duplicate":
            new_key, destination = values
            items[new_key] = duplicate_item(character, items[key], destination)
        elif action == "replace":
            new_key, prefab, quality, stack = values
            items[new_key] = replace_item(character, items[key], prefab, quality, stack)
            del items[key]
        elif action == "fill":
            fill_stack(character, items[key])
        elif action == "skill":
            apply_skills(character, [values])
        else:
            raise FormatError("Unsupported editing command.")

    def publish(self, character, items, commands, label="Edit"):
        # Verify serialization before exposing the candidate to any widget.
        revision = sha256(character.serialize()).digest()
        if revision != self.revision:
            self.history.record(label, (self.working, self.items, self.commands),
                                (character, items, commands))
        self.working, self.items, self.commands = character, items, commands
        self.revision = revision

    def apply(self, command):
        character, items = deepcopy((self.working, self.items))
        self.run_command(character, items, command)
        self.publish(character, items, [*self.commands, command], command.action.title())
        self.item_drafts.pop(command.key, None)

    def undo(self):
        self._travel(False)

    def redo(self):
        self._travel(True)

    def _travel(self, redo):
        if self.has_drafts:
            raise FormatError("Apply or revert all form drafts before Undo/Redo.")
        if not (self.history.future if redo else self.history.past):
            return
        self.working, self.items, self.commands = self.history.redo() if redo else self.history.undo()
        self.revision = sha256(self.working.serialize()).digest()

    def organize(self, key, action, values=()):
        if self.has_drafts:
            raise FormatError("Apply or revert all form drafts before inventory quick actions.")
        if action not in ("move", "swap", "duplicate", "replace", "fill"):
            raise FormatError("Unsupported inventory quick action.")
        new_key = ("new", self.next_item)
        if action == "duplicate":
            values = (new_key, tuple(values))
        elif action == "replace":
            values = (new_key, *values)
        self.apply(Command(key, action, tuple(values)))
        if action in ("duplicate", "replace"):
            self.next_item += 1
            return new_key
        return key

    def edit_item(self, key, changes):
        item = self.items[key]
        if item.x >= 8 or (item.x, item.y) in self.duplicate_positions:
            raise FormatError("This inventory record cannot be edited at its saved position.")
        if changes:
            self.apply(Command(key, "edit", tuple(changes.items())))
        self.item_drafts.pop(key, None)

    def repair_plan(self, keys=None):
        keys = tuple(self.items if keys is None else keys)
        duplicates = self.duplicate_positions
        changes, skipped = [], []
        for key in keys:
            item = self.items[key]
            entry = item_entry(item)
            stats = calculate_item_stats(item)
            target = stats.repair_raw() if stats is not None else None
            if self.working.inventory_version != 110:
                reason = "Repair requires the current save format for the 1.0.21 statistics."
            elif key in self.item_drafts:
                reason = "Apply or revert this item's draft first."
            elif item.x >= 8 or (item.x, item.y) in duplicates:
                reason = "The saved position is ambiguous or unsupported."
            elif entry is None or entry.maximum_stack is None:
                reason = "Verified item metadata is unavailable."
            elif not 1 <= item.stack <= min(entry.maximum_stack, 65535):
                reason = "The saved quantity is outside its verified limit."
            elif stats is None:
                reason = "Statistics are unavailable for this prefab or quality."
            elif stats.maximum_durability is None:
                reason = "Verified durability is unavailable or inapplicable."
            elif target is None:
                reason = "This item is not repairable or its maximum cannot be encoded."
            elif item.durability_raw >= target:
                reason = "Durability is already at or above the repair target."
            else:
                changes.append((key, item.durability_raw, target))
                continue
            skipped.append((key, reason))
        return RepairPlan(self.revision, keys, tuple(changes), tuple(skipped))

    def apply_repairs(self, plan):
        if (plan.revision != self.revision or any(key not in self.items for key in plan.keys)
                or self.repair_plan(plan.keys) != plan):
            raise FormatError("Inventory or drafts changed. Review a fresh repair preview.")
        if not plan.changes:
            return
        character, items = deepcopy((self.working, self.items))
        commands = [
            Command(key, "edit", (("durability_raw", target),))
            for key, _, target in plan.changes
        ]
        for command in commands:
            self.run_command(character, items, command)
        self.publish(character, items, [*self.commands, *commands], "Repair" if len(commands) == 1 else "Repair All")

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
            self.publish(character, items, [*self.commands, *commands], "Edit skills")
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
            if before and after and (before.x, before.y) != position:
                details.append(f"Position  {slot_name((before.x, before.y))} → {slot_name(position)}")
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
        if any(c.action in ("move", "swap", "duplicate", "replace") for c in self.commands):
            raise FormatError("Use Undo or Discard All for dependent inventory operations.")
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
