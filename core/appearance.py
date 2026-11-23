"""Typed appearance values and targeted encoding, independent of desktop widgets."""

from dataclasses import dataclass, replace
import json
import math
from pathlib import Path
import struct

from core.fch import FormatError, string

CATALOG = json.loads(Path(__file__).with_name("appearance_catalog.json").read_text(encoding="utf-8"))
FIELDS = ("beard", "hair", "skin_color", "hair_color", "model")


@dataclass(frozen=True)
class Appearance:
    beard: str
    hair: str
    skin_color: tuple[float, float, float]
    hair_color: tuple[float, float, float]
    model: int


def same(left, right):
    if isinstance(left, tuple) and isinstance(right, tuple):
        return len(left) == len(right) and all(same(a, b) for a, b in zip(left, right))
    return left == right or (type(left) is float and type(right) is float
                             and math.isnan(left) and math.isnan(right))


def propose(character, changes):
    """Validate a complete proposal without mutating any part of the character."""
    if not character.roundtrip or (character.profile_version, character.player_version) != (47, 34):
        raise FormatError("Appearance editing requires validated profile 47 / player 34 (Valheim 1.0.21).")
    old = character.appearance
    values = {}
    for field, value in changes.items():
        if field not in FIELDS:
            raise FormatError("Unsupported appearance field; character name is read-only.")
        if same(getattr(old, field), value):
            continue
        if field == "model":
            if type(value) is not int or value not in (0, 1):
                raise FormatError("Choose verified body model 0 or 1.")
        elif field in ("hair", "beard"):
            if type(value) is not str or value not in CATALOG[field]:
                raise FormatError(f"Choose a verified {field} identifier; unknown existing values are preserved.")
        else:
            if (not isinstance(value, tuple) or len(value) != 3 or
                    any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1 for v in value)):
                raise FormatError("Edited RGB must contain three finite normalized values from 0 to 1.")
            value = tuple(struct.unpack("<f", struct.pack("<f", v))[0] for v in value)
        values[field] = value
    result = replace(old, **values)
    if {"model", "beard", "hair"} & values.keys():
        if result.model not in (0, 1):
            raise FormatError("Choose a verified model before changing styles.")
        if result.model == 1 and result.beard != "BeardNone":
            raise FormatError("Model 1 requires an explicit BeardNone selection. No beard is reset automatically.")
    return result


def encode_field(field, value, original, raw):
    if same(value, original):
        return raw
    if field in ("hair", "beard"):
        return string(value)
    if field == "model":
        return struct.pack("<i", value)
    return b"".join(raw[n*4:n*4+4] if same(v, original[n]) else struct.pack("<f", v)
                    for n, v in enumerate(value))


def encoded_middle(character):
    chunks = []
    end = 0
    for field, (start, stop) in character._appearance_spans.items():
        chunks.append(character.middle[end:start])
        chunks.append(encode_field(field, getattr(character.appearance, field),
                                   getattr(character._original_appearance, field), character.middle[start:stop]))
        end = stop
    chunks.append(character.middle[end:])
    return b"".join(chunks)


def protected_middle(character):
    """Opaque bytes outside the structurally parsed appearance spans."""
    start = next(iter(character._appearance_spans.values()))[0]
    end = list(character._appearance_spans.values())[-1][1]
    return character.middle[:start], character.middle[end:]


def apply_appearance(character, changes):
    character.appearance = propose(character, changes)
