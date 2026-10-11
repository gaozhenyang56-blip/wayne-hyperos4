import unittest
from audit_vibrator_contract import assess

class VibratorEvidenceTests(unittest.TestCase):
    paths=['lib64/hw/vibrator.fixture.so']
    def test_single_alternative_backend_opens_material_gate_only(self):
        for backend in ('timed_output','led_class','input_ff','vendor'):
            with self.subTest(backend=backend):
                r=assess(self.paths,backend,True,True);self.assertFalse(r['evidence_gate_rejected'])
                for k in ('contract_verified','hardware_tested','vibration_verified','haptic_effects_verified'):self.assertFalse(r[k])
    def test_unknown_backend_missing_material_or_binding_refused(self):
        self.assertTrue(assess(self.paths,'unknown',True,True)['evidence_gate_rejected'])
        self.assertTrue(assess(['build.prop','CONFIG_ANDROID_TIMED_OUTPUT=y'],'timed_output',True,True)['evidence_gate_rejected'])
        for flags in ((False,True),(True,False)):self.assertTrue(assess(self.paths,'vendor',*flags)['evidence_gate_rejected'])
        with self.assertRaises(ValueError):assess(self.paths,'vendor','false',True)
        with self.assertRaises(ValueError):assess(self.paths,'guessed_backend',True,True)
