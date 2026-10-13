"""Offline-only stage test/checkpoint runner, no request invocation."""
import datetime,hashlib,json,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[2];p=Path(__file__).resolve().parent
subprocess.run(['python3','tools/test_isolated_parent_commit_probe.py'],cwd=root,check=True)
subprocess.run(['python3','-m','unittest','discover','-s','tools','-p','test_6_6_gate_integration.py','-v'],cwd=root,check=True)
codes={}
for tool in ('ci_kernel_66_probe.py','ci_allocator_implementation.py'):
    r=subprocess.run(['python3','tools/'+tool,'--preflight'],cwd=root,capture_output=True)
    codes[tool]=r.returncode;(p/(tool+'.log')).write_bytes(r.stdout+r.stderr)
    assert r.returncode==2
old=json.loads((root/'research/isolated-blob-review-stage/checkpoint.json').read_bytes())
for item in old['preservation']:assert hashlib.sha256((root/item['path']).read_bytes()).hexdigest()==item['sha256'],item['path']
raw=(p/'evidence.json').read_bytes();d=json.loads(raw)
for name in ('request.json','request.stdout','request.stderr'):
    (p/name).write_bytes((root/'downloads/parent-commit-probe-a091e75'/name).read_bytes())
(p/'checkpoint.json').write_text(json.dumps({'baseline':'a091e75','recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'evidence_sha256':hashlib.sha256(raw).hexdigest(),'tests_passed':7,'preflight':codes,'remote_requests':1,'remote_result':d['request']['result'],'object_store_bytes':d['request']['object_store_bytes'],'preservation_verified':True,'relationship_status':'unresolved','unique_introducing_commit':None,'next':'Same blob already exists at parent 6fbaeffc3a92b4a32b8e320e486cf644ff30d240. Its recorded parent 50ae1c470491481328363639c227020691469f29 remains outside this one-request scope; no further request authorized in this stage.','eligible':False},indent=2)+'\n')
print(codes)
