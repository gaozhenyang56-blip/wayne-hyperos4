"""Only local tests and actual preflights; no network/object requests."""
import datetime,hashlib,json,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[2];stage=Path(__file__).resolve().parent
for cmd in (['python3','tools/test_isolated_blob_triage.py'],['python3','-m','unittest','discover','-s','tools','-p','test_6_6_gate_integration.py','-v']):subprocess.run(cmd,cwd=root,check=True)
codes={}
for t in ('ci_kernel_66_probe.py','ci_allocator_implementation.py'):
    r=subprocess.run(['python3','tools/'+t,'--preflight'],cwd=root,capture_output=True);codes[t]=r.returncode
    (stage/(t+'.log')).write_bytes(r.stdout+r.stderr);assert r.returncode==2
old=json.loads((root/'research/isolated-blob-review-stage/checkpoint.json').read_bytes())
for item in old['preservation']:assert hashlib.sha256((root/item['path']).read_bytes()).hexdigest()==item['sha256'],item['path']
for p in ['tools/isolated_third_parent_probe.py','research/isolated-third-parent-stage/evidence.json','research/isolated-third-parent-stage/request.json','research/isolated-blob-review-stage/review.json']:
    assert subprocess.run(['git','show','a5a84d5:'+p],cwd=root,capture_output=True,check=True).stdout==(root/p).read_bytes(),p
raw=(stage/'triage.json').read_bytes();d=json.loads(raw)
(stage/'checkpoint.json').write_text(json.dumps({'baseline':'a5a84d5','recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'triage_sha256':hashlib.sha256(raw).hexdigest(),'tests_passed':6,'preflight':codes,'network_requests':0,'fourth_layer_requested':False,'preservation_verified':True,'classification_counts':d['classification_counts'],'selected_next_target':d['selected_next_target'],'next':'Stop first-blob ancestry. Conditional next review: existing pm660 blob versus independent actual wayne board evidence. That evidence is absent; keep blocked, no network or next-target execution this stage.','eligible':False},indent=2)+'\n')
print(codes)
