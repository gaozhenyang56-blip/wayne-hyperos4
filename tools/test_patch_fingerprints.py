"""Actual synthetic git objects, no real hardware or upstream qualification."""
import hashlib,json,unittest
from pathlib import Path
from unittest.mock import patch
import test_source_update
from shallow_patch_inventory import inventory
from shallow_review_queue import generate as queue
from shallow_patch_fingerprints import fingerprint,generate,validate,canonical
from export_dtb_consumers import _write_payload

class FingerprintTests(unittest.TestCase):
    def setUp(self):
        self.h=test_source_update.SourceTests();self.h.setUp();self.repo=self.h.repo
        (self.repo/'.git/shallow').write_text(self.h.base+'\n')
    def tearDown(self):self.h.tearDown()
    def args(self,tip=None):
        raw=inventory(self.repo,tip or self.h.candidate);sha=hashlib.sha256(raw).hexdigest();q=queue(raw,sha)
        return raw,q,sha,hashlib.sha256(q).hexdigest(),self.repo
    def test_content_metadata_and_stability(self):
        original=fingerprint(self.repo,self.h.current,self.h.base)[0]
        self.h.git('checkout','-q',self.h.current);self.h.git('commit','--amend','--no-edit','--author','Other <other@example.invalid>')
        equivalent=self.h.git('rev-parse','HEAD').strip();same=fingerprint(self.repo,equivalent,self.h.base)[0]
        self.assertEqual(original['patch_id'],same['patch_id']);self.assertEqual(original['diff_sha256'],same['diff_sha256'])
        (self.repo/'local-patch').write_text('changed content');self.h.git('add','.');self.h.git('commit','--amend','-qm','changed')
        different=fingerprint(self.repo,self.h.git('rev-parse','HEAD').strip(),self.h.base)[0];self.assertNotEqual(original['patch_id'],different['patch_id'])
        args=self.args();raw=generate(*args);self.assertEqual(raw,generate(*args));self.assertEqual(raw,validate(raw,*args))
    def test_boundary_root_merge_and_missing(self):
        args=self.args();report=json.loads(generate(*args));self.assertEqual(report['null_reason_counts']['shallow_boundary'],1)
        self.h.git('checkout','-qb','branch',self.h.base);(self.repo/'branch').write_text('synthetic');self.h.git('add','.');self.h.git('commit','-qm','branch')
        self.h.git('checkout','-q',self.h.candidate);self.h.git('merge','--no-ff','-qm','merge','branch');tip=self.h.git('rev-parse','HEAD').strip()
        report=json.loads(generate(*self.args(tip)));self.assertEqual(report['null_reason_counts']['merge_commit'],1)
        self.h.git('checkout','--orphan','synthetic-root');self.h.git('commit','-qm','root')
        root_oid=self.h.git('rev-parse','HEAD').strip();root_report=json.loads(generate(*self.args(root_oid)))
        self.assertEqual(root_report['null_reason_counts']['zero_parents'],1)
        obj=self.repo/'.git/objects'/self.h.current[:2]/self.h.current[2:];obj.unlink()
        self.assertEqual(fingerprint(self.repo,self.h.current,self.h.base)[1],'objects_unavailable')
    def test_binding_report_tampering(self):
        args=self.args();raw=generate(*args)
        bad=list(args);bad[3]='0'*64
        with self.assertRaises(ValueError):generate(*bad)
        for key,value in [('patch_id','A'*40),('null_reason','merge_commit'),('diff_sha256','0'*64),('extra',1)]:
            data=json.loads(raw);data['items'][-1][key]=value
            with self.assertRaises(ValueError):validate(canonical(data),*args)
    def test_output_conflict_and_cleanup(self):
        raw=generate(*self.args());out=self.repo/'fingerprints.json';out.write_bytes(b'old')
        with self.assertRaises(ValueError):_write_payload(raw,out)
        self.assertEqual(out.read_bytes(),b'old');out.unlink()
        with patch('export_dtb_consumers.os.fsync',side_effect=OSError('IO fail')):
            with self.assertRaises(OSError):_write_payload(raw,out)
        self.assertFalse(out.exists());self.assertEqual(list(self.repo.glob('.fingerprints.json.*')),[])

if __name__=='__main__':unittest.main()
