#!/usr/bin/env python3
import unittest
from audit_kgsl_dt_closure import closure


class ClosureTests(unittest.TestCase):
    def test_complete_fixture_records_dependencies_without_hardware_claim(self):
        files={'board.dts':'#include "gpu.dtsi"',
               'gpu.dtsi':'gpu: gpu@0 { compatible="fixture,kgsl"; clocks=<&clk>; iommus=<&smmu>; vdd-supply=<&rail>; };'}
        result=closure('board.dts',files)
        self.assertTrue(result['textual_closure_complete'])
        self.assertTrue(result['kgsl_text_seen'])
        self.assertFalse(result['cpp_dtc_or_phandle_resolution_performed'])

    def test_missing_include_cannot_prove_kgsl_absence(self):
        result=closure('board.dts',{'board.dts':'#include "soc.dtsi"'})
        self.assertEqual(result['missing_includes'],['soc.dtsi'])
        self.assertFalse(result['textual_closure_complete'])
        self.assertFalse(result['kgsl_absence_proven'])

    def test_cycle_is_not_a_complete_closure(self):
        result=closure('a',{'a':'#include "b"','b':'#include "a"'})
        self.assertEqual(result['cycles'],['a'])
        self.assertFalse(result['textual_closure_complete'])

    def test_commented_gpu_and_include_are_not_evidence(self):
        result=closure('board.dts',{'board.dts':'/* #include "missing"\nkgsl {}; */\n// gpu@0 {};\n/ {}; '})
        self.assertTrue(result['textual_closure_complete'])
        self.assertFalse(result['kgsl_text_seen'])
        self.assertFalse(result['kgsl_absence_proven'])


if __name__=='__main__':unittest.main()
