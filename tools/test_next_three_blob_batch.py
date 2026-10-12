"""Synthetic local Git service incremental chains; never actual fork/device evidence."""
import hashlib,json,subprocess,unittest
from pathlib import Path
import test_four_blob_batch
from single_object_probe import attempt
from four_blob_batch_probe import run as old_run,validate as old_validate
from next_three_blob_probe import run,validate,canonical,CAP
from export_dtb_consumers import _write_payload

class IncrementTests(unittest.TestCase):
    def setUp(self):
        self.h=test_four_blob_batch.BatchTests();self.h.setUp();self.root=self.h.root;self.server=self.h.server
    def tearDown(self):self.h.tearDown()
    def args(self,size=32):
        ids=[]
        for n in range(8):
            payload=(str(n).encode()+b'synthetic-increment'+bytes(size))[:size]
            ids.append(subprocess.check_output(['git','-C',str(self.server),'hash-object','-w','--stdin'],input=payload).decode().strip())
        ids.sort();m=canonical({'schema_version':'wayne.missing-object-acquisition.v1','items':[{'missing_objects':[{'oid':o,'type':'blob','presence':'missing'} for o in ids]}]});ms=hashlib.sha256(m).hexdigest()
        single=attempt(self.root/'single',str(self.server),ids[0],ms,synthetic=True);ss=hashlib.sha256(single).hexdigest()
        previous_root=self.root/'previous';b=old_run(m,ms,single,ss,previous_root,synthetic=True,url=str(self.server));bs=hashlib.sha256(b).hexdigest()
        self.assertEqual(b,old_validate(b,m,ms,single,ss,previous_root,synthetic=True))
        return (m,ms,single,ss,b,bs,previous_root,self.root/'next'),ids
    def test_chain_global_order_counts_and_stability(self):
        args,ids=self.args();raw=run(*args,synthetic=True,url=str(self.server));self.assertEqual(raw,validate(raw,*args,synthetic=True));self.assertEqual(raw,validate(raw,*args,synthetic=True))
        d=json.loads(raw);self.assertEqual(d['global_selection_indices'],[5,6,7]);b=d['batch'];self.assertEqual(b['selected_oids'],ids[5:]);self.assertEqual(b['request_count'],3);self.assertEqual(b['cumulative_verified_payload_bytes'],8*32)
        self.assertEqual(b['payload_limit_bytes'],CAP);self.assertEqual(b['stop_reason'],'completed')
    def test_binding_order_payload_and_output_conflicts(self):
        args,ids=self.args();raw=run(*args,synthetic=True,url=str(self.server))
        bad=list(args);bad[5]='0'*64
        with self.assertRaises(ValueError):validate(raw,*bad,synthetic=True)
        mutations=[lambda d:d['batch']['selected_oids'].__setitem__(0,ids[0]),lambda d:d['global_selection_indices'].reverse(),lambda d:d['batch'].update(cumulative_verified_payload_bytes=999),lambda d:d.update(previous_batch_sha256='0'*64),lambda d:d.update(extra=1)]
        for mutate in mutations:
            d=json.loads(raw);mutate(d)
            with self.assertRaises(ValueError):validate(canonical(d),*args,synthetic=True)
        out=self.root/'output.json';out.write_bytes(b'old')
        with self.assertRaises(ValueError):_write_payload(raw,out)
        self.assertEqual(out.read_bytes(),b'old')
    def test_new_payload_cap_ignores_previous_accumulation(self):
        args,ids=self.args(size=CAP//2);raw=run(*args,synthetic=True,url=str(self.server));b=json.loads(raw)['batch']
        self.assertGreater(b['initial_verified_payload_bytes'],CAP);self.assertEqual(b['request_count'],2);self.assertEqual(b['batch_verified_payload_bytes'],CAP);self.assertEqual(b['items'][2]['result'],'not_attempted');self.assertEqual(b['stop_reason'],'payload_limit')
        self.assertEqual(raw,validate(raw,*args,synthetic=True))
    def test_second_reject_stops_tail(self):
        args,ids=self.args();(self.server/'objects'/ids[6][:2]/ids[6][2:]).unlink();raw=run(*args,synthetic=True,url=str(self.server));b=json.loads(raw)['batch']
        self.assertEqual(b['request_count'],2);self.assertEqual([i['result'] for i in b['items']],['success','server_rejected','not_attempted']);self.assertEqual(raw,validate(raw,*args,synthetic=True))

if __name__=='__main__':unittest.main()
