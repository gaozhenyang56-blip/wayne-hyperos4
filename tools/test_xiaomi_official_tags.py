"""Actual empty query; explicit synthetic tag/peel fixtures, no network."""
import hashlib,json,tempfile,unittest
from pathlib import Path
from check_xiaomi_official_tags import compose,audit,validate,canonical,URL,CMD
from export_dtb_consumers import _write_payload
class TagTests(unittest.TestCase):
    def run_record(self,data):return canonical({'schema_version':'wayne.xiaomi-official-tag-query.v1','baseline_discovery_sha256':'b'*64,'source_url':URL,'command':CMD,'request_count':1,'hard_timeout_seconds':60,'exit_code':0,'result':'success','stdout_sha256':hashlib.sha256(data).hexdigest(),'stderr_sha256':hashlib.sha256(b'').hexdigest()})
    def test_actual_unresolved_and_stability(self):
        raw=audit();d=json.loads(raw);self.assertEqual(d['advertised_tags'],[]);self.assertIsNone(d['source_entry']);self.assertEqual(d['target_association'],'unresolved');self.assertFalse(d['release_api_queried']);self.assertTrue(d['no_global_absence_claim']);self.assertEqual(raw,audit())
    def test_synthetic_tag_peel_and_rejections(self):
        tag=b'a'*40+b'\trefs/tags/wayne-o-release\n';peeled=b'c'*40+b'\trefs/tags/wayne-o-release^{}\n';data=tag+peeled
        d=json.loads(compose(self.run_record(data),data,b'','b'*64));self.assertEqual(d['source_entry']['immutable_peeled_oid'],'c'*40);self.assertFalse(d['eligible'])
        self.assertIsNone(json.loads(compose(self.run_record(tag),tag,b'','b'*64))['source_entry'])
        for bad in (data+tag,peeled,data[:-1],b'a'*40+b'\trefs/tags/jasmine-release\n'):
            with self.assertRaises(ValueError):compose(self.run_record(bad),bad,b'','b'*64)
        for change in (lambda r:r.update(extra=1),lambda r:r.update(source_url='https://github.com/thirdparty/fork.git'),lambda r:r.update(stdout_sha256='0'*64),lambda r:r.update(baseline_discovery_sha256='0'*64),lambda r:r.update(request_count=2)):
            r=json.loads(self.run_record(data));change(r)
            with self.assertRaises(ValueError):compose(canonical(r),data,b'','b'*64)
        with self.assertRaises(ValueError):compose(b'{"request_count":1,'+self.run_record(data)[1:],data,b'','b'*64)
    def test_synthetic_claim_drift_and_atomic_output(self):
        raw=audit()
        for key in ('history_complete','upstream_membership_verified','carry_strategy_reviewed','eligible','source_lock_input'):
            d=json.loads(raw);d[key]=True
            with self.assertRaises(ValueError):validate(canonical(d),raw)
        d=json.loads(raw);d['source_entry']={'tag':'movable-only'}
        with self.assertRaises(ValueError):validate(canonical(d),raw)
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'discovery.json';_write_payload(raw,p)
            with self.assertRaises(ValueError):_write_payload(b'synthetic conflict',p)
            self.assertEqual(p.read_bytes(),raw);self.assertEqual(list(Path(folder).iterdir()),[p])
if __name__=='__main__':unittest.main()
