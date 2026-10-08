#!/usr/bin/env python3
"""Rebuild vendor with static mount rules while preserving all original metadata."""
import argparse
import hashlib
import io
import json
import pathlib
import subprocess
import sys
import tarfile
from erofs_metadata import inventory
from static_wayne_layout import static_fstab,static_vendor_properties

ROOT=pathlib.Path(__file__).resolve().parent.parent

def main():
    p=argparse.ArgumentParser()
    p.add_argument('source',type=pathlib.Path)
    p.add_argument('image',type=pathlib.Path)
    p.add_argument('output',type=pathlib.Path)
    a=p.parse_args()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    metadata=a.output.parent/'vendor-inode-metadata.json'
    metadata.write_text(json.dumps(inventory(a.image,str(ROOT/'tools/local/usr/bin/dump.erofs')),indent=2)+'\n')
    changes={'etc/fstab.qcom':static_fstab((a.source/'etc/fstab.qcom').read_text()).encode(),
             'build.prop':static_vendor_properties((a.source/'build.prop').read_text()).encode()}
    overlay=a.output.parent/'vendor-overlay.tar'
    with tarfile.open(overlay,'w') as archive:
        for name,content in changes.items():
            entry=tarfile.TarInfo(name);entry.size=len(content)
            archive.addfile(entry,io.BytesIO(content))
    subprocess.run([sys.executable,str(ROOT/'tools/repack_system_metadata.py'),str(a.source),
                    str(metadata),str(overlay),str(a.output)],cwd=ROOT,check=True)
    report={'layout':'stock-size-static','original_vendor':str(a.image),
            'modified_files':list(changes),'partition_table_changed':False,
            'rawdump_repurposed':False,'hardware_tested':False,
            'output_size':a.output.stat().st_size,
            'output_sha256':hashlib.file_digest(a.output.open('rb'),'sha256').hexdigest()}
    a.output.with_suffix('.img.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
