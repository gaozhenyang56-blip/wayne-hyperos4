"""Actual synthetic binary fixtures; no hardware semantics or parser mocks."""
from dataclasses import FrozenInstanceError
import struct
import unittest
from dtb_consumer_evidence import collect_consumer_evidence
from read_dtb_identity import MAX_NODES,MAX_REFERENCE_EDGES
from test_dtb_phandle import binary,node,FIX


def fixture(consumers=None, reg=None):
    cell=lambda v:struct.pack('>I',v)
    consumers=[node('first',[('memory-region',cell(2)+cell(1)+cell(2)),('compatible',b'example,one\0example,two\0'),('status',b'disabled\0'),('firmware-name',b'synthetic-a\0synthetic-b\0')]),node('second',[('memory-region',cell(1))])] if consumers is None else consumers
    reserved=[('begin','reserved-memory'),('prop',('#address-cells',cell(1))),('prop',('#size-cells',cell(1))),('prop',('ranges',b''))]+node('a',[('phandle',cell(1)),('reg',struct.pack('>II',7,0) if reg is None else reg),('no-map',b'')])+node('b',[('phandle',cell(2)),('reg',struct.pack('>II',11,3)),('reusable',b'')])+[('end',None)]
    return binary([event for events in consumers for event in events]+reserved)

class ConsumerTests(unittest.TestCase):
    def test_multiple_order_raw_and_immutable(self):
        blob=(FIX/'consumer-positive.dtb').read_bytes();self.assertEqual(blob,fixture())
        records=collect_consumer_evidence(blob);self.assertEqual([r.source_path for r in records],['/first','/second'])
        self.assertEqual([t.edge.phandle for t in records[0].targets],[2,1,2])
        self.assertEqual(records[0].optional_properties[0].strings,('example,one','example,two'))
        self.assertEqual(records[0].optional_properties[1].strings,('disabled',))
        self.assertEqual(records[0].optional_properties[2].strings,('synthetic-a','synthetic-b'))
        for r in records:
            self.assertEqual(blob[r.memory_region_value_offset:r.memory_region_value_offset+len(r.memory_region_raw)],r.memory_region_raw)
        with self.assertRaises(FrozenInstanceError):records[0].source_path='/fake'
        with self.assertRaises(FrozenInstanceError):records[0].optional_properties[0].presence='absent'

    def test_single_absent_and_empty_enumeration(self):
        records=collect_consumer_evidence(fixture([node('one',[('memory-region',struct.pack('>I',1))])]))
        self.assertEqual(len(records),1)
        for p in records[0].optional_properties:self.assertEqual((p.presence,p.raw,p.strings),('absent',None,()))
        self.assertEqual(collect_consumer_evidence(fixture([])),())

    def test_bad_optional_all_or_nothing(self):
        for name in ('compatible','status','firmware-name'):
            values=[b'',b'nonterminated',b'\0',b'a\0\0',b'\0a\0']+([b'a\0b\0'] if name=='status' else [])
            for payload in values:
                result='none'
                consumers=[node('valid',[('memory-region',struct.pack('>I',1))]),node('bad',[('memory-region',struct.pack('>I',2)),(name,payload)])]
                with self.subTest(name=name,payload=payload),self.assertRaises(ValueError):result=collect_consumer_evidence(fixture(consumers))
                self.assertEqual(result,'none')

    def test_dangling_and_invalid_reserved(self):
        with self.assertRaises(ValueError):collect_consumer_evidence(fixture([node('bad',[('memory-region',struct.pack('>I',99))])]))
        with self.assertRaises(ValueError):collect_consumer_evidence(fixture(reg=b'bad'))

    def test_actual_aggregate_limits(self):
        cell=struct.pack('>I',1)
        consumers=[node('a',[('memory-region',cell*(MAX_REFERENCE_EDGES//2))]),node('b',[('memory-region',cell*(MAX_REFERENCE_EDGES//2))])]
        self.assertEqual(sum(len(r.targets) for r in collect_consumer_evidence(fixture(consumers))),MAX_REFERENCE_EDGES)
        consumers[1]=node('b',[('memory-region',cell*(MAX_REFERENCE_EDGES//2+1))])
        with self.assertRaisesRegex(ValueError,'aggregate'):collect_consumer_evidence(fixture(consumers))
        maximal=collect_consumer_evidence(fixture([node('n'+str(i),[('memory-region',cell)]) for i in range(MAX_NODES-4)]))
        self.assertEqual(len(maximal),MAX_NODES-4)
        # 65536 consumers cannot fit the inherited 16384-node bound; test the actual tighter structural ceiling.
        with self.assertRaises(ValueError):collect_consumer_evidence(fixture([node('n'+str(i),[('memory-region',cell)]) for i in range(MAX_NODES)]))

if __name__=='__main__':unittest.main()
