"""Offline tests and preservation only, no repeated query."""
import datetime,hashlib,json,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[2];stage=Path(__file__).resolve().parent
for cmd in (['python3','tools/test_xiaomi_official_source_entry.py'],['python3','-m','unittest','discover','-s','tools','-p','test_6_6_gate_integration.py','-v']):subprocess.run(cmd,cwd=root,check=True)
codes={}
for t in ('ci_kernel_66_probe.py','ci_allocator_implementation.py'):
    r=subprocess.run(['python3','tools/'+t,'--preflight'],cwd=root,capture_output=True);codes[t]=r.returncode
    (stage/(t+'.log')).write_bytes(r.stdout+r.stderr);assert r.returncode==2
old=json.loads((root/'research/isolated-blob-review-stage/checkpoint.json').read_bytes())
for item in old['preservation']:assert hashlib.sha256((root/item['path']).read_bytes()).hexdigest()==item['sha256'],item['path']
raw=(stage/'discovery.json').read_bytes()
(stage/'checkpoint.json').write_text(json.dumps({'baseline':'8c94125','recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'discovery_sha256':hashlib.sha256(raw).hexdigest(),'tests_passed':6,'preflight':codes,'metadata_queries':1,'query_exit_code':0,'matching_refs':0,'source_entry':None,'target_association':'unresolved','preservation_verified':True,'next':'Single official-namespace wayne-prefixed heads query returned no match. No pinned release entry; do not infer global absence. Further official release/table/tag evidence requires separately bounded scope; no retry or source import this stage.','eligible':False},indent=2)+'\n')
print(codes)
