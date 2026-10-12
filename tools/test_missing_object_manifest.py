"""Synthetic git objects with a deliberately removed blob; never real source evidence."""
import hashlib,json,unittest
from pathlib import Path
from unittest.mock import patch
import test_source_update
from shallow_patch_inventory import inventory
from shallow_review_queue import generate as queue
from shallow_patch_fingerprints import generate as fingerprints
from missing_object_manifest import build,validate,canonical
from export_dtb_consumers import _write_payload

class AcquisitionTests(unittest.TestCase):
    def setUp(self):
        self.h=test_source_update.SourceTests();self.h.setUp();self.repo=self.h.repo
        (self.repo/'.git/shallow').write_text(self.h.base+'\n')
        self.inv=inventory(self.repo,self.h.candidate);ish=hashlib.sha256(self.inv).hexdigest();self.q=queue(self.inv,ish);qsh=hashlib.sha256(self.q).hexdigest()
        self.blob=self.h.git('rev-parse',self.h.current+':local-patch').strip();self.path=self.repo/'.git/objects'/self.blob[:2]/self.blob[2:];self.saved=self.path.read_bytes();self.path.unlink()
        second=self.h.git('rev-parse',self.h.candidate+':Makefile').strip()
        (self.repo/'.git/objects'/second[:2]/second[2:]).unlink()
        self.fp=fingerprints(self.inv,self.q,ish,qsh,self.repo);self.hashes={'inventory':ish,'review_queue':qsh,'fingerprints':hashlib.sha256(self.fp).hexdigest()};self.args=(self.repo,self.inv,self.q,self.fp,self.hashes)
    def tearDown(self):self.h.tearDown()
    def test_stable_boundary_and_known_missing(self):
        raw=build(*self.args);self.assertEqual(raw,build(*self.args));self.assertEqual(raw,validate(raw,*self.args));d=json.loads(raw)
        self.assertEqual(d['reason_counts'],{'missing_local_object':2,'shallow_boundary':1})
        boundary=next(i for i in d['items'] if i['acquisition_reason']=='shallow_boundary');self.assertIsNone(boundary['missing_objects']);self.assertIsNone(boundary['minimum_followup_requirement']['depth'])
    def test_present_contradiction_and_hash_drift(self):
        bad=dict(self.hashes);bad['inventory']='0'*64
        with self.assertRaises(ValueError):build(self.repo,self.inv,self.q,self.fp,bad)
        self.path.write_bytes(self.saved)
        with self.assertRaisesRegex(ValueError,'objects exist'):build(*self.args)
    def test_unknown_duplicates_reasons_and_sort(self):
        raw=build(*self.args)
        for mutation in (lambda d:d.update(extra=1),lambda d:d['items'].append(d['items'][0]),lambda d:d['items'].reverse(),lambda d:d['items'][0].update(acquisition_reason='made_up')):
            d=json.loads(raw);mutation(d)
            with self.assertRaises(ValueError):validate(canonical(d),*self.args)
        with self.assertRaises(ValueError):validate(b'{"schema_version":"duplicate",'+raw[1:],*self.args)
    def test_output_conflict_failure_cleanup(self):
        raw=build(*self.args);out=self.repo/'output.json';out.write_bytes(b'old')
        with self.assertRaises(ValueError):_write_payload(raw,out)
        self.assertEqual(out.read_bytes(),b'old');out.unlink()
        with patch('export_dtb_consumers.os.fsync',side_effect=OSError('IO fail')):
            with self.assertRaises(OSError):_write_payload(raw,out)
        self.assertFalse(out.exists());self.assertEqual(list(self.repo.glob('.output.json.*')),[])

if __name__=='__main__':unittest.main()
