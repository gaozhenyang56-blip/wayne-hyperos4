"""Actual local snapshot witnesses; report mutation fixtures are synthetic."""
import json,tempfile,unittest
from pathlib import Path
from isolated_blob_triage import audit,validate,canonical
from export_dtb_consumers import _write_payload
class TriageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.raw=audit()
    def test_real_paths_rank_and_no_target_upgrade(self):
        d=json.loads(self.raw);self.assertEqual(len(d['items']),8)
        self.assertEqual(d['classification_counts'],{'target_relevance_supported':0,'other_soc_or_device_path':5,'insufficient_target_evidence':3})
        self.assertTrue(all(i['snapshot_path_witnesses'] and not i['target_relevance_supported'] for i in d['items']))
        selected=d['selected_next_target'];self.assertEqual(selected['oid'],'0509c0e69da28fa0693258ddc6bf249e349ba3da')
        self.assertEqual(selected['blocked_reason'],'actual_wayne_board_evidence_missing');self.assertFalse(selected['executed_this_stage'])
        self.assertEqual(d['priority_oids'][-1],d['items'][0]['verified_facts']['oid'])
        pm=next(i for i in d['items'] if i['verified_facts']['oid']==selected['oid'])
        self.assertEqual(pm['classification'],'insufficient_target_evidence')
        self.assertTrue(all(e['evidence_scope']=='unverified_jasmine_inherited_experiment_only' for e in pm['dependency_evidence']))
        self.assertFalse(d['fourth_layer_requested']);self.assertEqual(d['network_requests'],0)
        self.assertEqual(self.raw,audit())
    def test_synthetic_chain_and_claim_drift_rejected(self):
        mutations=[lambda d:d.update(extra=1),lambda d:d['input_sha256'].update(third_parent='0'*64),lambda d:d['items'].append(d['items'][0]),lambda d:d['items'][0]['verified_facts'].update(type='tree'),lambda d:d['items'][0]['verified_facts'].update(main_present=True),lambda d:d['items'][0]['snapshot_path_witnesses'][0]['tree_chain'][0].update(entry_oid='0'*40),lambda d:d['priority_oids'].reverse(),lambda d:d['items'][3].update(target_relevance_supported=True),lambda d:d.update(fourth_layer_requested=True),lambda d:d['selected_next_target'].update(executed_this_stage=True)]
        for k in ('history_complete','upstream_membership_verified','carry_strategy_reviewed','eligible','source_lock_input'):
            mutations.append(lambda d,k=k:d.update({k:True}))
        for mutation in mutations:
            d=json.loads(self.raw);mutation(d)
            with self.assertRaises(ValueError):validate(canonical(d),self.raw)
        with self.assertRaises(ValueError):validate(b'{"eligible":false,'+self.raw[1:],self.raw)
    def test_atomic_conflict_no_partial_file(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'triage.json';_write_payload(self.raw,p)
            with self.assertRaises(ValueError):_write_payload(b'synthetic conflict',p)
            self.assertEqual(p.read_bytes(),self.raw);self.assertEqual(list(Path(folder).iterdir()),[p])
if __name__=='__main__':unittest.main()
