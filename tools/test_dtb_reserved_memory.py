"""Synthetic binary vectors only; no real wayne memory layout."""
from dataclasses import FrozenInstanceError
import struct
import unittest
from test_dtb_phandle import binary,node,FIX
from dtb_reserved_memory import decode_reserved_memory


def fixture(ac=1,sc=1,parent=None,first=None,second=None):
    def cell(v):return struct.pack('>I',v)
    def reg(values):return b''.join(a.to_bytes(ac*4,'big')+s.to_bytes(sc*4,'big') for a,s in values)
    parent=[('#address-cells',cell(ac)),('#size-cells',cell(sc)),('ranges',b'')] if parent is None else parent
    first=[('phandle',cell(1)),('reg',reg([(7,0),(9,3)])),('no-map',b'')] if first is None else first
    second=[('linux,phandle',cell(2)),('reg',reg([((1<<64)-1,0)] if ac==2 else [(11,2)])),('reusable',b'')] if second is None else second
    return binary(node('consumer',[('memory-region',cell(1)+cell(2))])+[('begin','reserved-memory')]+[('prop',p) for p in parent]+node('a',first)+node('b',second)+[('end',None)])

class ReservedTests(unittest.TestCase):
    def test_one_cell_multi_targets_flags_and_zero_size(self):
        blob=(FIX/'reserved-positive-11.dtb').read_bytes();self.assertEqual(blob,fixture())
        result=decode_reserved_memory(blob,'/consumer');self.assertEqual(len(result),2)
        self.assertEqual(result[0].reg,((7,0),(9,3)));self.assertTrue(result[0].no_map)
        self.assertTrue(result[1].reusable);self.assertEqual(result[1].reg,((11,2),))
        for target in result:
            for pair,offsets in zip(target.reg,target.reg_offsets):
                self.assertEqual(int.from_bytes(blob[offsets[0]:offsets[0]+4],'big'),pair[0])
                self.assertEqual(int.from_bytes(blob[offsets[1]:offsets[1]+4],'big'),pair[1])
        with self.assertRaises(FrozenInstanceError):result[0].no_map=False

    def test_two_cells_unsigned_max_and_order(self):
        blob=(FIX/'reserved-positive-22.dtb').read_bytes();self.assertEqual(blob,fixture(2,2))
        result=decode_reserved_memory(blob,'/consumer')
        self.assertEqual(result[0].reg,((7,0),(9,3)));self.assertEqual(result[1].reg,(((1<<64)-1,0),))
        self.assertEqual(result[0].reg_offsets[0][1]-result[0].reg_offsets[0][0],8)

    def test_cell_counts_and_ranges(self):
        valid=[('#address-cells',struct.pack('>I',1)),('#size-cells',struct.pack('>I',1)),('ranges',b'')]
        for name in ('#address-cells','#size-cells'):
            for payload in (None,b'',b'\x01',struct.pack('>II',1,1),struct.pack('>I',0),struct.pack('>I',3),struct.pack('>I',0xffffffff)):
                props=[p for p in valid if p[0]!=name]+([] if payload is None else [(name,payload)])
                with self.subTest(name=name,payload=payload),self.assertRaises(ValueError):decode_reserved_memory(fixture(parent=props),'/consumer')
        for props in (valid[:-1],valid[:-1]+[('ranges',b'\0'*4)]):
            with self.assertRaises(ValueError):decode_reserved_memory(fixture(parent=props),'/consumer')

    def test_bad_reg_boolean_and_no_partial_results(self):
        for payload in (None,b'',b'\1',b'\1'*7,b'\1'*9):
            props=[('linux,phandle',struct.pack('>I',2))]+([] if payload is None else [('reg',payload)])
            result='no result'
            with self.subTest(payload=payload),self.assertRaises(ValueError):result=decode_reserved_memory(fixture(second=props),'/consumer')
            self.assertEqual(result,'no result')
        with self.assertRaises(ValueError):decode_reserved_memory(fixture(2,2,second=[('phandle',struct.pack('>I',2)),('reg',bytes(8))]),'/consumer')
        base=[('phandle',struct.pack('>I',1)),('reg',struct.pack('>II',0,1))]
        for flags in ([('no-map',b'1')],[('reusable',b'1')],[('no-map',b''),('reusable',b'')]):
            with self.assertRaises(ValueError):decode_reserved_memory(fixture(first=base+flags),'/consumer')

    def test_targets_outside_direct_layer_and_missing_parent(self):
        consumer=node('consumer',[('memory-region',struct.pack('>I',1))])
        leaf=node('target',[('phandle',struct.pack('>I',1)),('reg',struct.pack('>II',0,1))])
        parent=[('begin','reserved-memory'),('prop',('#address-cells',struct.pack('>I',1))),('prop',('#size-cells',struct.pack('>I',1))),('prop',('ranges',b''))]
        for blob in (binary(consumer+leaf), binary(consumer+parent+[('end',None)]+leaf), binary(consumer+parent+[('begin','nested')]+leaf+[('end',None),('end',None)])):
            with self.assertRaises(ValueError):decode_reserved_memory(blob,'/consumer')

    def test_inherited_phandle_conflict_and_truncation(self):
        props=[('phandle',struct.pack('>I',1)),('linux,phandle',struct.pack('>I',2)),('reg',struct.pack('>II',0,1))]
        with self.assertRaisesRegex(ValueError,'conflicting phandle'):decode_reserved_memory(fixture(first=props),'/consumer')
        blob=fixture()
        for cut in range(len(blob)):
            with self.subTest(cut=cut),self.assertRaises(ValueError):decode_reserved_memory(blob[:cut],'/consumer')

if __name__=='__main__':unittest.main()
