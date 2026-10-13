"""Offline, bounded official tag advertisement validator; never queries network."""
import hashlib,json,os,re,subprocess
from pathlib import Path
from check_xiaomi_official_source_entry import URL,audit as previous_audit
from check_source_update import pairs,reject_constant
from isolated_blob_attribution import validate,ROOT
from shallow_patch_inventory import canonical
from export_dtb_consumers import _write_payload
TOKENS=('wayne','mi6x','mi-6x','mi_6x','MI6X','MI-6X','MI_6X','Mi6X','Mi-6X','Mi_6X','小米6X','小米6x')
CMD=['git','-c','http.followRedirects=false','-c','credential.helper=','ls-remote','--tags',URL,*['refs/tags/*'+s+'*' for s in TOKENS]]
KEYS={'schema_version','baseline_discovery_sha256','source_url','command','request_count','hard_timeout_seconds','exit_code','result','stdout_sha256','stderr_sha256'}


def compose(run_raw,stdout,stderr,base_sha):
    if max(map(len,(run_raw,stdout,stderr)))>65536:raise ValueError('metadata size bound')
    r=json.loads(run_raw.decode(),object_pairs_hook=pairs,parse_constant=reject_constant)
    if type(r) is not dict or set(r)!=KEYS or r['schema_version']!='wayne.xiaomi-official-tag-query.v1' or r['baseline_discovery_sha256']!=base_sha or not re.fullmatch('[0-9a-f]{64}',base_sha) or r['source_url']!=URL or r['command']!=CMD or type(r['request_count']) is not int or r['request_count']!=1 or r['hard_timeout_seconds']!=60 or type(r['exit_code']) is not int or r['result'] not in ('success','timeout','response_size_limit','bot_challenge','auth_required','rate_limited','server_rejected'):raise ValueError('schema/source/query/binding drift')
    for raw,key in ((stdout,'stdout_sha256'),(stderr,'stderr_sha256')):
        if hashlib.sha256(raw).hexdigest()!=r[key]:raise ValueError('response hash drift')
    if (r['exit_code']==0)!=(r['result']=='success'):raise ValueError('exit/result conflict')
    refs={}
    if r['result']=='success':
        if stdout and not stdout.endswith(b'\n'):raise ValueError('truncated response')
        for line in stdout.decode('utf-8').splitlines():
            m=re.fullmatch(r'([0-9a-f]{40})\t(refs/tags/[^\s]+)',line)
            if not m or m[2] in refs:raise ValueError('invalid/duplicate ref or OID')
            name=m[2][len('refs/tags/'):].removesuffix('^{}')
            if not any(token in name for token in TOKENS):raise ValueError('outside query device spelling scope')
            refs[m[2]]=m[1]
    elif stdout:raise ValueError('failed query partial output must not qualify')
    tags=[]
    for ref in sorted(refs):
        if ref.endswith('^{}'):
            if ref[:-3] not in refs:raise ValueError('peeled ref has no tag object')
            continue
        tag=ref[len('refs/tags/'):];label=re.search(r'(?:^|[-_.])(wayne|mi[-_]?6x|小米6x)(?:$|[-_.])',tag,re.I)
        tags.append({'tag':tag,'ref':ref,'tag_object_oid':refs[ref],'peeled_oid':refs.get(ref+'^{}'),'device_label':label[1].casefold() if label else None,'scope':'advertised_tag_label_only_not_actual_board_baseline'})
    entry=None
    if len(tags)==1 and tags[0]['peeled_oid'] is not None and tags[0]['device_label'] is not None:
        entry={'repository_url':URL,'tag':tags[0]['tag'],'immutable_tag_object_oid':tags[0]['tag_object_oid'],'immutable_peeled_oid':tags[0]['peeled_oid'],'device_label':tags[0]['device_label'],'commit_object_imported_or_verified':False}
    reason='query_failed_'+r['result'] if r['result']!='success' else 'no_matching_tags_in_single_query' if not tags else 'unique_annotated_device_tag_metadata_pinned' if entry else 'ambiguous_label_multiple_tags_or_missing_peel_keep_unresolved'
    return canonical({'schema_version':'wayne.xiaomi-official-tags-discovery.v1','baseline_discovery_sha256':base_sha,'query_run_sha256':hashlib.sha256(run_raw).hexdigest(),'query':r,'query_scope':'same_official_repository_tags_known_wayne_Mi6X_spelling_patterns_only','advertised_tags':tags,'source_entry':entry,'discovery_status':'metadata_entry_pinned' if entry else 'unresolved','reason':reason,'release_api_queried':False,'no_global_absence_claim':True,'target_association':'unresolved','board_baseline_verified':False,'history_complete':False,'upstream_membership_verified':False,'carry_strategy_reviewed':False,'eligible':False,'hardware_tested':False,'build_gate_authorization':False,'source_lock_input':False})


def audit(root=ROOT):
    root=Path(root);stage=root/'research/xiaomi-official-tags-stage';old=root/'research/xiaomi-official-entry-stage';base=(old/'discovery.json').read_bytes();sha=hashlib.sha256(base).hexdigest()
    if sha!=json.loads((old/'checkpoint.json').read_bytes())['discovery_sha256']:raise ValueError('baseline hash drift')
    validate(base,previous_audit(root))
    env=dict(os.environ,GIT_NO_LAZY_FETCH='1',GIT_TERMINAL_PROMPT='0',GIT_NO_REPLACE_OBJECTS='1')
    def git(*args,stdin=None):
        q=subprocess.run(['git','-c','protocol.allow=never','-C',str(root),*args],input=stdin,capture_output=True,env=env,timeout=5)
        if q.returncode:raise ValueError('local baseline evidence unavailable')
        return q.stdout
    if git('show','6e0419f:research/xiaomi-official-entry-stage/discovery.json')!=base:raise ValueError('baseline commit drift')
    raw=compose((stage/'query-run.json').read_bytes(),(stage/'ls-remote.stdout').read_bytes(),(stage/'ls-remote.stderr').read_bytes(),sha)
    oids=sorted({oid for tag in json.loads(raw)['advertised_tags'] for oid in (tag['tag_object_oid'],tag['peeled_oid']) if oid})
    if oids:
        expected=''.join(oid+' missing\n' for oid in oids).encode()
        if git('cat-file','--batch-check',stdin=('\n'.join(oids)+'\n').encode())!=expected:raise ValueError('advertised object imported into main database')
    return raw

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);p.add_argument('--check',type=Path);a=p.parse_args();raw=audit()
    if a.check:validate(a.check.read_bytes(),raw)
    elif a.output:_write_payload(raw,a.output)
    else:print(raw.decode(),end='')
