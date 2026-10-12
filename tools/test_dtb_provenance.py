"""All input fixtures synthetic/not device evidence; no parser mocks."""
import hashlib,json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from bind_dtb_provenance import envelope,bind,SCHEMA
from export_dtb_consumers import canonical_bytes
from test_dtb_consumer_evidence import fixture,FIX


def inputs():
    dtb=fixture();export=canonical_bytes(dtb);container=b'SYNTHETIC'+dtb+b'END'
    h=lambda b:hashlib.sha256(b).hexdigest()
    m={'schema_version':SCHEMA,'evidence_role':'synthetic_not_device_evidence','capture_type':'synthetic_fixture','device':'wayne','soc':'sdm660','collected_at':'2026-10-11T18:50:00-07:00','capture_command':'synthetic fixture construction; NOT device acquisition','capture_tool_version':'test-dtb-provenance/1','container_name':'synthetic-container.bin (not a device partition)','container_sha256':h(container),'dtb_offset':9,'dtb_length':len(dtb),'dtb_sha256':h(dtb),'consumer_export_sha256':h(export)}
    return m,dtb,export,container

def encode(m):return json.dumps(m,ensure_ascii=False).encode()

class ProvenanceTests(unittest.TestCase):
    def test_full_and_claim_only_deterministic(self):
        m,d,e,c=inputs();raw=(FIX/'provenance-synthetic.json').read_bytes();self.assertEqual(json.loads(raw),m)
        a=envelope(raw,d,e,c);self.assertEqual(a,envelope(raw,d,e,c));r=json.loads(a)
        self.assertEqual(r['validation_state'],'container_slice_verified')
        for k in ('physical_source_authenticated','build_gate_authorization','hardware_tested'):self.assertFalse(r[k])
        self.assertEqual(json.loads(envelope(raw,d,e))['validation_state'],'manifest_claim_validated')

    def test_hashes_ranges_and_container(self):
        m,d,e,c=inputs()
        for key,value in [('dtb_sha256','0'*64),('consumer_export_sha256','0'*64),('container_sha256','0'*64),('dtb_offset',len(c)),('dtb_offset',2**63-1),('dtb_length',0),('dtb_length',2**63),('dtb_offset',-1),('dtb_length',True)]:
            bad=dict(m);bad[key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):envelope(encode(bad),d,e,c)
        with self.assertRaises(ValueError):envelope(encode(m),d,e,c[:-4])
        bad=dict(m);bad['consumer_export_sha256']=hashlib.sha256(e+b' ').hexdigest()
        with self.assertRaises(ValueError):envelope(encode(bad),d,e+b' ',c)

    def test_strict_fields_identity_time_json(self):
        m,d,e,c=inputs()
        for key,value in [('extra','x'),('device','jasmine'),('soc','other'),('collected_at','2026-10-11T18:50:00'),('container_name','unknown'),('dtb_sha256',m['dtb_sha256'].upper()),('capture_command','')]:
            bad=dict(m);bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):envelope(encode(bad),d,e,c)
        raw=encode(m)
        for bad in (b'{"device":"wayne",'+raw[1:],raw.replace(b'"dtb_offset": 9',b'"dtb_offset": NaN'),raw.replace(b'"dtb_offset": 9',b'"dtb_offset": Infinity')):
            with self.assertRaises(ValueError):envelope(bad,d,e,c)

    def test_output_mismatch_and_failure_cleanup(self):
        m,d,e,c=inputs()
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);out=p/'evidence.json';out.write_bytes(b'original')
            with self.assertRaises(ValueError):bind(encode(m),d,e,c,out)
            self.assertEqual(out.read_bytes(),b'original');out.unlink()
            bad=dict(m);bad['dtb_sha256']='0'*64
            with self.assertRaises(ValueError):bind(encode(bad),d,e,c,out)
            self.assertEqual(list(p.iterdir()),[])
            with patch('export_dtb_consumers.os.fsync',side_effect=OSError('injected IO failure')):
                with self.assertRaises(OSError):bind(encode(m),d,e,c,out)
            self.assertEqual(list(p.iterdir()),[])
            payload=bind(encode(m),d,e,c,out);self.assertEqual(payload,out.read_bytes())

if __name__=='__main__':unittest.main()
