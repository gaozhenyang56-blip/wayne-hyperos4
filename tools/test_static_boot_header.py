#!/usr/bin/env python3
"""Reject unsupported/truncated input; no image is built or repacked."""
import pathlib
import struct
import tempfile
import unittest
from audit_static_boot_config import ROOT,boot


class StaticBootHeaderTests(unittest.TestCase):
    def test_invalid_headers_rejected(self):
        data=(ROOT/'artifacts/experimental/static/boot.img').read_bytes()
        with tempfile.TemporaryDirectory(dir=ROOT/'downloads') as folder:
            path=pathlib.Path(folder)/'header.fixture'
            variants=[b'ANDROID!',data[:4096]]
            for offset,value in [(40,3),(36,0),(24,1),(1632,1),(1644,0)]:
                changed=bytearray(data);struct.pack_into('<I',changed,offset,value);variants.append(changed)
            for index,changed in enumerate(variants):
                path.write_bytes(changed)
                with self.subTest(case=index),self.assertRaises(ValueError):boot(path)


if __name__=='__main__':unittest.main()
