import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from import_wayne_board_evidence import validate

FIXTURE = Path(__file__).resolve().parents[1] / 'tests/fixtures/wayne-evidence'

class EvidenceTests(unittest.TestCase):
    def test_fixture_positive_never_unlocks(self):
        result = validate(FIXTURE / 'manifest.json')
        self.assertFalse(result['build_gate_authorization'])
        self.assertFalse(result['physical_identity_verified'])
        self.assertEqual(result['role'], 'synthetic_fixture')

    def test_rejections(self):
        base = json.loads((FIXTURE / 'manifest.json').read_text())
        blob = (FIXTURE / 'getprop.txt').read_bytes()
        cases = ['missing', 'hash', 'source', 'jasmine', 'model', 'tool', 'compatible']
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as folder:
                p = Path(folder); data = copy.deepcopy(base); payload = blob
                if case == 'missing': data['files'][0]['path'] = 'absent'
                if case == 'hash': data['files'][0]['sha256'] = '0' * 64
                if case == 'source': data['source']['description'] = 'unknown'
                if case == 'jasmine': payload = blob.replace(b'vendor.device]: [wayne', b'vendor.device]: [jasmine')
                if case == 'model': payload = blob.replace(b'MI 6X', b'Mi A2')
                if case in ('tool', 'compatible'): data['files'][0]['kind'] = 'dtb'
                if payload != blob: data['files'][0]['sha256'] = hashlib.sha256(payload).hexdigest()
                (p/'getprop.txt').write_bytes(payload)
                (p/'manifest.json').write_text(json.dumps(data))
                with patch('import_wayne_board_evidence.shutil.which', return_value=None if case == 'tool' else '/mock/fdtget'), patch('import_wayne_board_evidence.subprocess.run') as run:
                    run.return_value.stdout = 'Mi 6X' # parser mock only: incompatible compatible property
                    with self.assertRaises(ValueError): validate(p/'manifest.json')

if __name__ == '__main__': unittest.main()
