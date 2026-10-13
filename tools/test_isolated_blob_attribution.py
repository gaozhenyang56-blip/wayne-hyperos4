"""Actual local witnesses; mutations explicitly synthetic, no network tests."""
import json,tempfile,unittest
from pathlib import Path
from isolated_blob_attribution import audit,validate,canonical
from export_dtb_consumers import _write_payload
class AttributionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.actual=audit()
    def test_local_snapshot_and_determinism(self):
        self.assertEqual(self.actual,audit());d=json.loads(self.actual)
        self.assertEqual(d['network_requests'],0);self.assertEqual(len(d['snapshot_witnesses']),1)
        w=d['snapshot_witnesses'][0]
        self.assertEqual(w['snapshot_commit'],'b633be8ec977605e7d47c2b9a778ad8298a7dd0a')
        self.assertEqual(w['path'],'arch/arm64/boot/dts/qcom/sm8450-sony-xperia-nagara.dtsi')
        self.assertEqual(w['tree_chain'][-1]['entry_oid'],d['selected']['oid'])
        self.assertEqual(d['relationship_status'],'unresolved');self.assertFalse(d['eligible'])
    def test_synthetic_drift_rejected(self):
        for mutate in (lambda d:d.update(extra=1),lambda d:d.update(eligible=True),lambda d:d.update(source_lock_input=True),lambda d:d['selected'].update(main_present=True),lambda d:d['input_sha256'].update(review='0'*64),lambda d:d['snapshot_witnesses'][0].update(snapshot_commit='0'*40),lambda d:d['snapshot_witnesses'][0]['tree_chain'][0].update(entry_oid='0'*40),lambda d:d['snapshot_witnesses'].append(d['snapshot_witnesses'][0]),lambda d:d['examined'].reverse()):
            d=json.loads(self.actual);mutate(d)
            with self.assertRaises(ValueError):validate(canonical(d),self.actual)
        with self.assertRaises(ValueError):validate(b'{"eligible":false,'+self.actual[1:],self.actual)
    def test_atomic_conflict_leaves_no_partial_file(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'evidence.json';_write_payload(self.actual,p);_write_payload(self.actual,p)
            with self.assertRaises(ValueError):_write_payload(b'conflict',p)
            self.assertEqual(p.read_bytes(),self.actual);self.assertEqual(list(Path(folder).iterdir()),[p])
if __name__=='__main__':unittest.main()
