"""Offline verification and noncanonical checkpoint; never invokes attempt."""
import datetime,hashlib,json,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[2];stage=Path(__file__).resolve().parent
for cmd in (['python3','tools/test_isolated_next_parent_probe.py'],['python3','-m','unittest','discover','-s','tools','-p','test_6_6_gate_integration.py','-v']):subprocess.run(cmd,cwd=root,check=True)
codes={}
for t in ('ci_kernel_66_probe.py','ci_allocator_implementation.py'):
    r=subprocess.run(['python3','tools/'+t,'--preflight'],cwd=root,capture_output=True);codes[t]=r.returncode
    (stage/(t+'.log')).write_bytes(r.stdout+r.stderr);assert r.returncode==2
old=json.loads((root/'research/isolated-blob-review-stage/checkpoint.json').read_bytes())
for item in old['preservation']:assert hashlib.sha256((root/item['path']).read_bytes()).hexdigest()==item['sha256'],item['path']
for path in ['tools/isolated_parent_commit_probe.py','research/isolated-parent-stage/evidence.json','research/isolated-parent-stage/request.json','research/isolated-blob-history-boundary-stage/boundary.json']:
    before=subprocess.run(['git','show','7ed2ee3:'+path],cwd=root,capture_output=True,check=True).stdout
    assert before==(root/path).read_bytes(),path
for name in ('request.json','request.stdout','request.stderr'):(stage/name).write_bytes((root/'downloads/next-parent-probe-7ed2ee3'/name).read_bytes())
raw=(stage/'evidence.json').read_bytes();d=json.loads(raw);e=d['request_engine_evidence']
(stage/'checkpoint.json').write_text(json.dumps({'baseline':'7ed2ee3','recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'evidence_sha256':hashlib.sha256(raw).hexdigest(),'tests_passed':6,'preflight':codes,'remote_requests':1,'remote_result':e['request']['result'],'object_store_bytes':e['request']['object_store_bytes'],'preservation_verified':True,'relationship_status':'unresolved','unique_introducing_commit':None,'next':'Same blob proven at 50ae1c470491481328363639c227020691469f29; its recorded parent 9a6ed4ea985ac4b7a566faddeb16271b8ea54d36 is outside this stage. Stop; no recursive request or second blob.','eligible':False},indent=2)+'\n')
print(codes)
