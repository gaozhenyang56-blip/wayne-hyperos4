#!/usr/bin/env python3
import copy
import json
import pathlib
import unittest
from audit_graphics_contract import assess

ROOT=pathlib.Path(__file__).resolve().parent.parent


class DisplayFlagTests(unittest.TestCase):
    def setUp(self):
        self.profile=json.loads((ROOT/'config/kernel-6.6-graphics-profile.json').read_text())
        self.rows=json.loads((ROOT/'research/gpu-allocator-stage/graphics-contract.json').read_text())['graphics_files']

    def test_actual_sample_missing_all_three_abis_rejected(self):
        result=assess(self.rows,self.profile)
        self.assertEqual({r['abi'] for r in result['findings']},{'kgsl','ion','msm_fb'})
        self.assertTrue(result['legacy_pairing_rejected'])

    def test_modern_paths_never_imply_display_validation(self):
        result=assess([{'path':'fixture.so','device_path_strings':['/dev/dri/renderD128','/dev/dma_heap/system']}],self.profile)
        self.assertFalse(result['legacy_pairing_rejected'])
        self.assertFalse(result['compatible_verified'])
        self.assertFalse(result['hardware_tested'])

    def test_false_strings_cannot_bypass_refusal(self):
        self.profile['provided_legacy_abis']={key:'false' for key in ('kgsl','ion','msm_fb')}
        with self.assertRaisesRegex(ValueError,'explicit JSON booleans'):assess(self.rows,self.profile)

    def test_missing_or_nonboolean_capability_rejected(self):
        for value in (None,0,1,[],{}):
            profile=copy.deepcopy(self.profile);profile['provided_legacy_abis']['msm_fb']=value
            with self.subTest(value=value),self.assertRaises(ValueError):assess(self.rows,profile)
        del self.profile['provided_legacy_abis']['msm_fb']
        with self.assertRaises(ValueError):assess(self.rows,self.profile)


if __name__=='__main__':unittest.main()
