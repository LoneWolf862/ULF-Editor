"""Synthetic field-specific FR-092/005/050/053/060 preservation tests."""
from dataclasses import replace
from pathlib import Path
import struct
import tempfile
import unittest

from core.appearance import CATALOG, FIELDS, apply_appearance, encoded_middle, protected_middle
from core.export import export_character
from core.fch import Character, FormatError, string
from synthetic import character_bytes, current_character_bytes
from desktop.session import Session


def fixture(**overrides):
    values = dict(beard="Beard1", hair="Hair7", skin=(.1, .2, .3), hair_color=(.4, .5, .6), model=0)
    values.update(overrides)
    appearance = (string(values['beard']) + string(values['hair']) +
                  struct.pack('<6fi', *values['skin'], *values['hair_color'], values['model']))
    return current_character_bytes(appearance_bytes=appearance)


class AppearanceTests(unittest.TestCase):
    def test_fr020_grouped_and_mixed_history_restores_exact_bytes(self):
        s=Session(Character(fixture()),Path('synthetic.fch')); states=[s.working.serialize()]
        s.apply_appearance_batch({'hair':'HairNone','hair_color':(.1,.2,.3)})
        states.append(s.working.serialize())
        s.edit_item(('item',0),{'stack':6});states.append(s.working.serialize())
        s.apply_skill_batch([(1,30,None)]);states.append(s.working.serialize())
        s.apply_appearance_batch({'model':1,'beard':'BeardNone'});states.append(s.working.serialize())
        self.assertEqual(len(s.history.past),4)
        for state in reversed(states[:-1]):s.undo();self.assertEqual(s.working.serialize(),state)
        for state in states[1:]:s.redo();self.assertEqual(s.working.serialize(),state)

    def test_fr020_appearance_drafts_block_history_and_divergence(self):
        s=Session(Character(fixture()),Path('synthetic.fch'))
        s.apply_appearance_batch({'hair':'Hair1'});s.undo()
        s.appearance_drafts={'skin_color':('bad','0','0')}
        self.assertTrue(s.has_drafts)
        with self.assertRaises(FormatError):s.redo()
        with self.assertRaises(FormatError):s.apply_appearance_batch({'model':1})
        self.assertEqual(len(s.history.future),1)
        s.appearance_drafts.clear();s.apply_appearance_batch({'hair':'Hair2'})
        self.assertFalse(s.history.future)

    def test_fr054_appearance_review_discard_and_noop(self):
        s=Session(Character(fixture()),Path('synthetic.fch'))
        s.apply_appearance_batch({'hair':'Hair7'})
        self.assertFalse(s.history.past);self.assertFalse(s.changes())
        s.apply_appearance_batch({'hair':'HairNone','skin_color':(.3,.4,.5)})
        changes=s.changes();self.assertEqual(len(changes),1)
        self.assertEqual(len(changes[0].details),2)
        s.discard({('appearance',0)})
        self.assertEqual(s.working.serialize(),s.baseline.original)
        s.undo();self.assertEqual(len(s.changes()),1)
        s.appearance_drafts={'hair':'Hair1'};s.discard_all()
        self.assertFalse(s.has_drafts);self.assertFalse(s.changes())

    def test_fr005_raw_nan_signed_zero_and_noncanonical_strings(self):
        raw=(b'\x89\x00BeardNone'+string('ModHair')+
             bytes.fromhex('0100c07f000000800000803f')+struct.pack('<3fi',.1,.2,.3,0))
        c=Character(current_character_bytes(appearance_bytes=raw))
        self.assertEqual(c.serialize(),c.original)
        apply_appearance(c,{'hair':'HairNone'})
        after=Character(c.serialize());a,b=after._appearance_spans['beard']
        self.assertEqual(after.middle[a:b],b'\x89\x00BeardNone')
        a,b=after._appearance_spans['skin_color']
        self.assertEqual(after.middle[a:b],bytes.fromhex('0100c07f000000800000803f'))

    def test_fr051_mixed_history_export_preserves_identity_and_unknowns(self):
        s=Session(Character(fixture()),Path('synthetic.fch'))
        s.apply_appearance_batch({'hair':'HairNone'})
        s.organize(('item',0),'move',(1,0));s.undo();s.redo()
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'input.fch';target=Path(folder)/'output.fch'
            source.write_bytes(s.baseline.original);export_character(s.working,source,target)
            actual=Character(target.read_bytes())
            self.assertEqual(actual.serialize(),s.working.serialize())
            self.assertEqual(actual.prefix,s.baseline.prefix)
            self.assertEqual(actual.tail,s.baseline.tail)
            self.assertEqual(actual.items[0].tail,s.baseline.items[0].tail)
            self.assertEqual(source.read_bytes(),s.baseline.original)

    def test_fr092_catalog_build_counts_labels_and_model_rules(self):
        self.assertEqual(CATALOG['game_version'], '1.0.21')
        self.assertEqual((len(CATALOG['hair']), len(CATALOG['beard'])), (39, 27))
        self.assertEqual(CATALOG['beard']['BeardNone']['models'], [0, 1])
        self.assertTrue(all('_' not in k for group in ('hair', 'beard') for k in CATALOG[group]))

    def test_fr005_supported_layouts_noop_and_legacy_readonly(self):
        for version in range(23, 34):
            c = Character(character_bytes(player_version=version))
            self.assertEqual(c.serialize(), c.original)
            with self.assertRaises(FormatError):
                apply_appearance(c, {'hair': 'Hair1'})
        c = Character(fixture())
        self.assertEqual(c.appearance.hair, 'Hair7')
        self.assertEqual(c.appearance.beard, 'Beard1')
        self.assertEqual(c.serialize(), c.original)

    def test_fr092_each_field_changes_only_its_span(self):
        for field, value in [('hair', 'HairNone'), ('beard', 'BeardNone'),
                             ('hair_color', (.2, .5, .6)), ('skin_color', (.4, .2, .3)),
                             ('model', 1)]:
            with self.subTest(field=field):
                c = Character(fixture(beard='BeardNone'))
                old = Character(c.original)
                apply_appearance(c, {field: value})
                reopened = Character(c.serialize())
                for other in FIELDS:
                    if other != field:
                        a,b = old._appearance_spans[other]; x,y = reopened._appearance_spans[other]
                        self.assertEqual(old.middle[a:b], reopened.middle[x:y])
                self.assertEqual(protected_middle(old), protected_middle(reopened))
                for name in ('prefix','suffix','head','tail','_skill_bytes'):
                    self.assertEqual(getattr(old,name),getattr(reopened,name))
                self.assertEqual([i.to_bytes() for i in old.items], [i.to_bytes() for i in reopened.items])

    def test_fr092_grouped_model_resolution_explicit(self):
        c = Character(fixture()); before = c.serialize()
        with self.assertRaisesRegex(FormatError, 'explicit BeardNone'):
            apply_appearance(c, {'model': 1})
        self.assertEqual(c.serialize(), before)
        apply_appearance(c, {'model': 1, 'beard': 'BeardNone', 'hair': 'Hair2'})
        self.assertEqual((c.appearance.model,c.appearance.beard,c.appearance.hair),(1,'BeardNone','Hair2'))

    def test_fr092_invalid_proposals_atomic(self):
        for proposal in ({'model': 2}, {'model': True}, {'hair': 'Unknown'}, {'beard': ''},
                         {'skin_color': (float('inf'),0,0)}, {'hair_color': (-.1,0,0)},
                         {'skin_color': (1.1,0,0)}, {'hair_color': (0,0)}, {'name': 'Other'}):
            c = Character(fixture()); before = c.serialize()
            with self.subTest(proposal=proposal), self.assertRaises(FormatError):
                apply_appearance(c, {'hair': 'HairNone', **proposal})
            self.assertEqual(c.serialize(),before)

    def test_fr005_unknown_styles_model_and_float_values_preserved(self):
        c=Character(fixture(hair='ModHair',beard='ModBeard',model=99,skin=(float('nan'),-0.,3)))
        self.assertEqual(c.serialize(),c.original)
        apply_appearance(c,{'hair_color':(.1,.2,.3)})
        new=Character(c.serialize())
        self.assertEqual((new.appearance.hair,new.appearance.beard,new.appearance.model),('ModHair','ModBeard',99))
        a,b=c._appearance_spans['skin_color'];self.assertEqual(c.middle[a:b],new.middle[a:b])

    def test_fr005_noop_and_float32_quantization(self):
        c=Character(fixture())
        apply_appearance(c,{field:getattr(c.appearance,field) for field in FIELDS})
        self.assertEqual(c.serialize(),c.original)
        apply_appearance(c,{'skin_color':(.123456789,.2,.3)})
        self.assertEqual(c.appearance.skin_color[0],struct.unpack('<f',struct.pack('<f',.123456789))[0])
        self.assertEqual(Character(c.serialize()).serialize(),c.serialize())

    def test_fr050_export_roundtrip_and_source_protection(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'in.fch'; target=Path(directory)/'out.fch'
            c=Character(fixture());source.write_bytes(c.original)
            apply_appearance(c,{'hair':'HairNone','skin_color':(.7,.8,.9)})
            export_character(c,source,target)
            self.assertEqual(Character(target.read_bytes()).serialize(),c.serialize())
            self.assertEqual(source.read_bytes(),c.original)
            with self.assertRaises(FormatError): export_character(c,source,source)

    def test_fr053_export_revalidates_bypassed_appearance(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'in.fch';target=Path(directory)/'out.fch'
            c=Character(fixture());source.write_bytes(c.original)
            c.appearance=replace(c.appearance,hair='InjectedUnknown')
            with self.assertRaises(FormatError):export_character(c,source,target)
            self.assertFalse(target.exists())

    def test_fr060_export_rejects_unrelated_middle_change(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'in.fch';target=Path(directory)/'out.fch'
            c=Character(fixture());source.write_bytes(c.original)
            # Replace an empty known-recipes list with one entry; all appearance
            # offsets are reconstructed by reparsing, not trusted from the caller.
            c.middle=struct.pack('<i',1)+string('InjectedRecipe')+c.middle[4:]
            offset=len(string('InjectedRecipe'))
            c._appearance_spans={k:(a+offset,b+offset) for k,(a,b) in c._appearance_spans.items()}
            with self.assertRaises(FormatError):export_character(c,source,target)
            self.assertFalse(target.exists())
