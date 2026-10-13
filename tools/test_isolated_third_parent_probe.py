"""Real third isolated parent; synthetic report mutations only, no network tests."""
import json,tempfile,unittest
from pathlib import Path
from isolated_third_parent_probe import audit,validate,canonical
from export_dtb_consumers import _write_payload
class ThirdParentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.raw=audit()
    def test_actual_direct_parent_deterministic(self):
        d=json.loads(self.raw);e=d['request_engine_evidence']
        self.assertEqual(d['derived_parent_oid'],'9a6ed4ea985ac4b7a566faddeb16271b8ea54d36')
        self.assertEqual(e['parent_snapshot']['type'],'commit');self.assertEqual(e['parent_snapshot']['commit_oid'],d['derived_parent_oid'])
        self.assertEqual(e['comparison']['child_commit'],'50ae1c470491481328363639c227020691469f29')
        self.assertTrue(e['comparison']['same_path_object']);self.assertEqual(e['request']['request_count'],1)
        self.assertIsNone(e['nearest_local_introduction_boundary']);self.assertIsNone(d['unique_introducing_commit'])
        self.assertFalse(d['information_gain_review']['continued_layer_requests_recommended']);self.assertFalse(d['information_gain_review']['fourth_layer_authorized'])
        self.assertEqual(self.raw,audit())
    def test_synthetic_mutations_rejected(self):
        changes=[lambda d:d.update(extra=1),lambda d:d.update(previous_evidence_sha256='0'*64),lambda d:d.update(derived_parent_oid='0'*40),lambda d:d['request_engine_evidence']['parent_snapshot'].update(type='blob'),lambda d:d['request_engine_evidence']['parent_snapshot']['tree_chain'][0].update(entry_oid='0'*40),lambda d:d['request_engine_evidence']['parent_snapshot']['tree_chain'].append(d['request_engine_evidence']['parent_snapshot']['tree_chain'][0]),lambda d:d['request_engine_evidence']['comparison'].update(same_path_object=False),lambda d:d['request_engine_evidence']['selected_blob'].update(main_present=True),lambda d:d['information_gain_review'].update(fourth_layer_authorized=True)]
        for k in ('history_complete','upstream_membership_verified','carry_strategy_reviewed','eligible','source_lock_input'):
            changes.extend([lambda d,k=k:d.update({k:True}),lambda d,k=k:d['request_engine_evidence'].update({k:True})])
        for change in changes:
            d=json.loads(self.raw);change(d)
            with self.assertRaises(ValueError):validate(canonical(d),self.raw)
        with self.assertRaises(ValueError):validate(b'{"eligible":false,'+self.raw[1:],self.raw)
    def test_atomic_conflict_no_partial(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'evidence.json';_write_payload(self.raw,p)
            with self.assertRaises(ValueError):_write_payload(b'synthetic conflict',p)
            self.assertEqual(p.read_bytes(),self.raw);self.assertEqual(list(Path(folder).iterdir()),[p])
if __name__=='__main__':unittest.main()
