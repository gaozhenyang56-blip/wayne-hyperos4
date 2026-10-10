#!/usr/bin/env python3
import hashlib
import pathlib
import tempfile
import unittest
from audit_camera_contract import assess_inventory,collect_text

class CameraEvidenceTests(unittest.TestCase):
    def test_complete_fixture_opens_gate_without_compatibility_claim(self):
        result=assess_inventory(['lib64/hw/camera.fixture.so','etc/camera/fixture.xml'])
        self.assertFalse(result['evidence_gate_rejected'])
        for flag in ('contract_verified','hardware_tested','camera_verified','recording_verified'):self.assertFalse(result[flag])

    def test_properties_service_and_each_missing_category_rejected(self):
        for paths in (['build.prop','etc/init/camera-provider.rc'],['lib/hw/camera.fixture.so'],['etc/camera/fixture.xml'],[]):
            with self.subTest(paths=paths):self.assertTrue(assess_inventory(paths)['evidence_gate_rejected'])

    def test_changed_property_evidence_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);(root/'build.prop').write_bytes(b'changed')
            manifest={'extracted':[{'path':'build.prop','sha256':hashlib.sha256(b'original').hexdigest()}]}
            with self.assertRaisesRegex(ValueError,'Sample hash changed'):collect_text(root,manifest)

if __name__=='__main__':unittest.main()
