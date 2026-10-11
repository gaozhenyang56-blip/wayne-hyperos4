import unittest
from audit_radio_contract import assess

class RadioEvidenceTests(unittest.TestCase):
    paths=['lib64/hw/radio.fixture.so','radio/qcril_database/qcril.db']
    def test_complete_fixture_opens_material_gate_only(self):
        r=assess(self.paths,True,True,True);self.assertFalse(r['evidence_gate_rejected'])
        for k in ('contract_verified','hardware_tested','calls_verified','sms_verified','data_verified','volte_verified'):self.assertFalse(r[k])
    def test_reference_vendor_or_missing_material_cannot_pass(self):
        for flags in ((False,True,True),(True,False,True),(True,True,False)):
            with self.subTest(flags=flags):self.assertTrue(assess(self.paths,*flags)['evidence_gate_rejected'])
        for paths in (self.paths[:1],self.paths[1:],['build.prop','etc/init/hw/init.qcom.rc']):self.assertTrue(assess(paths,True,True,True)['evidence_gate_rejected'])
        with self.assertRaises(ValueError):assess(self.paths,'false',True,True)
