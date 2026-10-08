#!/usr/bin/env python3
"""Verify finite range retries, no cursor advance on failure, and SHA256 cache reuse."""
import hashlib
import pathlib
import tempfile
import unittest
from unittest.mock import patch
from inspect_ota import RemoteFile
from download_verified import download

class SourceChecks(unittest.TestCase):
    def test_transient_retry_and_exhaustion(self):
        with patch('inspect_ota.time.sleep'),patch.object(RemoteFile,'_range_once',side_effect=[OSError('reset'),ValueError('short'),b'x']) as request:
            remote=RemoteFile('https://fixture.invalid',attempts=3)
            self.assertEqual(request.call_count,3);self.assertEqual(remote.pos,0)
        remote.size=10
        with patch('inspect_ota.time.sleep'),patch.object(RemoteFile,'_range_once',side_effect=OSError('reset')) as request:
            with self.assertRaises(OSError):remote.read(2)
            self.assertEqual(request.call_count,3);self.assertEqual(remote.pos,0)
    def test_verified_cache_and_corrupt_cache(self):
        data=b'known-source';expected=hashlib.sha256(data).hexdigest()
        class FakeRemote:
            size=len(data)
            def range(self,start,length):return data[start:start+length]
        with tempfile.TemporaryDirectory() as folder:
            target=pathlib.Path(folder)/'source.zip';target.write_bytes(data)
            with patch('download_verified.RemoteFile',side_effect=AssertionError('cache should avoid network')):
                download('https://fixture.invalid',target,expected)
            target.write_bytes(b'bad-cache')
            with patch('download_verified.RemoteFile',return_value=FakeRemote()) as network:
                download('https://fixture.invalid',target,expected)
                self.assertEqual(network.call_count,1)
            self.assertEqual(target.read_bytes(),data)
    def test_bad_retry_limit_rejected(self):
        for attempts in (0,6):
            with self.assertRaises(ValueError):RemoteFile('https://fixture.invalid',attempts=attempts)

if __name__=='__main__':unittest.main()
