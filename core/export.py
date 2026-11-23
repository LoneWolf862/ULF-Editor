"""Save As publication with source protection and on-disk verification."""

import os
from pathlib import Path
import tempfile
import math
import struct

from core.fch import Character, FormatError, stable_hash
from core.catalog import CATALOG
from core.inventory_ops import legal_position


def export_character(character, source, destination):
    """Validate a closed temporary output before atomically publishing it."""
    source = Path(source)
    destination = Path(destination)
    temporary = None
    stage = "validating the proposed export"
    try:
        if not character.roundtrip:
            raise FormatError("The original character did not pass round-trip validation.")
        if source.read_bytes() != character.original:
            raise FormatError("The original file changed. Reload it before exporting.")
        if destination.resolve() == source.resolve():
            raise FormatError("Choose a different file. The original character is protected.")
        if destination.exists() and os.path.samefile(source, destination):
            raise FormatError("This destination refers to the original character file.")
        expected = character.serialize()
        verified = Character(expected)
        if not verified.roundtrip:
            raise FormatError("The edited character failed serialization validation.")
        if verified.items != character.items or len(verified.skills) != len(character.skills):
            raise FormatError("Serialized inventory or skill records differ from the intended edits.")
        for intended, actual in zip(character.skills, verified.skills):
            if intended[0] != actual[0]:
                raise FormatError("A serialized skill identifier differs from the intended edit.")
            for value, decoded in zip(intended[1:], actual[1:]):
                if math.isnan(value) and math.isnan(decoded):
                    continue
                if struct.unpack('<f', struct.pack('<f', value))[0] != decoded:
                    raise FormatError("A serialized skill value differs from the intended edit.")
        original = Character(character.original)
        known = {stable_hash(name): entry for name, entry in CATALOG.items()}
        original_items = original.items
        if len({(item.x,item.y) for item in original_items}) != len(original_items):
            raise FormatError("Duplicate inventory positions prevent safe editing.")
        current_items = {(item.x, item.y): item for item in verified.items}
        if len(current_items) != len(verified.items):
            raise FormatError("More than one item occupies an inventory position.")
        retained=set()
        protected_item_fields=('prefab_hash','has_prefab','world_level','picked','variant','crafter_id','crafter_name','custom','tail')
        for item,edited in zip(verified.items,character.items):
            origin=edited.origin_index
            previous=None
            if origin is not None:
                if type(origin) is not int or not 0<=origin<len(original_items) or origin in retained:
                    raise FormatError("An inventory record has an invalid source identity.")
                retained.add(origin)
                previous=original_items[origin]
            maximum = known.get(item.prefab_hash, {}).get("max_stack")
            if maximum is not None and not 1<=item.stack<=maximum:
                raise FormatError("An item exceeds its verified maximum stack size.")
            if previous is None:
                if maximum is None or item.tail!=0 or not 1<=item.quality<=65535:
                    raise FormatError("A new item has unverified limits or a cheated-item flag.")
                if original.inventory_version == 110 and (
                    item.x >= 8 or item.y >= original.writable_inventory_rows
                ):
                    raise FormatError("A new item is outside the source character's writable slots.")
            else:
                if (item.x, item.y) != (previous.x, previous.y) and (
                    not legal_position(original, (previous.x, previous.y))
                    or not legal_position(original, (item.x, item.y))
                ):
                    raise FormatError("An item moved outside the supported inventory.")
                if item.quality != previous.quality and not 1 <= item.quality <= 65535:
                    raise FormatError("An edited item has an invalid quality value.")
                if any(getattr(item,name)!=getattr(previous,name) for name in protected_item_fields):
                    raise FormatError("An existing item's identity or protected metadata changed.")
                if maximum is None and item.to_bytes()!=previous.to_bytes():
                    raise FormatError("An unverified inventory item was modified.")
        for index,item in enumerate(original_items):
            if index not in retained and known.get(item.prefab_hash,{}).get('max_stack') is None:
                raise FormatError("An unverified inventory item was removed.")
        from core.appearance import FIELDS, same, propose, encoded_middle, protected_middle
        if protected_middle(verified) != protected_middle(original):
            raise FormatError("Export would change protected progression metadata.")
        changes = {f: getattr(verified.appearance, f) for f in FIELDS
                   if not same(getattr(original.appearance, f), getattr(verified.appearance, f))}
        if changes:
            original.appearance = propose(original, changes)
        if verified.middle != encoded_middle(original):
            raise FormatError("Appearance encoding differs from the validated targeted changes.")
        protected = ("prefix", "suffix", "head", "tail")
        if any(getattr(verified, name) != getattr(original, name) for name in protected):
            raise FormatError("Export would change protected character metadata.")
        stage = "creating the temporary output"
        descriptor, name = tempfile.mkstemp(
            prefix=".ulf-", suffix=".tmp", dir=destination.parent
        )
        temporary = Path(name)
        stage = "writing and flushing the temporary output"
        with os.fdopen(descriptor, "wb") as output:
            output.write(expected)
            output.flush()
            os.fsync(output.fileno())
        stage = "reading back the closed temporary output"
        actual = temporary.read_bytes()
        reopened = Character(actual)
        if actual != expected or not reopened.roundtrip:
            raise FormatError("The written file failed verification. Export was canceled.")
        if source.read_bytes() != character.original:
            raise FormatError("The original file changed during export. Reload it.")
        if destination.resolve() == source.resolve() or (
            destination.exists() and os.path.samefile(source, destination)
        ):
            raise FormatError("The export destination now refers to the original file.")
        stage = "publishing the verified output"
        os.replace(temporary, destination)
        temporary = None
        return destination
    except OSError as error:
        raise FormatError(
            f"Export failed while {stage} ({type(error).__name__}, errno={error.errno}). "
            "Check folder permissions, available disk space, and file locks."
        ) from error
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError as error:
                raise FormatError(
                    "Export failed and its temporary file could not be removed. "
                    "No output was published. Remove the .ulf-*.tmp file in the "
                    "destination folder after resolving permissions or file locks."
                ) from error
