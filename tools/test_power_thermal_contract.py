import unittest
from audit_power_thermal_contract import assess

class PowerThermalEvidenceTests(unittest.TestCase):
    paths=['lib64/hw/power.fixture.so','lib64/hw/thermal.fixture.so','etc/powerhint.fixture.json','etc/thermal.fixture.conf']
    def test_complete_fixture_never_claims_hardware(self):
        r=assess(self.paths,True);self.assertFalse(r['evidence_gate_rejected'])
        for k in ('contract_verified','hardware_tested','performance_verified','thermal_verified','battery_life_verified'):self.assertFalse(r[k])
    def test_each_missing_material_and_binding_refused(self):
        for n in range(len(self.paths)):
            with self.subTest(n=n):self.assertTrue(assess(self.paths[:n]+self.paths[n+1:],True)['evidence_gate_rejected'])
        self.assertTrue(assess(self.paths)['evidence_gate_rejected'])
        self.assertTrue(assess(['build.prop','etc/init/hw/init.qcom.rc'],True)['evidence_gate_rejected'])
        with self.assertRaises(ValueError):assess(self.paths,'false')
