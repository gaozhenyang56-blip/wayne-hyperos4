#!/usr/bin/env python3
import unittest
from audit_wifi_contract import assess

class WifiEvidenceTests(unittest.TestCase):
    paths=['lib64/hw/wifi.fixture.so','etc/wifi/fixture.conf']
    def test_builtin_fixture_needs_no_module_but_is_not_verified(self):
        r=assess(self.paths,'builtin',True,False,True)
        self.assertFalse(r['evidence_gate_rejected'])
        for k in ('contract_verified','hardware_tested','wifi_verified','hotspot_verified'):self.assertFalse(r[k])
    def test_unknown_or_module_without_inventory_rejected(self):
        for kind in ('unknown','module'):
            with self.subTest(kind=kind):self.assertTrue(assess(self.paths,kind,True,False,True)['evidence_gate_rejected'])
    def test_missing_files_firmware_or_string_flags_rejected(self):
        self.assertTrue(assess(['build.prop','etc/init/hw/init.qcom.rc'],'builtin',True,False,True)['evidence_gate_rejected'])
        self.assertTrue(assess(self.paths,'builtin',True,False,False)['evidence_gate_rejected'])
        with self.assertRaises(ValueError):assess(self.paths,'builtin','false',False,True)

if __name__=='__main__':unittest.main()
