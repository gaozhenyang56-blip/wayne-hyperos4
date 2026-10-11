"""Synthetic actual binary vectors; no parser mocks or wayne layout claims."""
from dataclasses import FrozenInstanceError
from pathlib import Path
import struct
import unittest
from dtb_memory_region import decode_memory_region
from read_dtb_identity import MAX_REFERENCE_EDGES
from test_dtb_phandle import binary,node,FIX


def fixture(values=(2,1,2), payload=None):
    payload = b''.join(struct.pack('>I',v) for v in values) if payload is None else payload
    return binary(node('consumer',[('memory-region',payload)])+node('later-a',[('phandle',struct.pack('>I',1))])+node('later-b',[('linux,phandle',struct.pack('>I',2))]))

class MemoryRegionTests(unittest.TestCase):
    def test_single(self):
        edges=decode_memory_region(fixture((1,)),'/consumer')
        self.assertEqual(len(edges),1);self.assertEqual(edges[0].target_path,'/later-a')

    def test_multiple_forward_duplicates_offsets_and_frozen(self):
        blob=(FIX/'memory-region-positive.dtb').read_bytes();self.assertEqual(blob,fixture())
        edges=decode_memory_region(blob,'/consumer')
        self.assertIsInstance(edges,tuple)
        self.assertEqual([e.phandle for e in edges],[2,1,2])
        self.assertEqual([e.target_path for e in edges],['/later-b','/later-a','/later-b'])
        for i,e in enumerate(edges):
            self.assertEqual(e.cell_index,i);self.assertEqual(e.source_path,'/consumer');self.assertEqual(e.property_name,'memory-region')
            self.assertEqual(struct.unpack_from('>I',blob,e.value_offset)[0],e.phandle)
        with self.assertRaises(FrozenInstanceError):edges[0].phandle=9

    def test_invalid_cells_and_all_or_nothing(self):
        for values in ((0,),(0xffffffff,),(1,99)):
            result='not returned'
            with self.subTest(values=values),self.assertRaises(ValueError):result=decode_memory_region(fixture(values),'/consumer')
            self.assertEqual(result,'not returned')
        with self.assertRaises(ValueError):decode_memory_region((FIX/'memory-region-dangling.dtb').read_bytes(),'/consumer')

    def test_bad_lengths(self):
        for payload in (b'',b'\x01',b'\x01'*3,b'\x01'*5):
            with self.subTest(length=len(payload)),self.assertRaises(ValueError):decode_memory_region(fixture(payload=payload),'/consumer')

    def test_missing_source_property_and_unsupported(self):
        for path in ('/absent','/consumer/',None):
            with self.subTest(path=path),self.assertRaises(ValueError):decode_memory_region(fixture(),path)
        with self.assertRaises(ValueError):decode_memory_region(fixture(),'/later-a')
        for name in ('clocks','resets','interrupts-extended','gpios','iommus','phandle','unknown'):
            with self.subTest(name=name),self.assertRaises(ValueError):decode_memory_region(fixture(),'/consumer',name)

    def test_edge_limit_actual_binary(self):
        edges=decode_memory_region(fixture(payload=struct.pack('>I',1)*MAX_REFERENCE_EDGES),'/consumer')
        self.assertEqual(len(edges),MAX_REFERENCE_EDGES)
        with self.assertRaises(ValueError):decode_memory_region(fixture(payload=struct.pack('>I',1)*(MAX_REFERENCE_EDGES+1)),'/consumer')

    def test_inherited_conflict(self):
        for declarations in ([('phandle',struct.pack('>I',1)),('linux,phandle',struct.pack('>I',2))],[('phandle',struct.pack('>I',2))]):
            bad=binary(node('consumer',[('memory-region',struct.pack('>I',1))])+node('a',[('phandle',struct.pack('>I',1))])+node('b',declarations))
            if len(declarations)==1: # duplicate a rather than unique value
                bad=binary(node('consumer',[('memory-region',struct.pack('>I',1))])+node('a',[('phandle',struct.pack('>I',2))])+node('b',declarations))
            with self.assertRaisesRegex(ValueError,'conflicting phandle aliases|duplicate phandle across nodes'):decode_memory_region(bad,'/consumer')

    def test_truncated(self):
        blob=fixture()
        for cut in range(len(blob)):
            with self.subTest(cut=cut),self.assertRaises(ValueError):decode_memory_region(blob[:cut],'/consumer')

if __name__=='__main__':unittest.main()
