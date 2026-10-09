#!/usr/bin/env python3
"""ABI rejection, tamper checks, native UAPI and pinned Kconfig subset tests."""
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest
import kconfiglib
from audit_graphics_contract import collect, assess
from extract_wayne_graphics_sample import restore_sparse
import brotli

ROOT = pathlib.Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / 'research/gpu-allocator-stage'


class ContractTests(unittest.TestCase):
    def test_sparse_restore_matches_full_zero_filled_image(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d);data=root/'data.br';transfer=root/'transfer.list'
            data.write_bytes(brotli.compress(b'A'*4096+b'B'*4096))
            transfer.write_text('4\n2\n0\n0\nerase 2,0,1\nnew 4,1,2,3,4\nzero 2,2,3\n')
            report=restore_sparse(data,transfer,root/'vendor.img')
            expected=b'\0'*4096+b'A'*4096+b'\0'*4096+b'B'*4096
            self.assertEqual((root/'vendor.img').read_bytes(),expected)
            self.assertEqual(report['sha256'],hashlib.sha256(expected).hexdigest())

    def test_sparse_restore_rejects_overlaps(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d);data=root/'data.br';transfer=root/'transfer.list'
            data.write_bytes(brotli.compress(b'A'*4096))
            transfer.write_text('4\n1\n0\n0\nnew 2,0,1\nerase 2,0,1\n')
            with self.assertRaisesRegex(ValueError,'Overlapping'):
                restore_sparse(data,transfer,root/'vendor.img')

    def test_actual_sample_rejects_all_three_legacy_abis(self):
        report = json.loads((EVIDENCE / 'graphics-contract.json').read_text())
        profile = json.loads((ROOT / 'config/kernel-6.6-graphics-profile.json').read_text())
        result = assess(report['graphics_files'], profile)
        self.assertEqual({x['abi'] for x in result['findings']}, {'kgsl', 'ion', 'msm_fb'})
        self.assertFalse(result['compatible_verified'])

    def test_modern_paths_do_not_imply_hardware_success(self):
        profile = json.loads((ROOT / 'config/kernel-6.6-graphics-profile.json').read_text())
        r = assess([{'path': 'test.so', 'device_path_strings': ['/dev/dri/renderD128',
                                                                 '/dev/dma_heap/system']}], profile)
        self.assertFalse(r['legacy_pairing_rejected'])
        self.assertFalse(r['compatible_verified'])
        self.assertFalse(r['hardware_tested'])

    def test_hash_tamper_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d); (root / 'x.so').write_bytes(b'changed')
            manifest = {'extracted': [{'path': 'x.so', 'sha256': hashlib.sha256(b'original').hexdigest()}]}
            with self.assertRaisesRegex(ValueError, 'hash changed'):
                collect(root, manifest)

    def test_empty_sample_is_not_accepted(self):
        with self.assertRaisesRegex(ValueError, 'No ELF'):
            collect(ROOT, {'extracted': []})

    def test_native_ion_and_heap_uapi_are_not_interchangeable(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            code = '#include <sys/ioctl.h>\n#include <stddef.h>\n#include <stdio.h>\n'
            code += '#include "' + str(EVIDENCE / 'kernel-uapi/dma-heap.h') + '"\n'
            code += '#include "' + str(EVIDENCE / 'kernel-uapi/ion-lineage.h') + '"\n'
            code += '''int main(void) {
              if (ION_IOC_ALLOC == DMA_HEAP_IOCTL_ALLOC) return 1;
              if (_IOC_TYPE(ION_IOC_ALLOC) != 'I' || _IOC_TYPE(DMA_HEAP_IOCTL_ALLOC) != 'H') return 2;
              if (offsetof(struct ion_allocation_data, fd) == offsetof(struct dma_heap_allocation_data, fd)) return 3;
              printf("ION=%#lx DMA_HEAP=%#lx ion_fd=%zu heap_fd=%zu\\n",
                 (unsigned long)ION_IOC_ALLOC, (unsigned long)DMA_HEAP_IOCTL_ALLOC,
                 offsetof(struct ion_allocation_data, fd), offsetof(struct dma_heap_allocation_data, fd));
              return 0;
            }'''
            (root / 'test.c').write_text(code)
            subprocess.run(['cc', '-Wall', '-Werror', str(root / 'test.c'), '-o', str(root / 'test')], check=True)
            subprocess.run([str(root / 'test')], check=True)

    def test_pinned_allocator_kconfig_before_after_and_dependency(self):
        # Only allocator subtree is resolved; external dependencies are explicit.
        # This is not whole-tree olddefconfig or a new kernel build.
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d);sub = root / 'drivers/dma-buf/heaps';sub.mkdir(parents=True)
            shutil.copyfile(EVIDENCE / 'kernel-uapi/Kconfig', sub / 'Kconfig')
            shutil.copyfile(EVIDENCE / 'kernel-uapi/dma-buf-Kconfig', root / 'dma-buf-Kconfig')
            common = ['DMA_SHARED_BUFFER', 'DMA_CMA', 'DEBUG_FS', 'MEMFD_CREATE', 'COMPILE_TEST', 'DMA_API_DEBUG']
            top = ''.join('config '+x+'\n\tbool "External '+x+'"\n\n' for x in common)
            top += 'source "dma-buf-Kconfig"\n';(root / 'Kconfig').write_text(top)
            old = os.environ.get('srctree');os.environ['srctree'] = str(root)
            try:
                k = kconfiglib.Kconfig(str(root / 'Kconfig'), warn=False)
                def apply(path):
                    for line in path.read_text().splitlines():
                        if line.startswith('CONFIG_') and '=' in line:
                            key, value = line[7:].split('=', 1)
                            if key in k.syms and value in ('y', 'm', 'n'):k.syms[key].set_value(value)
                apply(EVIDENCE / 'kernel-uapi/sdm660_defconfig')
                self.assertEqual(k.syms['DMABUF_HEAPS'].str_value, 'n')
                apply(ROOT / 'config/kernel-6.6-android.fragment')
                for name in ['DMABUF_HEAPS', 'DMABUF_HEAPS_SYSTEM', 'DMABUF_HEAPS_CMA', 'SYNC_FILE']:
                    self.assertEqual(k.syms[name].str_value, 'y', name)
                k.syms['DMA_CMA'].set_value('n')
                self.assertEqual(k.syms['DMABUF_HEAPS_CMA'].str_value, 'n')
                self.assertEqual(k.syms['DMABUF_HEAPS_SYSTEM'].str_value, 'y')
            finally:
                if old is None:os.environ.pop('srctree', None)
                else:os.environ['srctree'] = old


if __name__ == '__main__':
    unittest.main()
