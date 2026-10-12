"""Explicit synthetic inventory fixtures, not actual source history."""
import hashlib,json,tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from shallow_review_queue import generate,validate,canonical
from export_dtb_consumers import _write_payload


def fixture():
    records=[]
    for n,subject,paths in [('a','jasmine',None),('b','wayne SDM660 Android',['arch/arm64/boot/dts/qcom/wayne.dts']),('c','Qualcomm Android',['drivers/qcom/generic.c']),('d','jasmine',['arch/jasmine.dts'])]:
        r={'oid':n*40,'parents':[] if n=='a' else [{'oid':'a'*40,'inside_visible_graph':True,'object_available':True}],'author_date':{'unix_seconds':0,'timezone':'+0000'},'subject':subject,'changed_paths':paths,'path_evidence_complete':paths is not None,'shallow_boundary_commit':n=='a','clues':[],'wayne_target_verified':False,'commit_object_sha256':'f'*64}
        records.append({**r,'record_sha256':hashlib.sha256(canonical(r)).hexdigest()})
    return canonical({'schema_version':'wayne.shallow-patch-inventory.v1','current_commit':'d'*40,'shallow_boundaries':['a'*40],'records':records,'clue_rule_version':'literal-subject-path-component-v1','shallow_boundary':True,'history_complete':False,'upstream_membership_verified':False,'carry_strategy_reviewed':False,'eligible':False,'hardware_tested':False})

class QueueTests(unittest.TestCase):
    def setUp(self):self.raw=fixture();self.sha=hashlib.sha256(self.raw).hexdigest()
    def test_multisignal_order_and_determinism(self):
        q=generate(self.raw,self.sha);self.assertEqual(q,generate(self.raw,self.sha));self.assertEqual(q,validate(q,self.raw,self.sha))
        i=next(i for i in json.loads(q)['items'] if i['commit_oid']=='b'*40)
        self.assertEqual(i['classes'],['wayne_explicit','sdm660_explicit','qualcomm_generic','android_generic']);self.assertEqual(i['review_status'],'unreviewed')
    def test_boundary_jasmine_and_generic_isolation(self):
        items=json.loads(generate(self.raw,self.sha))['items']
        boundary=next(i for i in items if i['commit_oid']=='a'*40);self.assertFalse(boundary['paths_known']);self.assertTrue(all(s['source']!='path' for s in boundary['signal_sources']))
        for n in ('a','d'):self.assertEqual(next(i for i in items if i['commit_oid']==n*40)['classes'],['jasmine_only'])
        self.assertEqual(next(i for i in items if i['commit_oid']=='c'*40)['classes'],['qualcomm_generic','android_generic'])
    def test_hash_sources_duplicates_enums_sorting(self):
        q=generate(self.raw,self.sha)
        with self.assertRaises(ValueError):generate(self.raw,'0'*64)
        mutations=[lambda d:d['items'].append(d['items'][0]),lambda d:d['items'].reverse(),lambda d:d['items'][0].update(review_status='reviewed'),lambda d:d['items'][0]['signal_sources'][0].update(text='forged'),lambda d:d.update(extra=1)]
        for mutation in mutations:
            d=json.loads(q);mutation(d)
            with self.assertRaises(ValueError):validate(canonical(d),self.raw,self.sha)
        with self.assertRaises(ValueError):validate(b'{"schema_version":"duplicate",'+q[1:],self.raw,self.sha)
        for kind in ('duplicate','bad_oid','unknown_author'):
            d=json.loads(self.raw)
            if kind=='duplicate':d['records'].append(d['records'][0])
            elif kind=='bad_oid':d['records'][0]['oid']='A'*40
            else:d['records'][0]['author_date']['extra']='bad'
            raw=canonical(d)
            with self.assertRaises(ValueError):generate(raw,hashlib.sha256(raw).hexdigest())
    def test_no_partial_files_or_overwrite(self):
        q=generate(self.raw,self.sha)
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'queue.json';p.write_bytes(b'old')
            with self.assertRaises(ValueError):_write_payload(q,p)
            self.assertEqual(p.read_bytes(),b'old');p.unlink()
            with patch('export_dtb_consumers.os.fsync',side_effect=OSError('IO fail')):
                with self.assertRaises(OSError):_write_payload(q,p)
            self.assertEqual(list(Path(folder).iterdir()),[])

if __name__=='__main__':unittest.main()
