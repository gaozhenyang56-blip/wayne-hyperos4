#!/usr/bin/env python3
"""Encryption dependency refusal, without changing any cipher or partition."""
import unittest
from static_wayne_layout import static_fstab

BASE=('system /system erofs ro wait,logical,first_stage_mount\n'
      'vendor /vendor erofs ro wait,logical,first_stage_mount\n'
      '/dev/block/by-name/userdata /data ext4 nosuid,nodev wait,fileencryption=ice,quota\n')


class FbeDependencyTests(unittest.TestCase):
    def test_existing_fbe_flags_preserved(self):
        self.assertIn(BASE.splitlines()[2],static_fstab(BASE))

    def test_metadata_keydirectory_refused(self):
        for directory in ('/metadata','/metadata/vold/metadata_encryption'):
            source=BASE.replace('fileencryption=ice','fileencryption=ice,keydirectory='+directory)
            with self.subTest(directory=directory),self.assertRaisesRegex(ValueError,'removed /metadata'):
                static_fstab(source)

    def test_refused_even_if_source_had_metadata_mount(self):
        source=BASE.replace('fileencryption=ice','fileencryption=ice,keydirectory=/metadata/keys')
        source+='/dev/block/by-name/rawdump /metadata ext4 defaults wait\n'
        with self.assertRaisesRegex(ValueError,'removed /metadata'):static_fstab(source)

    def test_unrelated_prefix_not_misclassified(self):
        source=BASE.replace('fileencryption=ice','fileencryption=ice,keydirectory=/metadata_backup/keys')
        self.assertIn('keydirectory=/metadata_backup/keys',static_fstab(source))
        # Passing this narrow dependency guard is NOT key-path authorization.

    def test_fde_reference_flags_not_converted_to_fbe(self):
        source=BASE.replace('fileencryption=ice','encryptable=ice')
        self.assertIn('encryptable=ice',static_fstab(source))
        self.assertNotIn('fileencryption=',static_fstab(source))


if __name__=='__main__':unittest.main()
