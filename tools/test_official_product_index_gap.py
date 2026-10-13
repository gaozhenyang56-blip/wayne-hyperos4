"""Actual scoped records; synthetic mutations, no network or endpoint guesses."""
import json,tempfile,unittest
from pathlib import Path
from check_official_product_index_gap import audit,validate,canonical
from export_dtb_consumers import _write_payload
class IndexGapTests(unittest.TestCase):
    def test_actual_no_request_is_not_negative_response(self):
        raw=audit();d=json.loads(raw);self.assertEqual(d['network_requests'],0);self.assertIsNone(d['index_entry']);self.assertFalse(d['negative_index_query_result'])
        for k in ('response_count','pagination','truncated','device_matches'):self.assertIsNone(d[k])
        self.assertEqual([c['kind'] for c in d['covered_metadata_boundaries']],['heads','tags','releases_page']);self.assertEqual(raw,audit())
    def test_synthetic_endpoint_and_claim_drift(self):
        raw=audit()
        for change in (lambda d:d.update(extra=1),lambda d:d.update(index_entry={'url':'https://api.github.com/repos/MiCode/Xiaomi_Kernel_OpenSource/readme'}),lambda d:d.update(network_requests=1),lambda d:d.update(negative_index_query_result=True),lambda d:d.update(response_count=0),lambda d:d['offline_scope'][0].update(sha256='0'*64)):
            d=json.loads(raw);change(d)
            with self.assertRaises(ValueError):validate(canonical(d),raw)
        for k in ('history_complete','upstream_membership_verified','carry_strategy_reviewed','eligible','source_lock_input'):
            d=json.loads(raw);d[k]=True
            with self.assertRaises(ValueError):validate(canonical(d),raw)
        with self.assertRaises(ValueError):validate(b'{"eligible":false,'+raw[1:],raw)
    def test_atomic_conflict(self):
        raw=audit()
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'gap.json';_write_payload(raw,p)
            with self.assertRaises(ValueError):_write_payload(b'synthetic conflict',p)
            self.assertEqual(p.read_bytes(),raw);self.assertEqual(list(Path(folder).iterdir()),[p])
if __name__=='__main__':unittest.main()
