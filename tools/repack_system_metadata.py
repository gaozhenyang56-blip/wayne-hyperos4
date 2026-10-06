#!/usr/bin/env python3
"""Stream source files to mkfs.erofs, restoring ownership and binary xattrs."""
import argparse
import base64
import io
import json
import os
import pathlib
import stat
import subprocess
import tarfile


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root',type=pathlib.Path)
    parser.add_argument('metadata',type=pathlib.Path)
    parser.add_argument('overlay',type=pathlib.Path)
    parser.add_argument('output',type=pathlib.Path)
    args=parser.parse_args();metadata=json.loads(args.metadata.read_text());patches={}
    with tarfile.open(args.overlay) as tar:
        for entry in tar:
            if entry.isfile():patches[entry.name]=tar.extractfile(entry).read()
    paths=metadata['paths'].copy()
    for name in patches:
        if name not in paths:
            paths[name]={'nid':-1,'mode':stat.S_IFREG|0o644,'uid':0,'gid':0,
                         'xattrs_base64':{'security.selinux':base64.b64encode(b'u:object_r:system_file:s0').decode()}}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    part=args.output.with_suffix(args.output.suffix+'.part')
    command=['tools/local/usr/bin/mkfs.erofs','--tar=f','-zlz4hc','-T1230768000',
             '-U36b70828-7600-5b69-9c83-f2d6d7f8ae01',str(part)]
    process=subprocess.Popen(command,stdin=subprocess.PIPE);seen={}
    try:
        with tarfile.open(fileobj=process.stdin,mode='w|',format=tarfile.PAX_FORMAT) as tar:
            for name,record in sorted(paths.items(),key=lambda x:(x[0].count('/'),x[0])):
                source=args.root/name;entry=tarfile.TarInfo(name)
                entry.uid=record['uid'];entry.gid=record['gid'];entry.mode=stat.S_IMODE(record['mode'])
                entry.mtime=metadata['epoch']
                entry.pax_headers={'SCHILY.xattr.'+key:base64.b64decode(value).decode('utf-8','surrogateescape')
                                   for key,value in record['xattrs_base64'].items()}
                mode=record['mode'];nid=record['nid']
                if stat.S_ISDIR(mode):entry.type=tarfile.DIRTYPE;tar.addfile(entry)
                elif stat.S_ISLNK(mode):entry.type=tarfile.SYMTYPE;entry.linkname=os.readlink(source);tar.addfile(entry)
                elif stat.S_ISREG(mode):
                    if nid in seen and name not in patches:
                        entry.type=tarfile.LNKTYPE;entry.linkname=seen[nid];tar.addfile(entry)
                    else:
                        if nid>=0:seen[nid]=name
                        if name in patches:
                            entry.size=len(patches[name]);tar.addfile(entry,io.BytesIO(patches[name]))
                        else:
                            entry.size=source.stat().st_size
                            with source.open('rb') as stream:tar.addfile(entry,stream)
                else:raise ValueError('Unsupported special inode '+name)
        process.stdin.close();code=process.wait()
        if code:raise RuntimeError('mkfs.erofs failed: '+str(code))
    except BaseException:
        process.stdin.close();process.terminate();process.wait();raise
    part.replace(args.output)
    print(json.dumps({'paths':len(paths),'patched_files':list(patches),'output':str(args.output)}))


if __name__=='__main__':main()
