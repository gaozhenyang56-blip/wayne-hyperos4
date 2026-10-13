"""Selected real PM660/reference only; mutations explicitly synthetic, no network."""
import json,tempfile,unittest
from pathlib import Path
from check_pm660_wayne_association import audit,validate,canonical,OID
from export_dtb_consumers import _write_payload
class AssociationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.raw=audit()
    def test_selected_only_and_reference_not_baseline(self):
        d=json.loads(self.raw);self.assertEqual(d['selected_candidate_blob']['oid'],OID)
        self.assertEqual(d['selected_candidate_blob']['type'],'blob');self.assertEqual(d['selected_candidate_blob']['bytes'],5410)
        self.assertEqual(d['recorded_board_reference']['includes'][0]['included_relative_path'],'sdm660-xiaomi-jasmine.dts')
        self.assertFalse(d['recorded_board_reference']['commit_tree_membership_verified']);self.assertFalse(d['recorded_board_reference']['physical_source_authenticated'])
        self.assertEqual(d['target_association'],'unresolved');self.assertEqual(d['include_chain']['status'],'not_closed')
        self.assertEqual(d['source_request_decision']['network_requests'],0);self.assertFalse(d['other_blobs_processed']);self.assertFalse(d['first_blob_history_resumed'])
        self.assertEqual(self.raw,audit())
    def test_synthetic_schema_oid_chain_and_claim_drift(self):
        changes=[lambda d:d.update(extra=1),lambda d:d['input_sha256'].update(triage='0'*64),lambda d:d['selected_candidate_blob'].update(oid='0'*40),lambda d:d['selected_candidate_blob'].update(type='tree'),lambda d:d['selected_candidate_blob']['snapshot_path_witnesses'][0]['tree_chain'][0].update(entry_oid='0'*40),lambda d:d['selected_candidate_blob']['snapshot_path_witnesses'].append(d['selected_candidate_blob']['snapshot_path_witnesses'][0]),lambda d:d['recorded_board_reference'].update(physical_source_authenticated=True),lambda d:d.update(target_association='verified'),lambda d:d['include_chain'].update(status='closed')]
        for k in ('history_complete','upstream_membership_verified','carry_strategy_reviewed','eligible','source_lock_input'):
            changes.append(lambda d,k=k:d.update({k:True}))
        for change in changes:
            d=json.loads(self.raw);change(d)
            with self.assertRaises(ValueError):validate(canonical(d),self.raw)
        with self.assertRaises(ValueError):validate(b'{"eligible":false,'+self.raw[1:],self.raw)
    def test_atomic_conflict_no_partial(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'association.json';_write_payload(self.raw,p)
            with self.assertRaises(ValueError):_write_payload(b'synthetic conflict',p)
            self.assertEqual(p.read_bytes(),self.raw);self.assertEqual(list(Path(folder).iterdir()),[p])
if __name__=='__main__':unittest.main()
