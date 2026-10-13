"""Offline-only tests, preservation and checkpoint; never invokes network attempt."""
import datetime,hashlib,json,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[2];stage=Path(__file__).resolve().parent
for cmd in (['python3','tools/test_isolated_third_parent_probe.py'],['python3','-m','unittest','discover','-s','tools','-p','test_6_6_gate_integration.py','-v']):subprocess.run(cmd,cwd=root,check=True)
codes={}
for tool in ('ci_kernel_66_probe.py','ci_allocator_implementation.py'):
    r=subprocess.run(['python3','tools/'+tool,'--preflight'],cwd=root,capture_output=True);codes[tool]=r.returncode
    (stage/(tool+'.log')).write_bytes(r.stdout+r.stderr);assert r.returncode==2
old=json.loads((root/'research/isolated-blob-review-stage/checkpoint.json').read_bytes())
for item in old['preservation']:assert hashlib.sha256((root/item['path']).read_bytes()).hexdigest()==item['sha256'],item['path']
for path in ['tools/isolated_parent_commit_probe.py','tools/isolated_next_parent_probe.py','research/isolated-parent-stage/evidence.json','research/isolated-next-parent-stage/evidence.json','research/isolated-next-parent-stage/request.json']:
    before=subprocess.run(['git','show','f530131:'+path],cwd=root,capture_output=True,check=True).stdout
    assert before==(root/path).read_bytes(),path
for name in ('request.json','request.stdout','request.stderr'):(stage/name).write_bytes((root/'downloads/third-parent-probe-f530131'/name).read_bytes())
raw=(stage/'evidence.json').read_bytes();d=json.loads(raw);e=d['request_engine_evidence']
(stage/'checkpoint.json').write_text(json.dumps({'baseline':'f530131','recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'evidence_sha256':hashlib.sha256(raw).hexdigest(),'tests_passed':6,'preflight':codes,'remote_requests':1,'remote_result':e['request']['result'],'object_store_bytes':e['request']['object_store_bytes'],'preservation_verified':True,'relationship_status':'unresolved','unique_introducing_commit':None,'information_gain_review':d['information_gain_review'],'next':'Same blob at 9a6ed4ea985ac4b7a566faddeb16271b8ea54d36. Recorded parent add8973e3de6a3557ef5fd0ecc317b24fc6efe6e not acquired. Three layers show no introduction transition; recommend stop incremental requests. No fourth layer authorized or attempted.','eligible':False},indent=2)+'\n')
print(codes)
