"""Synthetic binary structure tests; no real device bindings or mock parser outputs."""
from pathlib import Path
import struct
import unittest
from read_dtb_identity import read_tree, read_identity, MAX_NODES, MAX_PROPERTIES, MAX_DEPTH, MAX_PROPERTY_SIZE, MAX_SIZE

def pack_tree(nodes):
    strings=bytearray(); offsets={}; stream=bytearray()
    def word(*v): stream.extend(struct.pack('>'+'I'*len(v),*v))
    def raw(v): stream.extend(v);stream.extend(b'\0'*(-len(stream)%4))
    for kind, data in nodes:
        if kind=='begin': word(1);raw(data.encode()+b'\0')
        elif kind=='end':word(2)
        elif kind=='prop':
            name,value=data
            if name not in offsets:offsets[name]=len(strings);strings.extend(name.encode()+b'\0')
            word(3,len(value),offsets[name]);raw(value)
        else:word(kind)
    word(9)
    if not strings: strings.extend(b'\0')
    header=struct.pack('>10I',0xd00dfeed,56+len(stream)+len(strings),56,56+len(stream),40,17,16,0,len(strings),len(stream))
    return header+b'\0'*16+stream+strings

def root(): return [('begin',''),('prop',('model',b'MI 6X\0')),('prop',('compatible',b'xiaomi,wayne\0qcom,sdm660\0'))]

def nested(): return pack_tree(root()+[('begin','bus'),('prop',('raw-data',b'\x00\x01\xff')),('begin','leaf@0'),('prop',('empty',b'')),('end',None),('end',None),('end',None)])

class TreeTests(unittest.TestCase):
    def test_nested_snapshot_offsets(self):
        blob=nested();tree=read_tree(blob)
        self.assertEqual(blob,(Path(__file__).resolve().parents[1]/'tests/fixtures/wayne-evidence/tree-nested.dtb').read_bytes())
        self.assertEqual(set(tree['nodes']),{'/','/bus','/bus/leaf@0'})
        for node in tree['nodes'].values():
            for prop in node['properties'].values():self.assertEqual(blob[prop['value_offset']:prop['value_offset']+prop['length']].hex(),prop['hex'])
        self.assertEqual(read_identity(blob)['model'],'MI 6X')
        self.assertFalse(tree['build_gate_authorization']);self.assertIsNone(tree['reference_edges'])

    def test_bad_paths_properties_tokens(self):
        vectors=[root()+[('begin',n),('end',None),('end',None)] for n in ('.','..','a/b','bad name','')]
        vectors += [root()+[('begin','x'),('end',None),('begin','x'),('end',None),('end',None)],root()+[('prop',('model',b'conflict\0')),('end',None)],root()+[('prop',('bad/name',b'')),('end',None)],root()+[(0x55,None),('end',None)]]
        for v in vectors:
            with self.subTest(v=v),self.assertRaises(ValueError):read_tree(pack_tree(v))

    def test_truncation_nul_and_immutability(self):
        blob=nested()
        for cut in range(len(blob)):
            with self.subTest(cut=cut),self.assertRaises(ValueError):read_tree(blob[:cut])
        bad=bytearray(pack_tree([('begin',''),('end',None)]));bad[60:struct.unpack_from('>I',bad,12)[0]]=b'A'*(struct.unpack_from('>I',bad,12)[0]-60) # no NUL anywhere in node-name remainder
        with self.assertRaises(ValueError):read_tree(bytes(bad))
        bad=bytearray(blob);bad[-1]=65
        with self.assertRaises(ValueError):read_tree(bytes(bad))
        with self.assertRaises(ValueError):read_tree(bytearray(blob))

    def test_real_limits(self):
        # Generated binary vectors, actual production limits; no limit mocks.
        accepted=root()+[('begin','d'+str(i)) for i in range(MAX_DEPTH-1)]+[('end',None)]*MAX_DEPTH
        read_tree(pack_tree(accepted))
        read_tree(pack_tree([('begin','')]+[event for i in range(MAX_NODES-1) for event in [('begin','n'+str(i)),('end',None)]]+[('end',None)]))
        read_tree(pack_tree([('begin','')]+[('prop',('p'+str(i),b'')) for i in range(MAX_PROPERTIES)]+[('end',None)]))
        read_tree(pack_tree(root()+[('prop',('large',bytes(MAX_PROPERTY_SIZE))),('end',None)]))
        for vector in (root()+[('begin','d'+str(i)) for i in range(MAX_DEPTH)]+[('end',None)]*(MAX_DEPTH+1), root()+[event for i in range(MAX_NODES) for event in [('begin','n'+str(i)),('end',None)]]+[('end',None)], [('begin','')]+[('prop',('p'+str(i),b'')) for i in range(MAX_PROPERTIES+1)]+[('end',None)],root()+[('prop',('large',bytes(MAX_PROPERTY_SIZE+1))),('end',None)]):
            with self.assertRaises(ValueError):read_tree(pack_tree(vector))
        with self.assertRaises(ValueError):read_tree(bytes(MAX_SIZE+1))

if __name__=='__main__':unittest.main()
