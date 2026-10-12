"""Synthetic ls-remote vectors, NOT real repository evidence."""
import json
import unittest
from candidate_metadata import candidate,canonical,validate_metadata,URL


def raw():
    return (('a'*40)+'\trefs/tags/v6.6.9\n'+('b'*40)+'\trefs/tags/v6.6.9^{}\n'+('c'*40)+'\trefs/tags/v6.6.10\n'+('d'*40)+'\trefs/tags/v6.6.10^{}\n').encode()

class CandidateTests(unittest.TestCase):
    def test_numeric_peeled_stable(self):
        r=raw();m=candidate(r);self.assertEqual(m['candidate_tag'],'v6.6.10');self.assertEqual(m['tag_object'],'c'*40);self.assertEqual(m['peeled_commit'],'d'*40)
        self.assertEqual(canonical(m),validate_metadata(canonical(m),r));self.assertEqual(canonical(m),canonical(candidate(r)));self.assertEqual(m['update_status'],'blocked')
    def test_duplicate_conflict_nonsemver_and_lightweight(self):
        r=raw()
        for bad in (r+r.splitlines(keepends=True)[0],r+('e'*40+'\trefs/tags/v6.6.10\n').encode(),r+('e'*40+'\trefs/tags/v6.6.11-rc1\n').encode(),r+('e'*40+'\trefs/tags/v6.6.11\n').encode(),r[:-1]):
            with self.assertRaises(ValueError):candidate(bad)
    def test_binding_drift(self):
        r=raw();m=candidate(r)
        for key,value in [('source_url','https://drift.invalid'),('peeled_commit','e'*40),('candidate_tag','v6.6.9'),('query_stdout_sha256','0'*64),('current_commit','0'*40),('extra',1)]:
            bad=dict(m);bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate_metadata(canonical(bad),r)
    def test_remote_failure(self):
        for args in ({'exit_code':128},{'complete':False},{'url':'https://drift.invalid'}):
            with self.assertRaises(ValueError):candidate(raw(),**args)
    def test_strict_json(self):
        r=raw();payload=canonical(candidate(r))
        for bad in (b'{"extra":NaN,'+payload[1:],b'{"schema_version":"duplicate",'+payload[1:]):
            with self.assertRaises(ValueError):validate_metadata(bad,r)

if __name__=='__main__':unittest.main()
