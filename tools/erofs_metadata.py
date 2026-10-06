#!/usr/bin/env python3
"""Inventory ordinary EROFS inodes, ownership and binary xattrs without root."""
import argparse
import base64
import concurrent.futures
import json
import mmap
import pathlib
import re
import struct
import subprocess


def inventory(image,dumper):
    with image.open('rb') as source,mmap.mmap(source.fileno(),0,access=mmap.ACCESS_READ) as data:
        sb=1024
        if struct.unpack_from('<I',data,sb)[0]!=0xe0f5e1e2:raise ValueError('Not EROFS')
        block=1<<data[sb+12]
        meta=struct.unpack_from('<I',data,sb+40)[0]*block
        shared=struct.unpack_from('<I',data,sb+44)[0]*block
        root=struct.unpack_from('<H',data,sb+14)[0]
        if data[sb+91]:raise ValueError('Long xattr prefixes not supported')
        epoch=struct.unpack_from('<Q',data,sb+24)[0]
        prefixes={1:'user.',2:'system.posix_acl_access',3:'system.posix_acl_default',
                  4:'trusted.',5:'lustre.',6:'security.'}
        def xattr(offset):
            length,index,value_size=struct.unpack_from('<BBH',data,offset)
            if index not in prefixes:raise ValueError('Unknown xattr prefix '+str(index))
            name=prefixes[index]+data[offset+4:offset+4+length].decode()
            value=data[offset+4+length:offset+4+length+value_size]
            return name,base64.b64encode(value).decode(),(offset+4+length+value_size+3)&~3
        def inode(nid):
            offset=meta+nid*32
            form,count,mode=struct.unpack_from('<HHH',data,offset)
            extended=bool(form&1);size=64 if extended else 32
            uid,gid=struct.unpack_from('<II' if extended else '<HH',data,offset+24)
            attributes={}
            if count:
                start=offset+size;shared_count=data[start+4]
                for i in range(shared_count):
                    key=struct.unpack_from('<I',data,start+12+4*i)[0]
                    name,value,_=xattr(shared+key*4);attributes[name]=value
                position=start+12+4*shared_count;end=start+12+(count-1)*4
                while position<end:
                    name,value,position=xattr(position);attributes[name]=value
            return {'nid':nid,'mode':mode,'uid':uid,'gid':gid,'xattrs_base64':attributes}
        paths={'.':inode(root)};pending=[('/',root)]
        def listing(item):
            path,nid=item
            output=subprocess.check_output([dumper,'--ls','--nid='+str(nid),str(image)],text=True)
            entries=[]
            for line in output.splitlines():
                match=re.match(r'^\s*(\d+)\s+([1-7])\s+(.+)$',line)
                if not match:continue
                child,kind,name=match.groups()
                if name in ('.','..'):continue
                if '/' in name or '\0' in name:raise ValueError('Unsafe directory entry')
                entries.append((path.rstrip('/')+'/'+name,int(child),int(kind)))
            return entries
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            while pending:
                batch=pending;pending=[]
                for entries in pool.map(listing,batch):
                    for path,nid,kind in entries:
                        name=path.lstrip('/');paths[name]=inode(nid)
                        if kind==2:pending.append((path,nid))
        return {'image':str(image),'block_size':block,'epoch':epoch,'paths':paths}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image',type=pathlib.Path)
    parser.add_argument('output',type=pathlib.Path)
    parser.add_argument('--dumper',default='tools/local/usr/bin/dump.erofs')
    args=parser.parse_args();record=inventory(args.image,args.dumper)
    args.output.write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({'paths':len(record['paths']),'output':str(args.output)}))
