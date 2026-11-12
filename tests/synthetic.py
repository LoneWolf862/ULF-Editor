"""Generated, non-personal profile 46/player 33 fixture."""

import hashlib
import struct

from core.fch import Item, stable_hash, string


def character_bytes(item_bytes=None, skill_bytes=None, profile_version=46, player_version=33,
                    inventory_version=109, skills_version=2, unique_entries=(), player_tail=None):
    def pack(fmt,*values):
        return struct.pack("<"+fmt,*values)
    item = Item(stable_hash("Wood"), 0, 0, stack=5, tail=5)
    player = pack("i4f", player_version, 100, 100, 100, 100) + string("")
    if player_version>=24:player+=pack("f",0)
    items=[item.to_bytes()] if item_bytes is None else item_bytes
    player += pack("iH", inventory_version, len(items)) + b"".join(items)
    player += pack("i", 0) * 4
    player += pack("i", len(unique_entries)) + b"".join(map(string, unique_entries))
    player += pack("i", 0) * 3
    player += string("") * 2 + bytes(24) + pack("ii", 0, 0)
    skills=[pack("iff",1,10.125,0.375)] if skill_bytes is None else skill_bytes
    if player_tail is None:
        player_tail = b"opaque-tail"
        if player_version == 34:
            build_ui = b"synthetic-build-ui"
            player_tail = (pack("i", 1) + string("fixture") + string("value")
                           + pack("fffi", 64.125, 10, 3.5, len(build_ui)) + build_ui
                           + pack("iii", 1, 17, 23) + pack("iii", 1, -456, 789))
    player += pack("ii",skills_version,len(skills))+b"".join(skills)+player_tail
    if profile_version == 47:
        maps = b"synthetic-map"
        command_history = pack("i", 1) + string("synthetic-history") + pack("f", 12)
        bucket = pack("f", 4) + pack("i", 0) * 8 + command_history
        world = pack("qB", 123, 1) + bytes(12) + pack("B", 1) + bytes(12)
        world += pack("B", 0) + bytes(24) + pack("Bi", 1, len(maps)) + maps
        body = pack("iii", profile_version, 1, 1) + bucket + pack("Bi", 0, 1) + world
    else:
        body = pack("iiiBi", profile_version, 0, 0, 0, 0)
    body += string("Synthetic") + pack("q", 0) + string("")
    body += pack("BqB", 1, 0, 1) + pack("i", len(player)) + player
    return pack("i", len(body)) + body + pack("i", 64) + hashlib.sha512(body).digest()


def current_character_bytes(**overrides):
    return character_bytes(**({"profile_version": 47, "player_version": 34,
                               "inventory_version": 110} | overrides))
