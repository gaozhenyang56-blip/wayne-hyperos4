#!/usr/bin/env python3
"""Extract one large remote ZIP member with bounded memory and CRC checking."""
import argparse
import hashlib
import json
import pathlib
import zipfile
from inspect_ota import RemoteFile


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('url')
    parser.add_argument('entry')
    parser.add_argument('output',type=pathlib.Path)
    args=parser.parse_args()
    remote=RemoteFile(args.url)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    part=args.output.with_suffix(args.output.suffix+'.part')
    digest=hashlib.sha256();total=0
    with zipfile.ZipFile(remote) as archive:
        info=archive.getinfo(args.entry)
        with archive.open(info) as source,part.open('wb') as target:
            while block:=source.read(8*1024*1024):
                target.write(block);digest.update(block);total+=len(block)
        if total!=info.file_size:raise ValueError('Incomplete entry')
    part.replace(args.output)
    report={'url':args.url,'entry':args.entry,'size':total,'sha256':digest.hexdigest(),
            'crc_verified':True,'whole_archive_hash_verified':False}
    args.output.with_suffix(args.output.suffix+'.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':main()
