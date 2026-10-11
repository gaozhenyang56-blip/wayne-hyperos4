"""Binary fixtures are synthetic format vectors, never actual wayne board evidence."""
import copy
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
from import_wayne_board_evidence import validate
from read_dtb_identity import read_identity

FIX = Path(__file__).resolve().parents[1] / 'tests/fixtures/wayne-evidence'

def make_dtb(model='MI 6X', compatible=('xiaomi,wayne', 'qcom,sdm660'), duplicate=False):
    def word(*values): return struct.pack('>' + 'I' * len(values), *values)
    def padded(value): return value + b'\0' * (-len(value) % 4)
    strings = b'model\0compatible\0'
    def prop(offset, value): return word(3, len(value), offset) + padded(value)
    identity = prop(0, model.encode() + b'\0') + prop(6, b'\0'.join(c.encode() for c in compatible) + b'\0')
    stream = word(1) + word(0) + identity + (prop(0, b'Mi A2\0') if duplicate else b'') + word(2, 9)
    return word(0xd00dfeed, 56 + len(stream) + len(strings), 56, 56 + len(stream), 40, 17, 16, 0, len(strings), len(stream)) + b'\0' * 16 + stream + strings

class DTBTests(unittest.TestCase):
    def test_binary_positive(self):
        blob = (FIX/'identity-positive.dtb').read_bytes()
        self.assertEqual(blob, make_dtb())
        self.assertEqual(read_identity(blob)['compatible'], ['xiaomi,wayne', 'qcom,sdm660'])
        with patch('import_wayne_board_evidence.shutil.which', return_value=None):
            result = validate(FIX/'dtb-manifest.json')
        self.assertFalse(result['build_gate_authorization'])
        self.assertEqual(result['files'][0]['parsed_fields']['identity_reader'], 'bounded_python_v17')

    def test_actual_binary_identity_rejection(self):
        for name in ('identity-jasmine.dtb', 'identity-model-conflict.dtb'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as folder:
                p = Path(folder); blob = (FIX/name).read_bytes(); (p/'input.dtb').write_bytes(blob)
                manifest = json.loads((FIX/'dtb-manifest.json').read_text())
                manifest['files'][0].update(path='input.dtb', sha256=hashlib.sha256(blob).hexdigest())
                (p/'manifest.json').write_text(json.dumps(manifest))
                with patch('import_wayne_board_evidence.shutil.which', return_value=None):
                    with self.assertRaises(ValueError): validate(p/'manifest.json')

    def test_truncation_and_malformed(self):
        blob = make_dtb()
        for cut in range(len(blob)):
            with self.subTest(cut=cut), self.assertRaises(ValueError): read_identity(blob[:cut])
        vectors = [make_dtb(duplicate=True), (FIX/'identity-malformed.dtb').read_bytes(), (FIX/'identity-truncated.dtb').read_bytes()]
        for offset, value in [(0,0), (8,0xffffffff), (12,56), (16,41), (20,16), (36,0xffffffff), (56,0x55), (68,0xffffffff), (72,1)]:
            bad = bytearray(blob); struct.pack_into('>I',bad,offset,value); vectors.append(bytes(bad))
        bad = bytearray(blob); bad[82] = 65; vectors.append(bytes(bad)) # model NUL
        bad = bytearray(blob); bad[-1] = 65; vectors.append(bytes(bad)) # property-name NUL
        for vector in vectors:
            with self.subTest(vector=vector.hex()[:40]), self.assertRaises(ValueError): read_identity(vector)

    def test_tool_failure_does_not_fallback(self):
        import subprocess
        with patch('import_wayne_board_evidence.shutil.which', return_value='/present/fdtget'), patch('import_wayne_board_evidence.subprocess.run', side_effect=subprocess.CalledProcessError(1, 'fdtget')):
            with self.assertRaises(subprocess.CalledProcessError): validate(FIX/'dtb-manifest.json')

if __name__ == '__main__': unittest.main()
