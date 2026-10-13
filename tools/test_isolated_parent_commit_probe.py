"""Existing real isolated parent plus explicitly synthetic mutations; no network."""
import json,tempfile,unittest
from pathlib import Path
from isolated_parent_commit_probe import audit,validate,canonical,PARENT,CHILD,reason_from_error
from export_dtb_consumers import _write_payload
class ParentProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.raw=audit()
    def test_actual_parent_same_blob_and_determinism(self):
        d=json.loads(self.raw);self.assertEqual(d['request']['result'],'success');self.assertEqual(d['request']['request_count'],1)
        self.assertEqual(d['parent_snapshot']['commit_oid'],PARENT);self.assertEqual(d['parent_snapshot']['type'],'commit')
        self.assertEqual(d['comparison']['child_commit'],CHILD);self.assertTrue(d['comparison']['same_path_object'])
        self.assertEqual(d['parent_snapshot']['path_blob_oid'],d['selected_blob']['oid'])
        self.assertIsNone(d['nearest_local_introduction_boundary']);self.assertIsNone(d['unique_introducing_commit'])
        self.assertEqual(self.raw,audit())
    def test_synthetic_schema_tree_hash_and_claim_drift(self):
        changes=[lambda d:d.update(extra=1),lambda d:d.update(boundary_sha256='0'*64),lambda d:d['parent_snapshot'].update(type='blob'),lambda d:d['parent_snapshot'].update(commit_oid='0'*40),lambda d:d['parent_snapshot']['tree_chain'][0].update(entry_oid='0'*40),lambda d:d['parent_snapshot']['tree_chain'].append(d['parent_snapshot']['tree_chain'][0]),lambda d:d['request'].update(request_count=2),lambda d:d['request'].update(source_url='https://invalid.example'),lambda d:d['selected_blob'].update(main_present=True),lambda d:d['comparison'].update(same_path_object=False)]
        for field in ('history_complete','upstream_membership_verified','carry_strategy_reviewed','eligible','source_lock_input'):
            changes.append(lambda d,field=field:d.update({field:True}))
        for change in changes:
            d=json.loads(self.raw);change(d)
            with self.assertRaises(ValueError):validate(canonical(d),self.raw)
        with self.assertRaises(ValueError):validate(b'{"eligible":false,'+self.raw[1:],self.raw)
    def test_synthetic_error_classification(self):
        for text,result in [(b'CAPTCHA','bot_challenge'),(b'Authentication failed','auth_required'),(b'filtering not recognized','filter_unsupported')]:
            self.assertEqual(reason_from_error(text),result)
    def test_atomic_conflict(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'evidence.json';_write_payload(self.raw,p)
            with self.assertRaises(ValueError):_write_payload(b'synthetic conflict',p)
            self.assertEqual(p.read_bytes(),self.raw);self.assertEqual(list(Path(folder).iterdir()),[p])
if __name__=='__main__':unittest.main()
