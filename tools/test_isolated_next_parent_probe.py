"""Real single-parent evidence; explicitly synthetic mutations, no network tests."""
import json,tempfile,unittest
from pathlib import Path
import isolated_parent_commit_probe as old
from isolated_next_parent_probe import audit,validate,canonical
from export_dtb_consumers import _write_payload
class NextParentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.raw=audit()
    def test_actual_parent_and_stability(self):
        d=json.loads(self.raw);e=d['request_engine_evidence'];p=e['parent_snapshot']
        self.assertEqual(d['derived_parent_oid'],'50ae1c470491481328363639c227020691469f29')
        self.assertEqual(p['commit_oid'],d['derived_parent_oid']);self.assertEqual(p['type'],'commit')
        self.assertEqual(e['comparison']['child_commit'],'6fbaeffc3a92b4a32b8e320e486cf644ff30d240')
        self.assertTrue(e['comparison']['same_path_object']);self.assertEqual(e['request']['request_count'],1)
        self.assertIsNone(e['nearest_local_introduction_boundary']);self.assertIsNone(d['unique_introducing_commit'])
        self.assertEqual(old.PARENT,'6fbaeffc3a92b4a32b8e320e486cf644ff30d240')
        self.assertEqual(self.raw,audit())
    def test_synthetic_drift_refused(self):
        changes=[lambda d:d.update(extra=1),lambda d:d.update(previous_evidence_sha256='0'*64),lambda d:d.update(derived_parent_oid='0'*40),lambda d:d['request_engine_evidence']['parent_snapshot'].update(type='blob'),lambda d:d['request_engine_evidence']['parent_snapshot']['tree_chain'][0].update(entry_oid='0'*40),lambda d:d['request_engine_evidence']['parent_snapshot']['tree_chain'].append(d['request_engine_evidence']['parent_snapshot']['tree_chain'][0]),lambda d:d['request_engine_evidence']['comparison'].update(same_path_object=False),lambda d:d['request_engine_evidence']['selected_blob'].update(main_present=True)]
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
