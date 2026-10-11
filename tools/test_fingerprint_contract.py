import unittest
from audit_fingerprint_contract import assess,relevant_text

class FingerprintEvidenceTests(unittest.TestCase):
    paths=['lib64/hw/fingerprint.fixture.so','etc/init/fingerprint.fixture.rc']
    def test_complete_fixture_opens_material_gate_only(self):
        r=assess(self.paths,True,True,True);self.assertFalse(r['evidence_gate_rejected'])
        for k in ('contract_verified','hardware_tested','enrollment_verified','recognition_verified','unlock_verified'):self.assertFalse(r[k])
    def test_missing_material_binding_or_string_flags_refused(self):
        for p in (self.paths[:1],self.paths[1:],['build.prop','etc/init/hw/init.qcom.rc']):self.assertTrue(assess(p,True,True,True)['evidence_gate_rejected'])
        for flags in ((False,True,True),(True,False,True),(True,True,False)):self.assertTrue(assess(self.paths,*flags)['evidence_gate_rejected'])
        with self.assertRaises(ValueError):assess(self.paths,'false',True,True)
    def test_build_fingerprint_is_not_sensor_evidence(self):
        self.assertFalse(relevant_text('ro.vendor.build.fingerprint=fixture'))
        self.assertTrue(relevant_text('service fingerprint.fixture /vendor/bin/fixture'))
