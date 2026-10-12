"""Tiny actual git histories; explicitly synthetic, never real SDM660 evidence."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from check_source_update import assess,parse,SCHEMA

class SourceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.repo=Path(self.temp.name)
        self.git('init','-q');self.git('config','user.name','Synthetic');self.git('config','user.email','fixture@example.invalid')
        self.url='https://example.invalid/synthetic.git';self.git('remote','add','origin',self.url)
        (self.repo/'Makefile').write_text('VERSION = 6\nPATCHLEVEL = 6\nSUBLEVEL = 9\n');self.git('add','.');self.git('commit','-qm','base');self.base=self.git('rev-parse','HEAD').strip()
        (self.repo/'local-patch').write_text('synthetic patch');self.git('add','.');self.git('commit','-qm','local');self.current=self.git('rev-parse','HEAD').strip()
        (self.repo/'Makefile').write_text('VERSION = 6\nPATCHLEVEL = 6\nSUBLEVEL = 10\n');self.git('add','.');self.git('commit','-qm','candidate');self.candidate=self.git('rev-parse','HEAD').strip()
        self.lock={'repository':self.url,'commit':self.current}
        self.req={'schema_version':SCHEMA,'current_url':self.url,'candidate_url':self.url,'current_commit':self.current,'candidate_commit':self.candidate,'upstream_base_commit':self.base,'patch_policy':'preserve_current_ancestry','evidence_sha256':{}}
    def tearDown(self):self.temp.cleanup()
    def git(self,*args):return subprocess.check_output(['git','-C',str(self.repo),*args],stderr=subprocess.DEVNULL,text=True)
    def result(self):return assess(json.dumps(self.req).encode(),self.repo,self.lock)
    def test_fast_forward_local_patch_and_stability(self):
        first=self.result();self.assertEqual(first,self.result());r=json.loads(first)
        self.assertTrue(r['relationship']['current_ancestor_candidate']);self.assertEqual(r['relationship']['current_only'],0)
        self.assertIn(self.current,r['relationship']['commits_after_declared_upstream_base']);self.assertEqual(r['status'],'blocked')
        self.req['evidence_sha256']={e['name']:e['sha256'] for e in r['evidence']};self.assertEqual(json.loads(self.result())['status'],'blocked')
    def test_divergence(self):
        self.git('checkout','-q',self.base);(self.repo/'other').write_text('fork');self.git('add','.');self.git('commit','-qm','fork');self.req['candidate_commit']=self.git('rev-parse','HEAD').strip()
        self.assertFalse(json.loads(self.result())['relationship']['current_ancestor_candidate'])
    def test_shallow_missing_and_tampered_hash(self):
        self.req['candidate_commit']='0'*40;self.assertIsNone(json.loads(self.result())['relationship'])
        self.req['candidate_commit']=self.candidate;(self.repo/'.git/shallow').write_text(self.current+'\n');self.assertIn('shallow',str(json.loads(self.result())['gaps']));(self.repo/'.git/shallow').unlink()
        self.req['evidence_sha256']={'current_makefile':'0'*64};self.assertIn('hash mismatch',str(json.loads(self.result())['gaps']))
    def test_strict_json(self):
        raw=json.dumps(self.req).encode()
        for bad in (b'{"extra":1,'+raw[1:],b'{"schema_version":"duplicate",'+raw[1:],raw.replace(b'"patch_policy": "preserve_current_ancestry"',b'"patch_policy": NaN')):
            with self.assertRaises(ValueError):parse(bad,self.lock)
        for key,value in [('current_commit','A'*40),('candidate_url','https://drift.invalid'),('candidate_commit','short')]:
            bad=dict(self.req);bad[key]=value
            with self.assertRaises(ValueError):parse(json.dumps(bad).encode(),self.lock)

if __name__=='__main__':unittest.main()
