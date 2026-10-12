"""Synthetic local Git services only; never real fork/device evidence."""
import hashlib,json,os,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from four_blob_batch_probe import run,validate,canonical,CAP
from single_object_probe import attempt,verify_blob
from export_dtb_consumers import _write_payload

class BatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.server=self.root/'server';subprocess.run(['git','init','--bare','-q',str(self.server)],check=True)
        subprocess.run(['git','-C',str(self.server),'config','uploadpack.allowAnySHA1InWant','true'],check=True)
    def tearDown(self):self.tmp.cleanup()
    def inputs(self,size=32):
        ids=[]
        for n in range(5):
            content=(str(n).encode()+b'synthetic'+bytes(size))[:size]
            ids.append(subprocess.check_output(['git','-C',str(self.server),'hash-object','-w','--stdin'],input=content).decode().strip())
        ids.sort();m=canonical({'schema_version':'wayne.missing-object-acquisition.v1','items':[{'missing_objects':[{'oid':oid,'type':'blob','presence':'missing'} for oid in ids]}]});ms=hashlib.sha256(m).hexdigest()
        p=attempt(self.root/'prior',str(self.server),ids[0],ms,synthetic=True);ps=hashlib.sha256(p).hexdigest();return m,ms,p,ps,ids
    def test_all_success_deterministic_and_tamper(self):
        m,ms,p,ps,ids=self.inputs();lab=self.root/'batch';raw=run(m,ms,p,ps,lab,synthetic=True,url=str(self.server));self.assertEqual(raw,validate(raw,m,ms,p,ps,lab,synthetic=True))
        d=json.loads(raw);self.assertEqual(d['request_count'],4);self.assertEqual(d['selected_oids'],ids[1:]);self.assertEqual(d['stop_reason'],'completed')
        self.assertEqual(raw,canonical(json.loads(raw)))
        for mutation in (lambda x:x['items'].reverse(),lambda x:x.update(extra=1),lambda x:x.update(batch_verified_payload_bytes=999),lambda x:x['items'][0]['object'].update(type='tree'),lambda x:x['items'][0]['probe'].update(object=None),lambda x:x['items'][0].update(oid=ids[2])):
            bad=json.loads(raw);mutation(bad)
            with self.assertRaises(ValueError):validate(canonical(bad),m,ms,p,ps,lab,synthetic=True)
        with self.assertRaises(ValueError):validate(raw,m,'0'*64,p,ps,lab,synthetic=True)
        out=self.root/'out.json';out.write_bytes(b'old')
        with self.assertRaises(ValueError):_write_payload(raw,out)
        self.assertEqual(out.read_bytes(),b'old');out.unlink()
        with patch('export_dtb_consumers.os.fsync',side_effect=OSError('IO fail')):
            with self.assertRaises(OSError):_write_payload(raw,out)
        self.assertFalse(out.exists());self.assertEqual(list(self.root.glob('.out.json.*')),[])
    def test_second_failure_stops_tail(self):
        m,ms,p,ps,ids=self.inputs();(self.server/'objects'/ids[2][:2]/ids[2][2:]).unlink()
        lab=self.root/'batch';raw=run(m,ms,p,ps,lab,synthetic=True,url=str(self.server));d=json.loads(raw)
        self.assertEqual(d['request_count'],2);self.assertEqual([i['result'] for i in d['items']],['success','server_rejected','not_attempted','not_attempted'])
        self.assertEqual(raw,validate(raw,m,ms,p,ps,lab,synthetic=True))
    def test_local_timeout_stops_all(self):
        m,ms,p,ps,ids=self.inputs();lab=self.root/'batch'
        with patch.dict(os.environ,{'GIT_ALLOW_PROTOCOL':'ext'}):raw=run(m,ms,p,ps,lab,synthetic=True,url='ext::sleep 2',timeout=.1)
        d=json.loads(raw);self.assertEqual(d['request_count'],1);self.assertEqual(d['items'][0]['result'],'timeout');self.assertTrue(all(i['result']=='not_attempted' for i in d['items'][1:]))
        self.assertEqual(raw,validate(raw,m,ms,p,ps,lab,synthetic=True))
    def test_real_payload_cap_after_first(self):
        m,ms,p,ps,ids=self.inputs(size=CAP//2);lab=self.root/'batch';raw=run(m,ms,p,ps,lab,synthetic=True,url=str(self.server));d=json.loads(raw)
        self.assertEqual(d['request_count'],1);self.assertEqual(d['cumulative_verified_payload_bytes'],CAP);self.assertEqual(d['stop_reason'],'payload_limit')
        self.assertEqual(raw,validate(raw,m,ms,p,ps,lab,synthetic=True))
        tree=subprocess.check_output(['git','-C',str(self.server),'hash-object','-t','tree','-w','--stdin'],input=b'').decode().strip();self.assertEqual(verify_blob(self.server,tree)[1],'type_error')

if __name__=='__main__':unittest.main()
