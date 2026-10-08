#!/usr/bin/env python3
"""Exercise meaningful packaging rejection and multi-part ZIP integrity gates."""
import copy
import hashlib
import io
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
import zipfile
from package_static_candidate import check_reports,NAME

class PackagingChecks(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.temp.name)
        self.folder=self.root/'research/static-wayne';self.folder.mkdir(parents=True)
        self.reports={n:{'success':True} for n in ('image-check.json','boot-check.json','system-content-check.json','system-metadata-check.json','vendor-content-check.json','vendor-metadata-check.json')}
        self.reports['image-check.json']['system_full_recheck_performed']=True
        self.reports['vintf-check.json']={'check':{'exit_code':0}}
        self.reports['native-versions.json']={'results':[{'target':t,'inspected_libraries':1,'missing_dependency_files':[],'unresolved_required_symbols_in_selected_scope':[]} for t in ('lib/hw/camera.sdm660.so','lib/hw/android.hardware.camera.provider@2.4-impl.so','bin/hw/android.hardware.camera.provider@2.4-service','bin/hw/android.hardware.graphics.composer@2.1-service')]}
    def tearDown(self):self.temp.cleanup()
    def save(self,reports):
        for n,r in reports.items():(self.folder/n).write_text(json.dumps(r))
    def test_report_gates(self):
        self.save(self.reports);self.assertEqual(len(check_reports(self.root)),8)
        for key in ('system_full_recheck_performed','success'):
            broken=copy.deepcopy(self.reports);broken['image-check.json'][key]=False;self.save(broken)
            with self.assertRaises(ValueError):check_reports(self.root)
        broken=copy.deepcopy(self.reports);broken['vendor-content-check.json']['success']=False;self.save(broken)
        with self.assertRaises(ValueError):check_reports(self.root)
        for kind in ('missing','duplicate','unresolved'):
            broken=copy.deepcopy(self.reports);native=broken['native-versions.json']['results']
            if kind=='missing':native.pop()
            elif kind=='duplicate':native[0]['target']=native[1]['target']
            else:native[0]['unresolved_required_symbols_in_selected_scope']=['symbol']
            self.save(broken)
            with self.assertRaises(ValueError):check_reports(self.root)
    def invoke(self,parts,base):
        return subprocess.run([sys.executable,str(pathlib.Path(__file__).with_name('verify_split_zip.py')),*map(str,parts),'--base',base,'--report',str(self.root/'archive-check.json')],capture_output=True)
    def test_split_zip_readback(self):
        data=b'test-image'*128;manifest={'images':{'system.img':{'size':len(data),'sha256':hashlib.sha256(data).hexdigest()}}}
        buf=io.BytesIO()
        with zipfile.ZipFile(buf,'w') as archive:
            archive.writestr(NAME+'/manifest.json',json.dumps(manifest));archive.writestr(NAME+'/system.img',data)
        raw=buf.getvalue();parts=[]
        for i,start in enumerate(range(0,len(raw),97)):
            part=self.root/('part%03d'%i);part.write_bytes(raw[start:start+97]);parts.append(part)
        self.assertEqual(self.invoke(parts,NAME+'/').returncode,0)
        for prefix in ('../','nested/name/',NAME):self.assertNotEqual(self.invoke(parts,prefix).returncode,0)
        corrupt=bytearray(parts[3].read_bytes());corrupt[20]^=1;parts[3].write_bytes(corrupt)
        self.assertNotEqual(self.invoke(parts,NAME+'/').returncode,0)

if __name__=='__main__':unittest.main()
