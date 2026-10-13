"""Offline index-entry gap, never derive an endpoint from a repository URL."""
import hashlib,json,os,re,subprocess
from pathlib import Path
from check_xiaomi_official_releases import audit as release_audit
from isolated_blob_attribution import ROOT,validate
from shallow_patch_inventory import canonical
from export_dtb_consumers import _write_payload
SCOPE=['README.md','sources.lock.json','config/project-requirements.json','docs/xiaomi-official-source-entry.md','docs/xiaomi-official-tags-discovery.md','docs/xiaomi-official-releases.md']+[f'research/{stage}/{name}' for stage,names in [('xiaomi-official-entry-stage',['query-run.json','discovery.json']),('xiaomi-official-tags-stage',['query-run.json','discovery.json']),('xiaomi-official-releases-stage',['request.json','discovery.json','checkpoint.json'])] for name in names]
BASE='https://github.com/MiCode/Xiaomi_Kernel_OpenSource.git'
RELEASE='https://api.github.com/repos/MiCode/Xiaomi_Kernel_OpenSource/releases?per_page=20&page=1'


def audit(root=ROOT):
    root=Path(root);release=(root/'research/xiaomi-official-releases-stage/discovery.json').read_bytes();validate(release,release_audit(root))
    records=[];refs=[];env=dict(os.environ,GIT_NO_LAZY_FETCH='1',GIT_TERMINAL_PROMPT='0',GIT_NO_REPLACE_OBJECTS='1')
    for path in SCOPE:
        raw=(root/path).read_bytes()
        q=subprocess.run(['git','-c','protocol.allow=never','-C',str(root),'show','03f7a8c:'+path],env=env,capture_output=True,timeout=5)
        if q.returncode or q.stdout!=raw or len(raw)>4194304:raise ValueError('scoped baseline missing/changed/oversize')
        text=raw.decode('utf-8');urls=sorted(set(re.findall(r'https://(?:github\.com/|api\.github\.com/repos/|raw\.githubusercontent\.com/)MiCode/Xiaomi_Kernel_OpenSource[A-Za-z0-9._~:/?&=%+#*-]*',text)))
        records.append({'path':path,'sha256':hashlib.sha256(raw).hexdigest(),'official_repository_url_mentions':urls})
        refs.extend(urls)
    urls=sorted(set(refs));unexpected=[u for u in urls if u not in (BASE,BASE[:-4],RELEASE)]
    if unexpected:raise ValueError('new possible index reference needs explicit re-review; no guessed request')
    run_paths=[('heads','research/xiaomi-official-entry-stage/query-run.json'),('tags','research/xiaomi-official-tags-stage/query-run.json'),('releases_page','research/xiaomi-official-releases-stage/request.json')]
    coverage=[]
    for kind,path in run_paths:
        raw=(root/path).read_bytes();r=json.loads(raw)
        coverage.append({'kind':kind,'request_sha256':hashlib.sha256(raw).hexdigest(),'command':r['command'],'result_scope_only':True})
    return canonical({'schema_version':'wayne.official-product-index-gap.v1','baseline':'03f7a8c','baseline_release_sha256':hashlib.sha256(release).hexdigest(),'offline_scope':records,'official_repository':BASE,'covered_metadata_boundaries':coverage,'index_entry':None,'index_entry_status':'unresolved_no_explicit_product_index_path_url_version_in_examined_records','suggestion_is_not_endpoint_evidence':True,'request_status':'not_attempted_missing_unique_index_entry','network_requests':0,'response_count':None,'pagination':None,'truncated':None,'device_matches':None,'negative_index_query_result':False,'source_entry':None,'target_association':'unresolved','next_evidence_required':['exact_authoritative_official_product_index_url_or_file_path','recorded_official_linkage_to_same_repository','version_or_object_identity_and_explicit_wayne_Mi6X_mapping'],'stop_repetitive_metadata_queries':True,'no_global_absence_claim':True,'history_complete':False,'upstream_membership_verified':False,'carry_strategy_reviewed':False,'eligible':False,'hardware_tested':False,'build_gate_authorization':False,'source_lock_input':False})

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);p.add_argument('--check',type=Path);a=p.parse_args();raw=audit()
    if a.check:validate(a.check.read_bytes(),raw)
    elif a.output:_write_payload(raw,a.output)
    else:print(raw.decode(),end='')
