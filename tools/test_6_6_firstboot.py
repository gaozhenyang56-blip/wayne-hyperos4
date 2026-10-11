import hashlib
import unittest
from audit_6_6_firstboot import assess_board

class BoardEvidenceTests(unittest.TestCase):
    dts='/ { compatible = "xiaomi,wayne", "qcom,sdm660"; };\n'
    probe={'compiled':True,'outputs':[{'path':'out/arch/arm64/boot/dts/qcom/sdm660-xiaomi-wayne.dtb','sha256':'a'*64}]}
    def evidence(self):return {'target':'China wayne/SDM660','scope':'board_bindings_against_actual_wayne_reference','source_dts_sha256':hashlib.sha256(self.dts.encode()).hexdigest(),'artifact_dtb_sha256':'a'*64,'reference_sha256':'b'*64}
    def test_bound_native_fixture_never_claims_boot(self):
        r=assess_board(self.dts,self.probe,self.evidence());self.assertFalse(r['evidence_gate_rejected'])
        for k in ('hardware_tested','boot_verified','flashable_qualified'):self.assertFalse(r[k])
    def test_renamed_foreign_board_or_missing_mismatched_evidence_refused(self):
        self.assertTrue(assess_board('#include "sdm660-xiaomi-jasmine.dts"\n'+self.dts,self.probe,self.evidence())['evidence_gate_rejected'])
        self.assertTrue(assess_board(self.dts,self.probe)['evidence_gate_rejected'])
        e=self.evidence();e['artifact_dtb_sha256']='c'*64
        self.assertTrue(assess_board(self.dts,self.probe,e)['evidence_gate_rejected'])
        e=self.evidence();e['source_dts_sha256']='c'*64
        self.assertTrue(assess_board(self.dts,self.probe,e)['evidence_gate_rejected'])
