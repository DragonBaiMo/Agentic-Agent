"""SPDX-License-Identifier: MIT

Check prepared versus real returned image evidence without making model calls.
"""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import unittest
from PIL import Image

ROOT=Path(__file__).parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from image_job import prepare, register
from project_io import write_json
TMP=ROOT/'tmp/image-job-tests';TMP.mkdir(parents=True,exist_ok=True)


class ImageJobTests(unittest.TestCase):
    """Isolate each registry and preserve exact copied reference bytes."""

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=TMP);self.root=Path(self.temp.name)
        self.image=self.root/'reference.png'
        Image.new('RGBA',(16,16),(0,0,0,128)).save(self.image)
        write_json(self.root/'jobs.json',{'tasks':{'S01':{'prompt':'A precise low-noise test image.',
            'references':['reference.png'],'transparent_background':True}}})

    def tearDown(self):
        self.temp.cleanup()

    def arguments(self):
        """Return explicit fixture arguments for one actual user-supplied image import."""
        return argparse.Namespace(project=self.root,task='S01',source=self.image,
            origin='user_supplied',tool='upload',call_id='not_exposed',execution=None,
            status='assets',reason='',job=None)

    def test_prepare_copies_real_reference_and_never_records_generation(self):
        prepare(self.root,'S01','jobs/J01')
        request=json.loads((self.root/'jobs/J01/request.json').read_text())
        self.assertEqual(request['status'],'prepared_not_executed')
        self.assertEqual((self.root/'jobs/J01/reference-1.png').read_bytes(),self.image.read_bytes())
        self.assertFalse((self.root/'receipts.json').exists())

    def test_prepare_refuses_overwrite(self):
        prepare(self.root,'S01','jobs/J01')
        with self.assertRaisesRegex(ValueError,'job_exists'):
            prepare(self.root,'S01','jobs/J01')

    def test_prepare_rejects_missing_reference(self):
        self.image.unlink()
        with self.assertRaisesRegex(ValueError,'reference_missing'):
            prepare(self.root,'S01','jobs/J01')

    def test_register_saves_exact_returned_bytes_and_unknown_call_id(self):
        result=register(self.arguments())
        row=json.loads((self.root/'receipts.json').read_text())[0]
        self.assertEqual((self.root/result['file']).read_bytes(),self.image.read_bytes())
        self.assertEqual(row['status'],'result_recorded')
        self.assertEqual(row['call_id'],'not_exposed')
        self.assertEqual(row['backend_binding_observed'],'not_exposed')

    def test_register_rejected_result_does_not_adopt_into_deck(self):
        args=self.arguments();args.status='rejected';args.reason='wrong text'
        result=register(args)
        row=json.loads((self.root/'receipts.json').read_text())[0]
        self.assertTrue(result['file'].startswith('rejected/'))
        self.assertEqual(row['reason'],'wrong text')
        self.assertFalse((self.root/'deck.json').exists())

    def test_register_keeps_preparation_snapshot(self):
        prepare(self.root,'S01','jobs/J01')
        args=self.arguments();args.job='jobs/J01';register(args)
        row=json.loads((self.root/'receipts.json').read_text())[0]
        self.assertEqual(row['preparation']['status'],'prepared_not_executed')
        self.assertEqual(row['status'],'result_recorded')


if __name__=='__main__':
    unittest.main()
