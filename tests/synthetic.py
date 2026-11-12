"""Generated, non-personal profile 46/player 33 fixture."""

import hashlib
import struct

from core.fch import Item, stable_hash, string


def character_bytes(item_bytes=None, skill_bytes=None, profile_version=46, player_version=33, inventory_version=109, skills_version=2):
    def pack(fmt,*values):
        return struct.pack("<"+fmt,*values)
    item = Item(stable_hash("Wood"), 0, 0, stack=5, tail=5)
    player = pack("i4f", player_version, 100, 100, 100, 100) + string("")
    if player_version>=24:player+=pack("f",0)
    items=[item.to_bytes()] if item_bytes is None else item_bytes
    player += pack("iH", inventory_version, len(items)) + b"".join(items)
    player += pack("i", 0) * 8
    player += string("") * 2 + bytes(24) + pack("ii", 0, 0)
    skills=[pack("iff",1,10.125,0.375)] if skill_bytes is None else skill_bytes
    player += pack("ii",skills_version,len(skills))+b"".join(skills)+b"opaque-tail"
    body = pack("iiiBi", profile_version, 0, 0, 0, 0)
    body += string("Synthetic") + pack("q", 0) + string("")
    body += pack("BqB", 1, 0, 1) + pack("i", len(player)) + player
    return pack("i", len(body)) + body + pack("i", 64) + hashlib.sha512(body).digest()
