"""Offline checks and checkpoint only; no source requests."""
import datetime,hashlib,json,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[2];stage=Path(__file__).resolve().parent
for cmd in (['python3','tools/test_pm660_wayne_association.py'],['python3','-m','unittest','discover','-s','tools','-p','test_6_6_gate_integration.py','-v']):subprocess.run(cmd,cwd=root,check=True)
codes={}
for t in ('ci_kernel_66_probe.py','ci_allocator_implementation.py'):
    r=subprocess.run(['python3','tools/'+t,'--preflight'],cwd=root,capture_output=True);codes[t]=r.returncode
    (stage/(t+'.log')).write_bytes(r.stdout+r.stderr);assert r.returncode==2
old=json.loads((root/'research/isolated-blob-review-stage/checkpoint.json').read_bytes())
for item in old['preservation']:assert hashlib.sha256((root/item['path']).read_bytes()).hexdigest()==item['sha256'],item['path']
raw=(stage/'association.json').read_bytes();d=json.loads(raw)
(stage/'checkpoint.json').write_text(json.dumps({'baseline':'1296e39','recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'association_sha256':hashlib.sha256(raw).hexdigest(),'tests_passed':6,'preflight':codes,'network_requests':0,'other_blobs_processed':False,'preservation_verified':True,'target_association':'unresolved','next':'Pinned third-party wayne-named entry directly includes jasmine. No independently admissible actual China-wayne board baseline or same-commit include-chain proof. Stop; do not join 7.x reference with 6.6 jasmine, fetch another source, or resume blob ancestry.','eligible':False},indent=2)+'\n')
print(codes)
