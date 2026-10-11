"""Actual synthetic DTB bytes; no mock parser output or device binding claims."""
import hashlib
from pathlib import Path
import struct
import unittest
from dtb_phandle_index import build_phandle_index
from test_dtb_tree import pack_tree, root

FIX=Path(__file__).resolve().parents[1]/'tests/fixtures/wayne-evidence'

def node(name, props):
    return [('begin', name)]+[('prop', (key, value)) for key, value in props]+[('end', None)]

def binary(nodes): return pack_tree(root()+nodes+[('end',None)])

def positive():
    return binary(node('consumer',[('opaque-cell',struct.pack('>I',0x01020304))])+node('later-target',[('phandle',struct.pack('>I',0x01020304))])+node('legacy',[('linux,phandle',struct.pack('>I',2))])+node('dual',[('phandle',struct.pack('>I',3)),('linux,phandle',struct.pack('>I',3))]))

class PhandleTests(unittest.TestCase):
    def test_positive_aliases_and_forward_lookup(self):
        blob=(FIX/'phandle-positive.dtb').read_bytes();self.assertEqual(blob,positive())
        index=build_phandle_index(blob)
        self.assertEqual(dict(index.targets),{0x01020304:'/later-target',2:'/legacy',3:'/dual'})
        self.assertEqual(index.resolve(0x01020304),'/later-target')
        self.assertEqual(index.source_sha256,hashlib.sha256(blob).hexdigest())
        with self.assertRaises(TypeError):index.targets[4]='/fake'

    def test_reserved_and_bad_lengths(self):
        for name in ('phandle','linux,phandle'):
            for payload in (b'',b'\x01',b'\x00\x00\x01',b'\x01'*5,b'\x01'*8,struct.pack('>I',0),struct.pack('>I',0xffffffff)):
                with self.subTest(name=name,payload=payload),self.assertRaises(ValueError):build_phandle_index(binary(node('x',[(name,payload)])))

    def test_conflicts_and_duplicates(self):
        with self.assertRaises(ValueError):build_phandle_index((FIX/'phandle-conflict.dtb').read_bytes())
        with self.assertRaises(ValueError):build_phandle_index(binary(node('x',[('phandle',struct.pack('>I',1))])+node('y',[('linux,phandle',struct.pack('>I',1))])))

    def test_endianness_and_queries(self):
        index=build_phandle_index(positive())
        with self.assertRaises(ValueError):index.resolve(0x04030201)
        little=binary(node('x',[('phandle',struct.pack('<I',0x01020304))]))
        self.assertEqual(build_phandle_index(little).resolve(0x04030201),'/x') # DTB bytes are ALWAYS big-endian; intent cannot be inferred.
        for query in (0,0xffffffff,-1,2**32,True,'2',2.0,99):
            with self.subTest(query=query),self.assertRaises(ValueError):index.resolve(query)

    def test_truncation_and_empty_index(self):
        blob=positive()
        for cut in range(len(blob)):
            with self.subTest(cut=cut),self.assertRaises(ValueError):build_phandle_index(blob[:cut])
        index=build_phandle_index(binary([]));self.assertEqual(dict(index.targets),{})
        with self.assertRaises(ValueError):index.resolve(1)

if __name__=='__main__':unittest.main()
