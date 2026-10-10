#!/usr/bin/env python3
"""Native static input and refusal tests; these do not identify real hardware."""
import unittest
from static_wayne_layout import static_cmdline


class StaticBootCmdlineTests(unittest.TestCase):
    def test_native_static_without_super(self):
        # Tokens present in the non-Miku wayne sample and fixed device config.
        source='console=ttyMSM0,115200n8 androidboot.hardware=qcom androidboot.usbcontroller=a800000.dwc3'
        result=static_cmdline(source).split()
        self.assertEqual(result[:-2],source.split())
        self.assertEqual(result[-2:],['androidboot.dynamic_partitions=false',
                                     'androidboot.dynamic_partitions_retrofit=false'])

    def test_static_normalization_idempotent(self):
        source='androidboot.hardware=qcom androidboot.dynamic_partitions=false'
        result=static_cmdline(source)
        self.assertEqual(result,static_cmdline(result))

    def test_old_conversion_output_unchanged(self):
        source='androidboot.hardware=qcom keep=yes androidboot.super_partition=system androidboot.dynamic_partitions=true'
        self.assertEqual(static_cmdline(source),'androidboot.hardware=qcom keep=yes androidboot.dynamic_partitions=false androidboot.dynamic_partitions_retrofit=false')

    def test_incomplete_or_conflicting_hardware_rejected(self):
        for source in ('', 'foo=bar', 'androidboot.hardware=other',
                       'androidboot.hardware=qcom androidboot.hardware=qcom',
                       'androidboot.hardware=qcom androidboot.hardware=other'):
            with self.subTest(source=source),self.assertRaises(ValueError):
                static_cmdline(source)


if __name__=='__main__':
    unittest.main()
