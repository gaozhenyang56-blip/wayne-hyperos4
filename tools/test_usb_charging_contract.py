import unittest
from audit_usb_charging_contract import assess_imports

class UsbImportTests(unittest.TestCase):
    text='import /vendor/etc/init/usb.fixture.rc\n'
    def test_literal_import_closure_never_claims_hardware(self):
        r=assess_imports(self.text,['etc/init/usb.fixture.rc']);self.assertFalse(r['evidence_gate_rejected'])
        for k in ('contract_verified','hardware_tested','charging_verified','usb_data_verified','adb_verified','otg_verified'):self.assertFalse(r[k])
    def test_missing_dynamic_or_unobserved_import_refused(self):
        self.assertTrue(assess_imports(self.text,[])['evidence_gate_rejected'])
        for text in ('import /vendor/etc/init/usb.${fixture}.rc','import /vendor/etc/init/usb.*.rc','# import /vendor/etc/init/usb.fixture.rc','import /vendor/etc/init/../usb.fixture.rc'):
            with self.subTest(text=text):self.assertTrue(assess_imports(text,['etc/init/usb.fixture.rc'])['evidence_gate_rejected'])
