#!/usr/bin/env python3
"""Read a concatenated split ZIP without making a second multi-gigabyte copy."""
import argparse
import bisect
import hashlib
import io
import json
import pathlib
import zipfile


class SplitReader(io.RawIOBase):
    def __init__(self, paths):
        self.paths=paths;self.ends=[];total=0
        for path in paths:
            total+=path.stat().st_size;self.ends.append(total)
        self.size=total;self.pos=0

    def readable(self):return True
    def seekable(self):return True
    def tell(self):return self.pos

    def seek(self, offset, whence=0):
        if whence not in (0,1,2):raise ValueError('Invalid seek origin')
        target=offset+(0 if whence==0 else self.pos if whence==1 else self.size)
        if target<0:raise ValueError('Negative seek')
        self.pos=target;return self.pos

    def read(self, length=-1):
        length=min(self.size-self.pos,length if length>=0 else self.size-self.pos)
        if length<=0:return b''
        result=[]
        while length:
            index=bisect.bisect_right(self.ends,self.pos)
            begin=0 if index==0 else self.ends[index-1]
            count=min(length,self.ends[index]-self.pos)
            with self.paths[index].open('rb') as stream:
                stream.seek(self.pos-begin);data=stream.read(count)
            if len(data)!=count:raise ValueError('Truncated part '+str(self.paths[index]))
            result.append(data);self.pos+=count;length-=count
        return b''.join(result)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('parts',type=pathlib.Path,nargs='+')
    parser.add_argument('--report',type=pathlib.Path,required=True)
    args=parser.parse_args()
    base='wayne-hyperos4-offline-20261006/'
    checked=[]
    with zipfile.ZipFile(SplitReader(args.parts)) as archive:
        info=archive.getinfo(base+'manifest.json')
        if info.file_size>1024*1024:raise ValueError('Oversized manifest')
        manifest=json.loads(archive.read(info))
        expected={base+name:record for name,record in manifest['images'].items()}
        for entry in archive.infolist():
            if entry.is_dir():continue
            with archive.open(entry) as stream:
                digest=hashlib.file_digest(stream,'sha256').hexdigest()
            if entry.filename in expected:
                record=expected[entry.filename]
                if entry.file_size!=record['size'] or digest!=record['sha256']:
                    raise ValueError('Image does not match manifest: '+entry.filename)
            checked.append(entry.filename)
        if not set(expected).issubset(checked):raise ValueError('Missing images')
    report={'success':True,'parts':[str(p) for p in args.parts],
            'archive_entries':checked,'image_hashes_match_manifest':True,'hardware_tested':False}
    args.report.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
