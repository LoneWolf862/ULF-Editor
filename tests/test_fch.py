import pathlib,sys,unittest
import hashlib,struct
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from core.fch import Character,stable_hash
from synthetic import character_bytes

class TestFch(unittest.TestCase):
 def test_hash(self):self.assertIsInstance(stable_hash('Wood'),int)
 def test_sample_roundtrip(self):
  raw=character_bytes();c=Character(raw);self.assertTrue(c.roundtrip);self.assertEqual(raw,c.serialize())
 def test_edit_preserves_flags(self):
  c=Character(character_bytes());initial=c.used_cheats
  c.items[0].quality=33;c.set_skill(1,87)
  d=Character(c.serialize());self.assertEqual(d.items[0].quality,33);self.assertEqual(d.used_cheats,initial)
 def test_fr003_unsupported_profile(self):
  raw=character_bytes();length=struct.unpack_from('<i',raw)[0]
  body=bytearray(raw[4:4+length]);struct.pack_into('<i',body,0,999)
  changed=struct.pack('<i',len(body))+body+struct.pack('<i',64)+hashlib.sha512(body).digest()
  with self.assertRaises(ValueError):Character(changed)
 def test_fr002_truncated_files(self):
  raw=character_bytes()
  for size in (0,1,4,20,len(raw)-1):
   with self.subTest(size=size):
    with self.assertRaises(ValueError):Character(raw[:size])
if __name__=='__main__':unittest.main()
