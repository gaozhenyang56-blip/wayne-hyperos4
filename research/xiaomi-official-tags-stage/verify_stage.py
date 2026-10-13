"""Offline checks only; no repeat or expanded metadata query."""
import datetime,hashlib,json,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[2];stage=Path(__file__).resolve().parent
for cmd in (['python3','tools/test_xiaomi_official_tags.py'],['python3','-m','unittest','discover','-s','tools','-p','test_6_6_gate_integration.py','-v']):subprocess.run(cmd,cwd=root,check=True)
codes={}
for tool in ('ci_kernel_66_probe.py','ci_allocator_implementation.py'):
    r=subprocess.run(['python3','tools/'+tool,'--preflight'],cwd=root,capture_output=True);codes[tool]=r.returncode
    (stage/(tool+'.log')).write_bytes(r.stdout+r.stderr);assert r.returncode==2
old=json.loads((root/'research/isolated-blob-review-stage/checkpoint.json').read_bytes())
for i in old['preservation']:assert hashlib.sha256((root/i['path']).read_bytes()).hexdigest()==i['sha256'],i['path']
raw=(stage/'discovery.json').read_bytes()
(stage/'checkpoint.json').write_text(json.dumps({'baseline':'6e0419f','recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'discovery_sha256':hashlib.sha256(raw).hexdigest(),'tests_passed':6,'preflight':codes,'metadata_queries':1,'query_exit_code':0,'matching_tags':0,'source_entry':None,'release_api_queried':False,'target_association':'unresolved','preservation_verified':True,'next':'Single official repository tag-pattern query had no matches. No global absence claim; release descriptions or other naming remain outside scope. Stop without heads repeat, API fallback, retry or source import.','eligible':False},indent=2)+'\n')
print(codes)
