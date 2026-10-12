#!/usr/bin/env python3
"""Validate provenance claims and byte bindings; never authenticate a physical device."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import sys
from export_dtb_consumers import canonical_bytes, _write_payload
from read_dtb_identity import MAX_SIZE

SCHEMA='wayne.provenance-manifest.v1'
FIELDS=('schema_version','evidence_role','capture_type','device','soc','collected_at','capture_command','capture_tool_version','container_name','container_sha256','dtb_offset','dtb_length','dtb_sha256','consumer_export_sha256')
MAX_CONTAINER=256*1024*1024
MAX_EXPORT=128*1024*1024
MAX_INTEGER=2**63-1


def _object(pairs):
    result={}
    for name,value in pairs:
        if name in result: raise ValueError('duplicate JSON key: '+name)
        result[name]=value
    return result


def _constant(value): raise ValueError('non-finite JSON constant: '+value)


def envelope(manifest, dtb, consumer_export, container=None):
    if any(not isinstance(v,bytes) for v in (manifest,dtb,consumer_export)) or (container is not None and not isinstance(container,bytes)):
        raise ValueError('immutable byte snapshots required')
    if len(manifest)>65536 or len(consumer_export)>MAX_EXPORT:raise ValueError('manifest/export size limit')
    data=json.loads(manifest.decode('utf-8'),object_pairs_hook=_object,parse_constant=_constant)
    if type(data) is not dict or set(data)!=set(FIELDS):raise ValueError('missing or unknown manifest fields')
    for name in FIELDS:
        value=data[name]
        if name in ('dtb_offset','dtb_length'):
            if type(value) is not int or not 0<=value<=MAX_INTEGER:raise ValueError('bounded nonnegative integer required: '+name)
        else:
            if not isinstance(value,str) or not value.strip() or len(value.encode('utf-8'))>4096 or value.strip().lower() in ('unknown','n/a','none','null','?','-'):
                raise ValueError('nonempty known UTF-8 string required: '+name)
    if data['schema_version']!=SCHEMA or data['device']!='wayne' or data['soc']!='sdm660':raise ValueError('schema/device/SoC mismatch')
    if data['evidence_role'] not in ('synthetic_not_device_evidence','actual_capture_claim'):raise ValueError('unsupported evidence role')
    if data['capture_type'] not in ('synthetic_fixture','live_fdt','boot_slice','dtbo_slice'):raise ValueError('unsupported capture type')
    if (data['evidence_role']=='synthetic_not_device_evidence') != (data['capture_type']=='synthetic_fixture'):raise ValueError('role/capture type conflict')
    stamp=data['collected_at']
    if not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)',stamp) or datetime.datetime.fromisoformat(stamp).utcoffset() is None:raise ValueError('timezone timestamp required')
    for name in ('container_sha256','dtb_sha256','consumer_export_sha256'):
        if not re.fullmatch('[0-9a-f]{64}',data[name]):raise ValueError('lowercase SHA256 required: '+name)
    offset,length=data['dtb_offset'],data['dtb_length']
    if not 0<length<=MAX_SIZE or offset>MAX_INTEGER-length or length!=len(dtb):raise ValueError('offset/length overflow or DTB size mismatch')
    digest=lambda b:hashlib.sha256(b).hexdigest()
    if digest(dtb)!=data['dtb_sha256'] or digest(consumer_export)!=data['consumer_export_sha256']:raise ValueError('DTB/export hash mismatch')
    if consumer_export!=canonical_bytes(dtb):raise ValueError('export is not the canonical bytes for this DTB')
    state='manifest_claim_validated'
    if container is not None:
        if len(container)>MAX_CONTAINER or offset+length>len(container):raise ValueError('container slice outside bounds')
        if digest(container)!=data['container_sha256'] or container[offset:offset+length]!=dtb:raise ValueError('container hash/slice mismatch')
        state='container_slice_verified'
    result={'schema_version':'wayne.provenance-envelope.v1','tool_version':'bind-dtb-provenance/1','manifest_sha256':digest(manifest),'dtb_sha256':digest(dtb),'consumer_export_sha256':digest(consumer_export),'validation_state':state,'manifest_claims':{name:data[name] for name in FIELDS},'physical_source_authenticated':False,'build_gate_authorization':False,'hardware_tested':False}
    return (json.dumps(result,ensure_ascii=False,allow_nan=False,separators=(',',':'))+'\n').encode('utf-8')


def bind(manifest,dtb,consumer_export,container=None,output=None):
    return _write_payload(envelope(manifest,dtb,consumer_export,container),output)


def _read(path,limit):
    with path.open('rb') as stream: blob=stream.read(limit+1)
    if len(blob)>limit:raise ValueError('input too large')
    return blob


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('manifest',type=Path);p.add_argument('dtb',type=Path);p.add_argument('consumer_export',type=Path)
    p.add_argument('--container',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    try:
        payload=bind(_read(a.manifest,65536),_read(a.dtb,MAX_SIZE),_read(a.consumer_export,MAX_EXPORT),_read(a.container,MAX_CONTAINER) if a.container else None,a.output)
        if a.output is None:sys.stdout.buffer.write(payload)
    except (ValueError,OSError) as error:p.exit(2,'REJECT: '+str(error)+'\n')

if __name__=='__main__':main()
