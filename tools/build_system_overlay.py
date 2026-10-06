#!/usr/bin/env python3
"""Create a small EROFS overlay; original image metadata is kept by rebuild mode."""
import argparse
import base64
import hashlib
import io
import json
import os
import pathlib
import tarfile


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('system_root',type=pathlib.Path)
    parser.add_argument('fcm5',type=pathlib.Path)
    parser.add_argument('output',type=pathlib.Path)
    parser.add_argument('--device-matrix',type=pathlib.Path,required=True,
                        help='Use the target wayne device matrix, not the donor hardware matrix')
    parser.add_argument('--metadata',type=pathlib.Path,
                        help='Read source labels from the original inode inventory for rootless builds')
    args=parser.parse_args();files={};changes={}
    metadata=json.loads(args.metadata.read_text())['paths'] if args.metadata else None
    def context_for(name):
        if metadata is not None:
            record=metadata.get(name)
            if record is None:return 'u:object_r:system_file:s0'
            return base64.b64decode(record['xattrs_base64']['security.selinux']).decode()
        source=args.system_root/name
        return os.getxattr(source,'security.selinux').decode() if source.exists() else 'u:object_r:system_file:s0'
    for partition,path in [('system','system/build.prop'),('system_ext','system_ext/etc/build.prop'),
                           ('product','product/etc/build.prop')]:
        original=(args.system_root/path).read_bytes()
        replacements={f'ro.product.{partition}.device':'wayne',f'ro.product.{partition}.name':'wayne_hyperos4',
                      f'ro.product.{partition}.brand':'Xiaomi',f'ro.product.{partition}.manufacturer':'Xiaomi',
                      f'ro.product.{partition}.model':'MI 6X'}
        patched='\n'.join((row.split('=',1)[0]+'='+replacements[row.split('=',1)[0]])
                          if '=' in row and row.split('=',1)[0] in replacements else row
                          for row in original.decode().splitlines())+'\n'
        content=patched.encode();files[path]=content
        changes[path]={'before':hashlib.sha256(original).hexdigest(),
                       'after':hashlib.sha256(content).hexdigest(),'properties':replacements}
    path='system/etc/vintf/compatibility_matrix.5.xml';files[path]=args.fcm5.read_bytes()
    changes[path]={'after':hashlib.sha256(files[path]).hexdigest(),'source':str(args.fcm5)}
    path='system/etc/vintf/compatibility_matrix.device.xml'
    files[path]=args.device_matrix.read_bytes()
    changes[path]={'before':hashlib.sha256((args.system_root/path).read_bytes()).hexdigest(),
                   'after':hashlib.sha256(files[path]).hexdigest(),'source':str(args.device_matrix)}
    directories=set()
    for path in files:
        directories.update(str(parent) for parent in pathlib.PurePosixPath(path).parents if str(parent)!='.')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with tarfile.open(args.output,'w',format=tarfile.PAX_FORMAT) as archive:
        for name in ['.']+sorted(directories,key=lambda x:(x.count('/'),x)):
            entry=tarfile.TarInfo(name);entry.type=tarfile.DIRTYPE;entry.mode=0o755
            entry.uid=0;entry.gid=0;entry.mtime=1230768000
            context=context_for(name)
            entry.pax_headers={'SCHILY.xattr.security.selinux':context}
            archive.addfile(entry)
        for name,content in sorted(files.items()):
            entry=tarfile.TarInfo(name);entry.size=len(content);entry.uid=0;entry.gid=0
            entry.mode=0o600 if name.endswith('build.prop') else 0o644;entry.mtime=1230768000
            context=context_for(name)
            entry.pax_headers={'SCHILY.xattr.security.selinux':context}
            archive.addfile(entry,io.BytesIO(content))
    args.output.with_suffix('.json').write_text(json.dumps({'changes':changes,
                          'uid_gid_and_selinux_explicit':True,'payload_files':len(files)},indent=2)+'\n')
    print(json.dumps({'payload_files':len(files),'tar':str(args.output)}))


if __name__=='__main__':main()
