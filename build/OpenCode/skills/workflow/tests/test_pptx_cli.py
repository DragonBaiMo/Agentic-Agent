"""SPDX-License-Identifier: MIT

Exercise the actual new CLI entrypoints, including structured failures and saved evidence.
"""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

ROOT=Path(__file__).parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import crop_alpha
import image_job
import pptx_project
from project_io import write_json

TMP=ROOT/'tmp/pptx-cli-tests';TMP.mkdir(parents=True,exist_ok=True)


class PptxCliTests(unittest.TestCase):
    """Run public parsers in-process so statements and error paths stay measurable."""

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=TMP);self.root=Path(self.temp.name)
        self.image=self.root/'art.png'
        im=Image.new('RGBA',(20,20),(0,0,0,0));im.putpixel((5,7),(30,40,50,255));im.save(self.image)
        self.plan={'schema_version':'pptx-1','canvas':[20,20],'background':'art.png',
            'slides':[{'id':'S01','elements':[{'kind':'image','id':'title','file':'art.png','box':[0,0,20,20],'alt':'test'}]}]}
        write_json(self.root/'deck.json',self.plan)
        write_json(self.root/'jobs.json',{'tasks':{'S01':{'prompt':'Test actual preparation.',
            'references':['art.png'],'transparent_background':True}}})

    def tearDown(self):
        self.temp.cleanup()

    def test_compile_cli_writes_real_output(self):
        with patch.object(sys,'argv',['pptx_project','--project',str(self.root),'--out','builds/B01/compiled.json']),self.assertLogs(level='INFO'):
            pptx_project.main()
        actual=json.loads((self.root/'builds/B01/compiled.json').read_text())
        self.assertEqual(actual['slides'][0]['elements'][0]['file'],'art.png')

    def test_compile_cli_refuses_collision(self):
        write_json(self.root/'compiled.json',{'prior':'kept'})
        with patch.object(sys,'argv',['pptx_project','--project',str(self.root),'--out','compiled.json']),self.assertLogs(level='ERROR'),self.assertRaises(SystemExit) as error:
            pptx_project.main()
        self.assertEqual(error.exception.code,2)
        self.assertEqual(json.loads((self.root/'compiled.json').read_text()),{'prior':'kept'})

    def test_compile_cli_reports_invalid_native_theme_without_traceback(self):
        del self.plan['background']
        self.plan['theme']=[]
        write_json(self.root/'deck.json',self.plan)
        argv=['pptx_project','--project',str(self.root),'--out','compiled.json']
        with patch.object(sys,'argv',argv),self.assertLogs(level='ERROR') as log,self.assertRaises(SystemExit) as error:
            pptx_project.main()
        self.assertEqual(error.exception.code,2)
        self.assertIn('invalid_solid_background: theme',log.output[0])
        self.assertFalse((self.root/'compiled.json').exists())

    def test_compile_cli_saves_pending_art_job_and_stops(self):
        self.plan['data_file']='data.json'
        self.plan['art_bindings']=[{'key':'score','approved_value':72.6,'file':'art.png','object_id':'title',
            'sha256':hashlib.sha256(self.image.read_bytes()).hexdigest()}]
        write_json(self.root/'deck.json',self.plan);write_json(self.root/'data.json',{'score':80})
        with patch.object(sys,'argv',['pptx_project','--project',str(self.root),'--out','builds/B01/compiled.json']),self.assertLogs(level='ERROR'),self.assertRaises(SystemExit) as error:
            pptx_project.main()
        self.assertEqual(error.exception.code,2)
        actual=json.loads((self.root/'builds/B01/pending-art-replacements.json').read_text())
        self.assertEqual(actual[0]['new_value'],80)
        self.assertFalse((self.root/'builds/B01/compiled.json').exists())

    def test_compile_cli_rejects_missing_art_target_without_writing_candidate(self):
        self.plan['data_file']='data.json'
        self.plan['art_bindings']=[{'key':'score','approved_value':80,'file':'art.png','object_id':'missing',
            'sha256':hashlib.sha256(self.image.read_bytes()).hexdigest()}]
        write_json(self.root/'deck.json',self.plan);write_json(self.root/'data.json',{'score':80})
        before=(self.root/'deck.json').read_bytes()
        argv=['pptx_project','--project',str(self.root),'--out','builds/B01/compiled.json']
        with patch.object(sys,'argv',argv),self.assertLogs(level='ERROR') as log,self.assertRaises(SystemExit) as error:
            pptx_project.main()
        self.assertEqual(error.exception.code,2)
        self.assertIn('art_binding_target_missing: */missing',log.output[0])
        self.assertFalse((self.root/'builds/B01/compiled.json').exists())
        self.assertEqual((self.root/'deck.json').read_bytes(),before)

    def test_crop_cli_saves_compensated_ledger(self):
        argv=['crop_alpha','--input',str(self.image),'--output',str(self.root/'crop.png'),
              '--target','0','0','200','200','--padding','0','--ledger',str(self.root/'ledger.json')]
        with patch.object(sys,'argv',argv),self.assertLogs(level='INFO'):
            crop_alpha.main()
        actual=json.loads((self.root/'ledger.json').read_text())
        self.assertEqual(actual['target_xywh'],[50,70,10,10])

    def test_crop_cli_does_not_replace_existing_ledger(self):
        write_json(self.root/'ledger.json',{'prior':'kept'})
        argv=['crop_alpha','--input',str(self.image),'--output',str(self.root/'crop.png'),
              '--target','0','0','200','200','--ledger',str(self.root/'ledger.json')]
        with patch.object(sys,'argv',argv),self.assertLogs(level='ERROR'),self.assertRaises(SystemExit) as error:
            crop_alpha.main()
        self.assertEqual(error.exception.code,2)
        self.assertFalse((self.root/'crop.png').exists())

    def test_job_cli_prepare_then_record_is_separate(self):
        argv=['image_job','prepare','--project',str(self.root),'--task','S01','--out','jobs/J01']
        with patch.object(sys,'argv',argv),self.assertLogs(level='INFO'):
            image_job.main()
        argv=['image_job','record','--project',str(self.root),'--task','S01','--source',str(self.image),
              '--origin','user_supplied','--tool','upload','--job','jobs/J01']
        with patch.object(sys,'argv',argv),self.assertLogs(level='INFO'):
            image_job.main()
        actual=json.loads((self.root/'receipts.json').read_text())[0]
        self.assertEqual(actual['status'],'result_recorded')
        self.assertEqual(actual['preparation']['status'],'prepared_not_executed')

    def test_job_cli_error_preserves_failure_status(self):
        argv=['image_job','prepare','--project',str(self.root),'--task','unknown','--out','jobs/J01']
        with patch.object(sys,'argv',argv),self.assertLogs(level='ERROR'),self.assertRaises(SystemExit) as error:
            image_job.main()
        self.assertEqual(error.exception.code,2)
        self.assertFalse((self.root/'receipts.json').exists())


if __name__=='__main__':
    unittest.main()
