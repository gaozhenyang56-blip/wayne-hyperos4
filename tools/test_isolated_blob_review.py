"""Synthetic facts for offline review serialization only; no Git/network service."""
import json,unittest
from isolated_blob_review import compose,validate,canonical

class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.bindings={k:'a'*64 for k in ('manifest','single','batch1','batch2')}
        self.facts=[{'oid':format(i+1,'040x'),'type':'blob','bytes':i,'content_sha256':'b'*64,'isolation_slot':'single:0' if i==0 else 'batch1:'+str(i-1) if i<5 else 'batch2:'+str(i-5),'bare':True,'isolated_oid_only':True,'main_present':False,'fork_present':False} for i in range(8)]
    def test_stable_unresolved(self):
        raw=compose(self.bindings,self.facts);self.assertEqual(raw,compose(self.bindings,self.facts));self.assertEqual(raw,validate(raw,raw))
        d=json.loads(raw);self.assertFalse(d['eligible']);self.assertTrue(all(o['precise_path'] is None and o['precise_commit'] is None and not o['source_lock_input'] for o in d['objects']))
    def test_pollution_duplicate_and_scope(self):
        for field in ('main_present','fork_present'):
            facts=[dict(o) for o in self.facts];facts[0][field]=True
            with self.assertRaises(ValueError):compose(self.bindings,facts)
        with self.assertRaises(ValueError):compose(self.bindings,list(reversed(self.facts)))
        facts=[dict(o) for o in self.facts];facts[1]['oid']=facts[0]['oid']
        with self.assertRaises(ValueError):compose(self.bindings,facts)
    def test_strict_drift_and_claims(self):
        expected=compose(self.bindings,self.facts)
        for mutation in (lambda d:d.update(extra=1),lambda d:d.update(eligible=True),lambda d:d['input_sha256'].update(single='0'*64),lambda d:d['objects'][0].update(source_lock_input=True),lambda d:d['objects'][0]['verified_facts'].update(content_sha256='0'*64)):
            d=json.loads(expected);mutation(d)
            with self.assertRaises(ValueError):validate(canonical(d),expected)
        with self.assertRaises(ValueError):validate(b'{"schema_version":"duplicate",'+expected[1:],expected)

if __name__=='__main__':unittest.main()
