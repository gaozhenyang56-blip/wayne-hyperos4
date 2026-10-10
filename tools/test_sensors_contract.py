#!/usr/bin/env python3
import unittest
from audit_sensors_contract import assess

class SensorsEvidenceTests(unittest.TestCase):
    paths=['lib64/hw/sensors.fixture.so','etc/sensors/fixture.conf']
    def test_complete_fixture_opens_gate_without_runtime_claim(self):
        r=assess(self.paths,True,True);self.assertFalse(r['evidence_gate_rejected'])
        for k in ('contract_verified','hardware_tested','sensors_verified','sensors_function_verified'):self.assertFalse(r[k])
    def test_init_paths_cannot_substitute_hal_or_transport(self):
        self.assertTrue(assess(['build.prop','etc/init/hw/init.qcom.rc','dev/serialFixture','sys/class/input/fixture'])['evidence_gate_rejected'])
        self.assertTrue(assess(self.paths,False,True)['evidence_gate_rejected'])
        self.assertTrue(assess(self.paths,True,False)['evidence_gate_rejected'])
    def test_each_missing_category_and_string_flags_rejected(self):
        for p in (self.paths[:1],self.paths[1:]):self.assertTrue(assess(p,True,True)['evidence_gate_rejected'])
        with self.assertRaises(ValueError):assess(self.paths,'false',True)

if __name__=='__main__':unittest.main()
