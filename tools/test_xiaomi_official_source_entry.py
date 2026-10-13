"""Actual empty advertisement plus explicitly synthetic refs, never source evidence."""
import hashlib,json,tempfile,unittest
from pathlib import Path
from check_xiaomi_official_source_entry import audit,compose,validate,canonical,CMD,URL
from export_dtb_consumers import _write_payload
class SourceTests(unittest.TestCase):
    def synthetic(self,stdout=b'',url=URL):
        run={'schema_version':'wayne.xiaomi-official-query-run.v1','command':CMD,'source_url':url,'request_count':1,'hard_timeout_seconds':60,'exit_code':0,'result':'success','stdout_sha256':hashlib.sha256(stdout).hexdigest(),'stderr_sha256':hashlib.sha256(b'').hexdigest()}
        return canonical(run)
    def test_actual_empty_response_stable(self):
        raw=audit();d=json.loads(raw);self.assertIsNone(d['source_entry']);self.assertEqual(d['discovery_status'],'unresolved');self.assertTrue(d['no_global_absence_claim']);self.assertEqual(raw,audit())
    def test_synthetic_fixed_oid_and_strict_policy(self):
        data=b'a'*40+b'\trefs/heads/wayne-o-oss\n';run=self.synthetic(data);d=json.loads(compose(run,data,b'','b'*64))
        self.assertEqual(d['source_entry']['immutable_oid'],'a'*40);self.assertFalse(d['eligible'])
        for response in (data+data,b'not-an-oid\trefs/heads/wayne-o-oss\n',data.rstrip(b'\n'),b'a'*40+b'\trefs/heads/jasmine-o-oss\n'):
            with self.assertRaises(ValueError):compose(self.synthetic(response),response,b'','b'*64)
        for mutation in (lambda r:r.update(extra=1),lambda r:r.update(source_url='https://github.com/thirdparty/fork.git'),lambda r:r.update(stdout_sha256='0'*64),lambda r:r.update(request_count=2)):
            r=json.loads(run);mutation(r)
            with self.assertRaises(ValueError):compose(canonical(r),data,b'','b'*64)
        with self.assertRaises(ValueError):compose(b'{"request_count":1,'+run[1:],data,b'','b'*64)
        two=data+b'c'*40+b'\trefs/heads/wayne-other\n';self.assertIsNone(json.loads(compose(self.synthetic(two),two,b'','b'*64))['source_entry'])
    def test_synthetic_output_claim_drift_and_atomic_conflict(self):
        raw=audit()
        for key in ('history_complete','upstream_membership_verified','carry_strategy_reviewed','eligible','source_lock_input'):
            d=json.loads(raw);d[key]=True
            with self.assertRaises(ValueError):validate(canonical(d),raw)
        d=json.loads(raw);d['source_entry']={'ref_at_query':'refs/heads/wayne-o-oss'}
        with self.assertRaises(ValueError):validate(canonical(d),raw)
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'discovery.json';_write_payload(raw,p)
            with self.assertRaises(ValueError):_write_payload(b'synthetic conflict',p)
            self.assertEqual(p.read_bytes(),raw);self.assertEqual(list(Path(folder).iterdir()),[p])
if __name__=='__main__':unittest.main()
