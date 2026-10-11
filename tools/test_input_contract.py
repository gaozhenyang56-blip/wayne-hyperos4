import unittest
from audit_input_contract import assess

class InputEvidenceTests(unittest.TestCase):
    paths=['system/usr/keylayout/Generic.kl']
    def test_verified_fallback_without_idc_opens_material_gate_only(self):
        r=assess(self.paths,True,True,True);self.assertFalse(r['evidence_gate_rejected']);self.assertEqual(r['optional_idc_kcm_candidates'],[])
        for k in ('contract_verified','hardware_tested','touch_verified','keys_verified','gestures_verified'):self.assertFalse(r[k])
    def test_generic_layout_or_kernel_flags_do_not_prove_binding(self):
        self.assertTrue(assess(self.paths)['evidence_gate_rejected'])
        self.assertTrue(assess(['CONFIG_INPUT_EVDEV=y','build.prop','etc/init/hw/init.qcom.rc'],True,True,True)['evidence_gate_rejected'])
        for flags in ((False,True,True),(True,False,True),(True,True,False)):self.assertTrue(assess(self.paths,*flags)['evidence_gate_rejected'])
        with self.assertRaises(ValueError):assess(self.paths,'false',True,True)
