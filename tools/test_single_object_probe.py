"""Synthetic local Git service/object stores; never actual source or device evidence."""
import hashlib,json,os,subprocess,tempfile,unittest,zlib
from pathlib import Path
from unittest.mock import patch
from single_object_probe import attempt,verify_blob,validate,selection,URL,canonical
from export_dtb_consumers import _write_payload

class ProbeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.server=self.root/'server'
        subprocess.run(['git','init','--bare','-q',str(self.server)],check=True)
        subprocess.run(['git','-C',str(self.server),'config','uploadpack.allowAnySHA1InWant','true'],check=True)
        self.oid=subprocess.check_output(['git','-C',str(self.server),'hash-object','-w','--stdin'],input=b'synthetic blob').decode().strip()
        self.manifest=canonical({'schema_version':'wayne.missing-object-acquisition.v1','items':[{'missing_objects':[{'oid':self.oid,'type':'blob','presence':'missing'}]}]});self.sha=hashlib.sha256(self.manifest).hexdigest()
    def tearDown(self):self.tmp.cleanup()
    def test_local_service_success_and_rejection(self):
        raw=attempt(self.root/'success',str(self.server),self.oid,self.sha,synthetic=True);d=json.loads(raw)
        self.assertEqual(d['result'],'success');self.assertEqual(d['object']['actual_oid'],self.oid);self.assertFalse(d['eligible'])
        fail=json.loads(attempt(self.root/'reject',str(self.server),'0'*40,self.sha,synthetic=True));self.assertEqual(fail['result'],'server_rejected');self.assertIsNone(fail['object'])
    def test_real_local_timeout(self):
        with patch.dict(os.environ,{'GIT_ALLOW_PROTOCOL':'ext'}):raw=attempt(self.root/'timeout','ext::sleep 2',self.oid,self.sha,timeout=.1,synthetic=True)
        self.assertEqual(json.loads(raw)['result'],'timeout');self.assertIsNone(json.loads(raw)['object'])
    def test_type_oid_and_binding_tamper(self):
        tree=subprocess.check_output(['git','-C',str(self.server),'hash-object','-t','tree','-w','--stdin'],input=b'').decode().strip()
        self.assertEqual(verify_blob(self.server,tree)[1],'type_error')
        target=self.server/'objects'/self.oid[:2]/self.oid[2:];target.chmod(0o644);target.write_bytes(zlib.compress(b'blob 5\0other'))
        self.assertEqual(verify_blob(self.server,self.oid)[1],'oid_mismatch')
        with self.assertRaises(ValueError):selection(self.manifest,'0'*64)
    def test_strict_validator_and_output(self):
        # Synthetic refusal shaped as production schema to test rejection only, never published as actual evidence.
        d=json.loads(attempt(self.root/'fail',str(self.server),'0'*40,self.sha,synthetic=True))
        d.update(evidence_scope='actual_remote_probe',source_url=URL,selected_oid=self.oid)
        d['command'][-2:]=[URL,self.oid]
        raw=canonical(d);self.assertEqual(validate(raw,self.manifest,self.sha,self.server),raw)
        for key,value in [('extra',1),('selected_oid','A'*40),('object',{'type':'blob'}),('selection_index',1),('manifest_sha256','0'*64)]:
            bad=dict(d);bad[key]=value
            with self.assertRaises(ValueError):validate(canonical(bad),self.manifest,self.sha,self.server)
        with self.assertRaises(ValueError):validate(b'{"schema_version":"duplicate",'+raw[1:],self.manifest,self.sha,self.server)
        out=self.root/'output.json';out.write_bytes(b'old')
        with self.assertRaises(ValueError):_write_payload(raw,out)
        self.assertEqual(out.read_bytes(),b'old');out.unlink()
        with patch('export_dtb_consumers.os.fsync',side_effect=OSError('IO fail')):
            with self.assertRaises(OSError):_write_payload(raw,out)
        self.assertFalse(out.exists());self.assertEqual(list(self.root.glob('.output.json.*')),[])

if __name__=='__main__':unittest.main()
