import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from core.fch import Character,stable_hash

class TestFch(unittest.TestCase):
 def test_hash(self):self.assertIsInstance(stable_hash('Wood'),int)
 def test_sample_roundtrip(self):
  p=pathlib.Path(__file__).parent/'fixtures'/'wolf.fch'
  if not p.exists():self.skipTest('Private fixture not bundled')
  raw=p.read_bytes();c=Character(raw);self.assertTrue(c.roundtrip);self.assertEqual(raw,c.serialize())
 def test_edit_preserves_flags(self):
  p=pathlib.Path(__file__).parent/'fixtures'/'wolf.fch'
  if not p.exists():self.skipTest('Private fixture not bundled')
  c=Character(p.read_bytes());initial=c.used_cheats
  c.items[0].quality=33;c.set_skill(1,87)
  d=Character(c.serialize());self.assertEqual(d.items[0].quality,33);self.assertEqual(d.used_cheats,initial)
if __name__=='__main__':unittest.main()
