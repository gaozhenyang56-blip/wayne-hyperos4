"""Synthetic git histories only; no hardware/source qualification."""
import hashlib,json
from pathlib import Path
import tempfile
import unittest
from test_source_update import SourceTests
from history_probe import probe,validate_fetch,URL

class HistoryTests(SourceTests):
    # Reuse fixture creation, not inherited test cases.
    def test_graph_ancestor_divergence_stability(self):
        a=probe(self.repo,self.current,self.candidate);self.assertEqual(a,probe(self.repo,self.current,self.candidate))
        self.assertTrue(json.loads(a)['relationship']['current_ancestor_candidate'])
        self.git('checkout','-q',self.base);(self.repo/'branch').write_text('synthetic');self.git('add','.');self.git('commit','-qm','branch');other=self.git('rev-parse','HEAD').strip()
        self.assertFalse(json.loads(probe(self.repo,self.current,other))['relationship']['current_ancestor_candidate'])
    def test_shallow_missing(self):
        (self.repo/'.git/shallow').write_text(self.current+'\n');self.assertIsNone(json.loads(probe(self.repo,self.current,self.candidate))['relationship']);(self.repo/'.git/shallow').unlink()
        self.assertIsNone(json.loads(probe(self.repo,self.current,'0'*40))['relationship'])
    def test_hash_and_url_drift(self):
        p=self.repo/'.git/objects/synthetic';p.write_bytes(b'not a git object; hash-check fixture only')
        command=['git','-c','gc.auto=0','-c','pack.threads=1','-C','<isolated-bare-fork>','fetch','--no-tags','--no-recurse-submodules','--filter=blob:none','--depth=64','origin',self.current]
        d={'schema_version':'wayne.history-fetch.v1','source_url':URL,'command':command,'exit_code':1,'depth':64,'byte_limit':16*1024*1024,'object_bytes':p.stat().st_size,'files':[{'path':'objects/synthetic','bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}],'ref':{'command':['git','rev-parse','FETCH_HEAD^{commit}'],'exit_code':1,'stdout':'','stdout_sha256':hashlib.sha256(b'').hexdigest()},'shallow':[],'blocked_reason':'synthetic','relationship_status':'undetermined','update_status':'blocked'}
        validate_fetch(json.dumps(d).encode(),self.repo/'.git',URL,self.current)
        with self.assertRaises(ValueError):validate_fetch(json.dumps(d).encode(),self.repo/'.git','https://drift.invalid',self.current)
        d['files'][0]['sha256']='0'*64
        with self.assertRaises(ValueError):validate_fetch(json.dumps(d).encode(),self.repo/'.git',URL,self.current)
# Remove inherited tests from this subclass; fixture helpers remain.
for name in ('test_fast_forward_local_patch_and_stability','test_divergence','test_shallow_missing_and_tampered_hash','test_strict_json'):setattr(HistoryTests,name,None)
if __name__=='__main__':unittest.main()
