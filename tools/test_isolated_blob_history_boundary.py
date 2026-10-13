"""Real local history checks; report mutations are synthetic, never device evidence."""
import json,tempfile,unittest
from pathlib import Path
from isolated_blob_history_boundary import audit,validate,canonical
from export_dtb_consumers import _write_payload
class BoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.expected=audit()
    def test_actual_bounded_parent_chain(self):
        d=json.loads(self.expected);self.assertEqual(d['stop_reason'],'shallow_boundary')
        self.assertEqual(len(d['snapshots']),13);self.assertEqual(len(d['parent_tree_differences']),12)
        self.assertFalse(d['snapshots'][0]['selected_blob_present'])
        self.assertTrue(all(s['selected_blob_present'] for s in d['snapshots'][1:]))
        self.assertEqual(d['nearest_proven_ancestral_snapshot']['commit_oid'],'71c631a9fb211df4ea5a59ac68a310c5854f07f1')
        self.assertFalse(d['parent_tree_differences'][0]['same_path_object'])
        self.assertTrue(all(e['same_path_object'] for e in d['parent_tree_differences'][1:]))
        self.assertIsNone(d['unique_introducing_commit']);self.assertIsNone(d['introduction_candidates'])
        self.assertEqual(d['network_requests'],0);self.assertEqual(self.expected,audit())
    def test_synthetic_mutations_rejected(self):
        mutations=[lambda d:d.update(extra=1),lambda d:d['input_sha256'].update(attribution='0'*64),lambda d:d['selected'].update(main_present=True),lambda d:d['snapshots'].append(d['snapshots'][0]),lambda d:d['snapshots'].reverse(),lambda d:d['snapshots'][1].update(commit_oid='0'*40),lambda d:d['snapshots'][1]['tree_chain'][0].update(entry_oid='0'*40),lambda d:d['parent_tree_differences'][0].update(same_path_object=True),lambda d:d.update(unique_introducing_commit=d['snapshots'][-1]['commit_oid'])]
        for k in ('history_complete','upstream_membership_verified','carry_strategy_reviewed','eligible','source_lock_input'):
            mutations.append(lambda d,k=k:d.update({k:True}))
        for mutate in mutations:
            d=json.loads(self.expected);mutate(d)
            with self.assertRaises(ValueError):validate(canonical(d),self.expected)
        with self.assertRaises(ValueError):validate(b'{"eligible":false,'+self.expected[1:],self.expected)
    def test_atomic_output_conflict(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'boundary.json';_write_payload(self.expected,p)
            with self.assertRaises(ValueError):_write_payload(b'synthetic conflicting output',p)
            self.assertEqual(p.read_bytes(),self.expected);self.assertEqual(list(Path(folder).iterdir()),[p])
if __name__=='__main__':unittest.main()
