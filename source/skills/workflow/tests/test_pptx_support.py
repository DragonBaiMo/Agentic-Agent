"""SPDX-License-Identifier: MIT

Test observable data/crop invariants with diagnostic pixels, never deck artwork.
"""
import copy
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from PIL import Image

ROOT=Path(__file__).parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from crop_alpha import crop_asset
from pptx_backend.contract import compile_deck, inside, numeric_box, pending_art, resolve_data

TMP=ROOT/'tmp/pptx-support-tests';TMP.mkdir(parents=True,exist_ok=True)


class PptxSupportTests(unittest.TestCase):
    """Each case uses its own project and asserts actual bytes or computed coordinates."""

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=TMP)
        self.root=Path(self.temp.name)
        self.source=self.root/'art.png'
        image=Image.new('RGBA',(20,20),(0,0,0,0))
        image.putpixel((5,7),(80,30,20,255));image.putpixel((4,7),(80,30,20,1))
        image.save(self.source)
        self.plan={'schema_version':'pptx-1','canvas':[20,20],'background':'art.png',
            'slides':[{'id':'S01','elements':[{'kind':'image','id':'art','file':'art.png',
            'box':[0,0,20,20],'alt':'Diagnostic asset'}]}]}
        self.binding={'key':'score','approved_value':72.6,'file':'art.png','object_id':'art',
            'sha256':hashlib.sha256(self.source.read_bytes()).hexdigest()}

    def tearDown(self):
        self.temp.cleanup()

    def test_valid_deck_compiles_without_mutating_source(self):
        before=copy.deepcopy(self.plan)
        actual,pending=compile_deck(self.root,self.plan,{})
        self.assertEqual(actual,self.plan)
        self.assertEqual(pending,[])
        self.assertEqual(before,self.plan)

    def test_single_data_source_fills_native_value(self):
        self.plan['slides'][0]['elements'].append({'kind':'chart','id':'chart','options':{'value':0}})
        self.plan['data_bindings']=[{'key':'score','path':['slides',0,'elements',1,'options','value']}]
        actual,_=compile_deck(self.root,self.plan,{'score':80})
        self.assertEqual(actual['slides'][0]['elements'][1]['options']['value'],80)
        self.assertEqual(self.plan['slides'][0]['elements'][1]['options']['value'],0)

    def test_unchanged_art_matches_value_and_bytes(self):
        self.assertEqual(pending_art(self.root,{'score':72.6},[self.binding]),[])

    def test_changed_value_requires_art_replacement(self):
        result=pending_art(self.root,{'score':80},[self.binding])
        self.assertEqual(result[0]['new_value'],80)
        self.assertEqual(result[0]['old_value'],72.6)

    def test_changed_art_bytes_require_recheck(self):
        self.binding['sha256']='0'*64
        self.assertEqual(len(pending_art(self.root,{'score':72.6},[self.binding])),1)

    def test_declared_derived_reduction(self):
        source={'old':75,'new':40,'_derived':[{'key':'less','operation':'reduction_percent',
            'baseline':'old','current':'new','decimals':0}]}
        self.assertEqual(resolve_data(source)['less'],47)
        self.assertNotIn('less',source)

    def test_zero_baseline_rejected(self):
        source={'old':0,'new':40,'_derived':[{'key':'less','operation':'reduction_percent','baseline':'old','current':'new'}]}
        with self.assertRaisesRegex(ValueError,'invalid_derived'):
            resolve_data(source)

    def test_path_traversal_rejected(self):
        with self.assertRaisesRegex(ValueError,'outside_project'):
            inside(self.root,'../outside.png')

    def test_symlink_escape_rejected(self):
        (self.root/'escape').symlink_to(self.root.parent,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'outside_project'):
            inside(self.root,'escape/outside.png')

    def test_duplicate_object_rejected(self):
        self.plan['slides'][0]['elements'].append(copy.deepcopy(self.plan['slides'][0]['elements'][0]))
        with self.assertRaisesRegex(ValueError,'duplicate_object_id'):
            compile_deck(self.root,self.plan,{})

    def test_duplicate_slide_rejected(self):
        self.plan['slides'].append(copy.deepcopy(self.plan['slides'][0]))
        with self.assertRaisesRegex(ValueError,'duplicate_slide_id'):
            compile_deck(self.root,self.plan,{})

    def test_unknown_schema_rejected(self):
        self.plan['schema_version']='PSD'
        with self.assertRaisesRegex(ValueError,'unsupported_deck_schema'):
            compile_deck(self.root,self.plan,{})

    def test_missing_asset_rejected(self):
        self.plan['slides'][0]['elements'][0]['file']='missing.png'
        with self.assertRaisesRegex(ValueError,'missing_asset'):
            compile_deck(self.root,self.plan,{})

    def test_nonfinite_geometry_rejected(self):
        with self.assertRaisesRegex(ValueError,'invalid_box'):
            numeric_box([0,0,float('nan'),1])

    def test_zero_size_rejected(self):
        with self.assertRaisesRegex(ValueError,'empty_box'):
            numeric_box([0,0,0,1])

    def test_crop_retains_alpha_one_and_compensates_origin(self):
        output=self.root/'crop.png'
        result=crop_asset(self.source,output,[100,200,200,200],1,0)
        self.assertEqual(result['crop_xywh'],[4,7,2,1])
        self.assertEqual(result['target_xywh'],[140,270,20,10])
        self.assertEqual(result['discarded_alpha_mass'],0)
        self.assertEqual(Image.open(output).getpixel((0,0)),(80,30,20,1))

    def test_padding_preserves_weak_soft_edge_at_higher_threshold(self):
        result=crop_asset(self.source,self.root/'crop.png',[0,0,20,20],4,2)
        self.assertEqual(result['crop_xywh'],[3,5,5,5])
        self.assertEqual(result['discarded_alpha_mass'],0)

    def test_bad_target_does_not_leave_an_output(self):
        output=self.root/'bad.png'
        with self.assertRaisesRegex(ValueError,'invalid_target'):
            crop_asset(self.source,output,[0,0,0,20])
        self.assertFalse(output.exists())

    def test_crop_rejects_overwrite(self):
        with self.assertRaisesRegex(ValueError,'output_exists'):
            crop_asset(self.source,self.source,[0,0,20,20])

    def test_crop_rejects_empty_transparency(self):
        Image.new('RGBA',(20,20),(0,0,0,0)).save(self.source)
        with self.assertRaisesRegex(ValueError,'empty_alpha'):
            crop_asset(self.source,self.root/'crop.png',[0,0,20,20])


if __name__=='__main__':
    unittest.main()
