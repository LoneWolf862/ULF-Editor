"""Build-scoped Valheim prefab coefficients and pure item calculations."""

from dataclasses import dataclass
import json
import math
from pathlib import Path
import struct

from core.catalog import CATALOG
from core.fch import stable_hash


SNAPSHOT = json.loads(Path(__file__).with_name("item_stats_1_0_21.json").read_text(encoding="utf-8"))
if SNAPSHOT["schema"] != 1:
    raise ValueError("Unsupported item statistics schema")
GAME_VERSION = SNAPSHOT["game_version"]


def _by_hash():
    hashes = {}
    for prefab in CATALOG:
        identifier = stable_hash(prefab)
        hashes[identifier] = None if identifier in hashes else prefab
    return {
        identifier: SNAPSHOT["items"][prefab] for identifier, prefab in hashes.items()
        if prefab in SNAPSHOT["items"] and
        SNAPSHOT["items"][prefab]["max_stack"] == CATALOG[prefab]["max_stack"]
    }


_COEFFICIENTS = _by_hash()


def _float32(value):
    return struct.unpack("<f", struct.pack("<f", value))[0]


def _scaled(coefficients, levels):
    base, increment = coefficients
    return _float32(base + _float32(levels * increment))


@dataclass(frozen=True)
class ItemStatistics:
    maximum_durability: float | None
    damage: dict | None
    armor: float | None
    block: float
    deflection: float
    parry: float
    movement: float
    repairable: bool

    def block_with_skill(self, factor):
        if type(factor) not in (int, float) or not 0 <= factor <= 1:
            raise ValueError("Blocking factor must be between zero and one")
        extra = _float32(_float32(self.block * _float32(factor)) * 0.5)
        return _float32(self.block + extra)

    def repair_raw(self):
        """Match the game's float32 multiplication and truncation to int32."""
        if not self.repairable or self.maximum_durability is None:
            return None
        try:
            raw = _float32(self.maximum_durability * 100)
        except OverflowError:
            return None
        return int(raw) if 1 <= raw < 2**31 else None


def calculate_item_stats(item, quality=None):
    """Calculate using the 1.0.21 snapshot, or return None without verified input."""
    quality = item.quality if quality is None else quality
    if type(quality) is not int or not 1 <= quality <= 65535 or not item.has_prefab:
        return None
    row = _COEFFICIENTS.get(item.prefab_hash)
    if row is None:
        return None
    levels = quality - 1
    maximum = _scaled(row["durability"], levels) if row["uses_durability"] else None
    if maximum is not None and (not math.isfinite(maximum) or maximum <= 0):
        maximum = None
    # The effective world-level constants and damage redistribution are not
    # verified for this snapshot. The other item getters do not use world level.
    damage = armor = None
    if item.world_level == 0:
        damage = {channel: _scaled(pair, levels) for channel, pair in row["damage"].items()}
        armor = _scaled(row["armor"], levels)
    return ItemStatistics(maximum, damage, armor, _scaled(row["block"], levels),
                          _scaled(row["deflection"], levels), row["parry"],
                          row["movement"], row["repairable"])
