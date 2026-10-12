"""Real binary fixtures; mocks inject IO failures only, never identity/parser output."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from export_dtb_consumers import canonical_bytes,export,SCHEMA_VERSION,TOOL_VERSION,_publish_no_replace
from test_dtb_consumer_evidence import fixture,FIX
from test_dtb_tree import pack_tree
from test_dtb_reserved_memory import fixture as reserved_fixture

class ExportTests(unittest.TestCase):
    def test_canonical_schema_and_stability(self):
        blob=(FIX/'consumer-positive.dtb').read_bytes()
        first=canonical_bytes(blob);self.assertEqual(first,canonical_bytes(blob));data=json.loads(first)
        self.assertEqual(list(data),['schema_version','tool_version','input_sha256','root_identity','consumers','physical_source_authenticated','build_gate_authorization','hardware_tested'])
        self.assertEqual(data['schema_version'],SCHEMA_VERSION);self.assertEqual(SCHEMA_VERSION,'wayne.consumer-evidence.v1');self.assertEqual(TOOL_VERSION,'export-dtb-consumers/1')
        self.assertEqual([r['source_path'] for r in data['consumers']],['/first','/second'])
        self.assertEqual(data['consumers'][1]['optional_properties'][0]['presence'],'absent')
        self.assertIsNone(data['consumers'][1]['optional_properties'][0]['raw'])
        self.assertEqual(data['consumers'][0]['targets'][1]['reg'],[[7,0]])
        multi=json.loads(canonical_bytes(reserved_fixture()))
        self.assertEqual(multi['consumers'][0]['targets'][0]['reg'],[[7,0],[9,3]])
        for name,p in data['root_identity'].items():self.assertEqual(blob[p['value_offset']:p['value_offset']+p['length']].hex(),p['hex'])

    def test_stdout_file_identical_and_idempotent(self):
        blob=fixture()
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);dtb=p/'input.dtb';dtb.write_bytes(blob);out=p/'evidence.json'
            expected=export(blob,out);self.assertEqual(expected,export(blob,out))
            result=subprocess.run([sys.executable,str(Path(__file__).with_name('export_dtb_consumers.py')),str(dtb)],capture_output=True)
            self.assertEqual(result.returncode,0);self.assertEqual(result.stdout,out.read_bytes())

    def test_identity_and_consumer_rejection_no_output(self):
        vectors=[(FIX/'identity-jasmine.dtb').read_bytes(),(FIX/'identity-model-conflict.dtb').read_bytes(),(FIX/'identity-truncated.dtb').read_bytes(),(FIX/'identity-malformed.dtb').read_bytes(),fixture(reg=b'bad')]
        vectors += [pack_tree([('begin',''),('end',None)]),pack_tree([('begin',''),('prop',('model',b'MI 6X')),('prop',('compatible',b'xiaomi,wayne\0qcom,sdm660\0')),('end',None)])]
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)/'result.json'
            for blob in vectors:
                with self.subTest(blob=blob[:16]),self.assertRaises(ValueError):export(blob,out)
                self.assertFalse(out.exists())
            out.write_bytes(b'preserved')
            with self.assertRaises(ValueError):export(vectors[0],out)
            self.assertEqual(out.read_bytes(),b'preserved')

    def test_existing_mismatch_and_concurrent_creation(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);out=p/'out.json';out.write_bytes(b'{"input_sha256":"different"}')
            with self.assertRaises(ValueError):export(fixture(),out)
            self.assertEqual(out.read_bytes(),b'{"input_sha256":"different"}')
            temp=p/'temporary';temp.write_bytes(b'new')
            with self.assertRaises(OSError):_publish_no_replace(temp,out)
            self.assertTrue(temp.exists());self.assertNotEqual(out.read_bytes(),b'new')

    def test_temp_write_failure_cleanup(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);out=p/'out.json'
            with patch('export_dtb_consumers.os.fsync',side_effect=OSError('injected write failure')):
                with self.assertRaises(OSError):export(fixture(),out)
            self.assertEqual(list(p.iterdir()),[])
            with patch('export_dtb_consumers._publish_no_replace',side_effect=OSError('injected rename failure')):
                with self.assertRaises(OSError):export(fixture(),out)
            self.assertEqual(list(p.iterdir()),[])

if __name__=='__main__':unittest.main()
