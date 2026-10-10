#!/usr/bin/env python3
import unittest
from audit_audio_contract import assess_inventory

class AudioEvidenceTests(unittest.TestCase):
    def test_minimal_inventory_opens_only_evidence_gate(self):
        result=assess_inventory(['lib64/hw/audio.primary.fixture.so','etc/mixer_paths_fixture.xml','etc/audio_platform_info_fixture.xml'])
        self.assertFalse(result['evidence_gate_rejected'])
        self.assertFalse(result['contract_verified'])
        self.assertFalse(result['hardware_tested'])
        self.assertFalse(result['audio_verified'])
        self.assertFalse(result['calls_verified'])

    def test_properties_and_service_are_not_hal_or_routes(self):
        result=assess_inventory(['build.prop','etc/init/hw/init.qcom.rc'])
        self.assertTrue(result['evidence_gate_rejected'])
        self.assertEqual(set(result['missing_evidence_categories']),{'audio_hal','mixer_paths','audio_platform_info'})

    def test_each_missing_category_refuses_contract_review(self):
        paths=['lib/hw/audio.primary.fixture.so','etc/mixer_paths.xml','etc/audio_platform_info.xml']
        for index in range(len(paths)):
            with self.subTest(index=index):self.assertTrue(assess_inventory(paths[:index]+paths[index+1:])['evidence_gate_rejected'])

if __name__=='__main__':unittest.main()
