"""Synthetic small git histories; not SDM660 source evidence."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import test_source_update
from shallow_patch_inventory import inventory,validate,canonical
from export_dtb_consumers import _write_payload

class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.helper=test_source_update.SourceTests();self.helper.setUp();self.repo=self.helper.repo;self.current=self.helper.candidate
        (self.repo/'.git/shallow').write_text(self.helper.base+'\n')
    def tearDown(self):self.helper.tearDown()
    def test_stability_shallow_missing_parent(self):
        raw=inventory(self.repo,self.current);self.assertEqual(raw,inventory(self.repo,self.current));self.assertEqual(raw,validate(raw,self.repo,self.current))
        self.assertFalse(json.loads(raw)['eligible'])
        (self.repo/'.git/shallow').write_text(self.helper.current+'\n')
        record=next(r for r in json.loads(inventory(self.repo,self.current))['records'] if r['oid']==self.helper.current)
        self.assertIsNone(record['changed_paths']);self.assertFalse(record['path_evidence_complete'])
        obj=self.repo/'.git/objects'/self.helper.base[:2]/self.helper.base[2:];obj.unlink()
        record=next(r for r in json.loads(inventory(self.repo,self.current))['records'] if r['oid']==self.helper.current)
        self.assertFalse(record['parents'][0]['object_available'])
    def test_branch_and_jasmine_only(self):
        h=self.helper;h.git('checkout','-qb','synthetic-branch',h.base);(self.repo/'jasmine.dts').write_text('synthetic');h.git('add','.');h.git('commit','-qm','jasmine only');branch=h.git('rev-parse','HEAD').strip()
        h.git('checkout','-q',self.current);h.git('merge','--no-ff','-qm','synthetic merge',branch)
        current=h.git('rev-parse','HEAD').strip();records=json.loads(inventory(self.repo,current))['records'];record=next(r for r in records if r['oid']==branch)
        self.assertIn('jasmine_reference',record['clues']);self.assertNotIn('wayne',record['clues']);self.assertFalse(record['wayne_target_verified'])
        self.assertEqual(len(next(r for r in records if r['oid']==current)['parents']),2)
    def test_tamper_unknown_duplicate_and_parent(self):
        raw=inventory(self.repo,self.current);d=json.loads(raw)
        for key,value in [('changed_paths',['../escape']),('record_sha256','0'*64),('oid','A'*40),('parents',[])]:
            bad=json.loads(raw);target=next(record for record in bad['records'] if record['parents']);target[key]=value
            with self.assertRaises(ValueError):validate(canonical(bad),self.repo,self.current)
        d['records'].append(d['records'][0])
        with self.assertRaises(ValueError):validate(canonical(d),self.repo,self.current)
        with self.assertRaises(ValueError):validate(b'{"extra":0,'+raw[1:],self.repo,self.current)
        with self.assertRaises(ValueError):validate(b'{"schema_version":"duplicate",'+raw[1:],self.repo,self.current)
    def test_output_failure_no_partial(self):
        raw=inventory(self.repo,self.current);out=self.repo/'output.json';out.write_bytes(b'preserved')
        with self.assertRaises(ValueError):_write_payload(raw,out)
        self.assertEqual(out.read_bytes(),b'preserved');out.unlink()
        with patch('export_dtb_consumers.os.fsync',side_effect=OSError('IO failure')):
            with self.assertRaises(OSError):_write_payload(raw,out)
        self.assertFalse(out.exists());self.assertEqual(list(self.repo.glob('.output.json.*')),[])

if __name__=='__main__':unittest.main()
