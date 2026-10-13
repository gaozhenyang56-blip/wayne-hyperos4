"""Offline validation of one narrow official-namespace ref query; no network calls."""
import hashlib,json,os,re,subprocess
from pathlib import Path
from check_source_update import pairs,reject_constant
from isolated_blob_attribution import validate,ROOT
from shallow_patch_inventory import canonical
from export_dtb_consumers import _write_payload
URL='https://github.com/MiCode/Xiaomi_Kernel_OpenSource.git'
CMD=['git','-c','http.followRedirects=false','-c','credential.helper=','ls-remote','--heads',URL,'refs/heads/wayne*']
KEYS={'schema_version','command','source_url','request_count','hard_timeout_seconds','exit_code','result','stdout_sha256','stderr_sha256'}


def compose(run_raw,stdout,stderr,association_sha):
    if max(len(run_raw),len(stdout),len(stderr))>65536:raise ValueError('metadata size limit')
    r=json.loads(run_raw.decode('utf-8'),object_pairs_hook=pairs,parse_constant=reject_constant)
    if type(r) is not dict or set(r)!=KEYS or r['schema_version']!='wayne.xiaomi-official-query-run.v1' or r['source_url']!=URL or r['command']!=CMD or type(r['request_count']) is not int or r['request_count']!=1 or r['hard_timeout_seconds']!=60 or type(r['exit_code']) is not int or r['result'] not in ('success','timeout','response_size_limit','bot_challenge','auth_required','server_rejected'):raise ValueError('schema/official URL/request policy drift')
    if not re.fullmatch('[0-9a-f]{64}',association_sha) or any(hashlib.sha256(raw).hexdigest()!=r[k] for raw,k in ((stdout,'stdout_sha256'),(stderr,'stderr_sha256'))):raise ValueError('evidence hash drift')
    if (r['result']=='success')!=(r['exit_code']==0):raise ValueError('query exit/result contradiction')
    refs=[]
    if r['result']=='success':
        if stdout and not stdout.endswith(b'\n'):raise ValueError('truncated ref response')
        seen=set()
        for line in stdout.decode('utf-8').splitlines():
            m=re.fullmatch(r'([0-9a-f]{40})\t(refs/heads/wayne[a-z0-9._-]*)',line)
            if not m or m[2] in seen:raise ValueError('malformed/non-wayne/duplicate ref')
            seen.add(m[2]);refs.append({'ref':m[2],'oid':m[1]})
    elif stdout:raise ValueError('failed query has ambiguous partial ref output')
    refs.sort(key=lambda x:x['ref']);entry=None
    if len(refs)==1:
        entry={'repository_url':URL,'official_namespace':'MiCode','ref_at_query':refs[0]['ref'],'immutable_oid':refs[0]['oid'],'object_type_basis':'advertised_heads_ref_not_locally_imported_commit','scope':'official_namespace_advertisement_only_not_board_baseline'}
    reason='query_failed_'+r['result'] if r['result']!='success' else 'no_matching_wayne_heads_in_single_query' if not refs else 'multiple_wayne_refs_no_unique_selection' if len(refs)>1 else 'metadata_entry_pinned_board_baseline_unverified'
    return canonical({'schema_version':'wayne.xiaomi-official-source-discovery.v1','baseline_association_sha256':association_sha,'query_run_sha256':hashlib.sha256(run_raw).hexdigest(),'query':r,'query_scope':'single_MiCode_Xiaomi_Kernel_OpenSource_wayne_prefixed_heads_only','advertised_refs':refs,'source_entry':entry,'discovery_status':'metadata_entry_pinned' if entry else 'unresolved','reason':reason,'official_namespace_basis':'fixed_known_Xiaomi_open_source_MiCode_repository_query','board_baseline_verified':False,'target_association':'unresolved','no_global_absence_claim':True,'history_complete':False,'upstream_membership_verified':False,'carry_strategy_reviewed':False,'eligible':False,'hardware_tested':False,'build_gate_authorization':False,'source_lock_input':False})


def audit(root=ROOT):
    root=Path(root);stage=root/'research/xiaomi-official-entry-stage';base=root/'research/pm660-wayne-association-stage/association.json';raw=base.read_bytes();sha=hashlib.sha256(raw).hexdigest()
    if sha!=json.loads((base.parent/'checkpoint.json').read_bytes())['association_sha256']:raise ValueError('baseline association drift')
    env=dict(os.environ,GIT_NO_LAZY_FETCH='1',GIT_TERMINAL_PROMPT='0',GIT_NO_REPLACE_OBJECTS='1')
    def git(*args,stdin=None):
        r=subprocess.run(['git','-c','protocol.allow=never','-C',str(root),*args],input=stdin,capture_output=True,env=env,timeout=5)
        if r.returncode:raise ValueError('local baseline unavailable')
        return r.stdout
    if git('show','8c94125:research/pm660-wayne-association-stage/association.json')!=raw:raise ValueError('baseline Git binding drift')
    result=compose((stage/'query-run.json').read_bytes(),(stage/'ls-remote.stdout').read_bytes(),(stage/'ls-remote.stderr').read_bytes(),sha)
    d=json.loads(result)
    for ref in d['advertised_refs']:
        oid=ref['oid']
        if git('cat-file','--batch-check',stdin=(oid+'\n').encode())!=(oid+' missing\n').encode():raise ValueError('advertised source object imported into main database')
    return result

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);p.add_argument('--check',type=Path);a=p.parse_args();raw=audit()
    if a.check:validate(a.check.read_bytes(),raw)
    elif a.output:_write_payload(raw,a.output)
    else:print(raw.decode(),end='')
