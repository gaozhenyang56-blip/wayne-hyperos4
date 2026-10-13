"""Actual one-page response; synthetic HTTP/release fixtures, no network tests."""
import hashlib,json,tempfile,unittest
from pathlib import Path
from check_xiaomi_official_releases import audit,compose,validate,canonical,URL,CMD
from export_dtb_consumers import _write_payload
class ReleaseTests(unittest.TestCase):
    def fixture(self,body,link=False,status=200):
        headers=('HTTP/2 '+str(status)+'\r\nContent-Type: application/json\r\nContent-Length: '+str(len(body))+('\r\nLink: <https://api.github.com/repos/MiCode/Xiaomi_Kernel_OpenSource/releases?page=2>; rel="next"' if link else '')+'\r\n\r\n').encode()
        run={'schema_version':'wayne.official-release-request.v1','baseline_tags_sha256':'b'*64,'url':URL,'request_count':1,'page':1,'per_page':20,'hard_timeout_seconds':60,'max_response_bytes':1048576,'redirects_followed':False,'curl_exit_code':0,'http_status':status,'body_sha256':hashlib.sha256(body).hexdigest(),'headers_sha256':hashlib.sha256(headers).hexdigest(),'stderr_sha256':hashlib.sha256(b'').hexdigest(),'command':CMD}
        return canonical(run),headers
    def test_actual_page_complete_empty_and_stable(self):
        raw=audit();d=json.loads(raw);r=d['response_scope'];self.assertEqual(r['returned_releases'],0);self.assertTrue(r['transfer_complete']);self.assertFalse(r['has_pagination_link']);self.assertFalse(r['attachments_downloaded']);self.assertIsNone(d['source_entry']);self.assertEqual(d['device_candidates'],[]);self.assertEqual(raw,audit())
    def test_synthetic_pagination_candidate_and_stop_states(self):
        obj={'id':42,'url':'https://api.github.com/repos/MiCode/Xiaomi_Kernel_OpenSource/releases/42','html_url':'https://github.com/MiCode/Xiaomi_Kernel_OpenSource/releases/tag/wayne-test','tag_name':'wayne-test','target_commitish':'main','name':'MI 6X','body':'小米6X synthetic fixture'}
        body=canonical([obj]);run,h=self.fixture(body,True);d=json.loads(compose(run,body,h,b'','b'*64));self.assertTrue(d['response_scope']['has_pagination_link']);self.assertIsNone(d['device_candidates'][0]['declared_commit_oid']);self.assertIsNone(d['source_entry']);self.assertFalse(d['eligible'])
        obj['target_commitish']='a'*40;body=canonical([obj]);run,h=self.fixture(body);d=json.loads(compose(run,body,h,b'','b'*64));self.assertFalse(d['device_candidates'][0]['oid_membership_verified'])
        body=b'{"message":"rate limit"}';run,h=self.fixture(body,status=429);self.assertEqual(json.loads(compose(run,body,h,b'','b'*64))['reason'],'auth_refusal_or_rate_limit_stop')
        r=json.loads(run);r['url']='https://api.github.com/repos/thirdparty/fork/releases'
        with self.assertRaises(ValueError):compose(canonical(r),body,h,b'','b'*64)
    def test_synthetic_schema_hash_claim_drift_and_atomic(self):
        body=b'[]';run,h=self.fixture(body)
        for change in (lambda r:r.update(extra=1),lambda r:r.update(body_sha256='0'*64),lambda r:r.update(page=2),lambda r:r.update(baseline_tags_sha256='0'*64)):
            r=json.loads(run);change(r)
            with self.assertRaises(ValueError):compose(canonical(r),body,h,b'','b'*64)
        with self.assertRaises(ValueError):compose(b'{"page":1,'+run[1:],body,h,b'','b'*64)
        raw=audit()
        for k in ('history_complete','upstream_membership_verified','carry_strategy_reviewed','eligible','source_lock_input'):
            d=json.loads(raw);d[k]=True
            with self.assertRaises(ValueError):validate(canonical(d),raw)
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'discovery.json';_write_payload(raw,p)
            with self.assertRaises(ValueError):_write_payload(b'synthetic conflict',p)
            self.assertEqual(p.read_bytes(),raw);self.assertEqual(list(Path(folder).iterdir()),[p])
if __name__=='__main__':unittest.main()
