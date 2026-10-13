"""Offline stage verification and breakpoint only, no repeated HTTP request."""
import datetime,hashlib,json,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[2];stage=Path(__file__).resolve().parent
for cmd in (['python3','tools/test_xiaomi_official_releases.py'],['python3','-m','unittest','discover','-s','tools','-p','test_6_6_gate_integration.py','-v']):subprocess.run(cmd,cwd=root,check=True)
codes={}
for t in ('ci_kernel_66_probe.py','ci_allocator_implementation.py'):
    r=subprocess.run(['python3','tools/'+t,'--preflight'],cwd=root,capture_output=True);codes[t]=r.returncode
    (stage/(t+'.log')).write_bytes(r.stdout+r.stderr);assert r.returncode==2
old=json.loads((root/'research/isolated-blob-review-stage/checkpoint.json').read_bytes())
for i in old['preservation']:assert hashlib.sha256((root/i['path']).read_bytes()).hexdigest()==i['sha256'],i['path']
raw=(stage/'discovery.json').read_bytes();d=json.loads(raw)
(stage/'checkpoint.json').write_text(json.dumps({'baseline':'1f2a896','recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'discovery_sha256':hashlib.sha256(raw).hexdigest(),'tests_passed':6,'preflight':codes,'release_requests':1,'http_status':200,'returned_releases':0,'response_scope':d['response_scope'],'source_entry':None,'target_association':'unresolved','preservation_verified':True,'next':'Stop release queries. A separately bounded review of this official repository product release index/README mapping is a feasible higher-information next step; require explicit Mi6X/wayne labeling and pinned file/object identity, never substitute jasmine board evidence. No request in this stage.','eligible':False},indent=2)+'\n')
print(codes)
