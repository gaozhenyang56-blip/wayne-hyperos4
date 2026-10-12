#!/usr/bin/env python3
"""Local acquisition needs only; no remote actions or permission to acquire."""
import argparse,hashlib,json,os,re,subprocess,sys
from pathlib import Path
from shallow_patch_inventory import canonical
from shallow_review_queue import validate as validate_queue
from check_source_update import pairs,reject_constant
from export_dtb_consumers import _write_payload
FP_KEYS={'schema_version','inventory_sha256','review_queue_sha256','diff_command','patch_id_command','items','success_count','null_reason_counts','history_complete','eligible','hardware_tested'}
ITEM_KEYS={'inventory_sha256','review_queue_sha256','commit_oid','parent_oid','parents','patch_id','diff_sha256','statistics','null_reason','review_status','carry_decision','upstream_membership_verified'}


def build(repo,inv_raw,queue_raw,fp_raw,hashes):
    if set(hashes)!={'inventory','review_queue','fingerprints'}:raise ValueError('unknown binding keys')
    for name,raw in zip(('inventory','review_queue','fingerprints'),(inv_raw,queue_raw,fp_raw)):
        if len(raw)>16*1024*1024 or not re.fullmatch('[0-9a-f]{64}',hashes[name]) or hashlib.sha256(raw).hexdigest()!=hashes[name]:raise ValueError('input binding drift')
    validate_queue(queue_raw,inv_raw,hashes['inventory'])
    inv=json.loads(inv_raw);fp=json.loads(fp_raw.decode('utf-8'),object_pairs_hook=pairs,parse_constant=reject_constant)
    if type(fp) is not dict or set(fp)!=FP_KEYS or fp['schema_version']!='wayne.shallow-patch-fingerprints.v1' or fp['inventory_sha256']!=hashes['inventory'] or fp['review_queue_sha256']!=hashes['review_queue'] or any(fp[k] is not False for k in ('eligible','history_complete','hardware_tested')):raise ValueError('fingerprint schema/claims drift')
    records={r['oid']:r for r in inv['records']};items=[];seen=[];counts={'missing_local_object':0,'shallow_boundary':0}
    env=dict(os.environ,GIT_NO_LAZY_FETCH='1',GIT_TERMINAL_PROMPT='0',GIT_LITERAL_PATHSPECS='1')
    def git(*args,stdin=None):
        r=subprocess.run(['git','-c','protocol.allow=never','-C',str(repo),*args],input=stdin,capture_output=True,env=env,timeout=5)
        if len(r.stdout)>4*1024*1024:raise ValueError('local evidence size limit')
        return r
    for f in fp['items']:
        if type(f) is not dict or set(f)!=ITEM_KEYS or f['commit_oid'] not in records or f['commit_oid'] in seen:raise ValueError('unknown/duplicate fingerprint record')
        seen.append(f['commit_oid']);r=records[f['commit_oid']]
        if f['inventory_sha256']!=hashes['inventory'] or f['review_queue_sha256']!=hashes['review_queue'] or f['parents']!=[p['oid'] for p in r['parents']] or f['review_status']!='unreviewed' or f['carry_decision']!='undetermined' or f['upstream_membership_verified'] is not False:raise ValueError('fingerprint record binding/parent drift')
        if f['parent_oid']!=(r['parents'][0]['oid'] if len(r['parents'])==1 else None):raise ValueError('parent OID contradiction')
        reason=f['null_reason']
        if reason not in ('objects_unavailable','shallow_boundary') or any(f[k] is not None for k in ('patch_id','diff_sha256','statistics')):raise ValueError('unsupported/nonmissing fingerprint state')
        if (reason=='shallow_boundary')!=r['shallow_boundary_commit']:raise ValueError('boundary reason contradiction')
        parents=[]
        for p in r['parents']:
            present=git('cat-file','-e',p['oid']+'^{commit}').returncode==0
            if present!=p['object_available']:raise ValueError('parent presence evidence drift')
            parents.append({**p,'local_presence_checked':present})
        missing=[];unknown=None
        if reason=='shallow_boundary':
            unknown='shallow_completeness_depth_unknown';kind='shallow_boundary'
            need={'action':'separate_completeness_review','object_oids':None,'source_url':None,'depth':None,'network_authorized':False}
        else:
            kind='missing_local_object'
            if len(parents)!=1 or not r['path_evidence_complete']:raise ValueError('not a visible single-parent missing-object record')
            found={}
            for commit in (r['oid'],parents[0]['oid']):
                output=git('ls-tree','-z',commit,'--',*r['changed_paths'])
                if output.returncode:raise ValueError('local tree unavailable; cannot guess missing type')
                if output.stdout and not output.stdout.endswith(b'\0'):raise ValueError('truncated tree evidence')
                for entry in output.stdout.split(b'\0'):
                    if not entry:continue
                    header,path=entry.split(b'\t',1);mode,typ,oid=header.decode().split()
                    if not re.fullmatch('[0-9a-f]{40}',oid):raise ValueError('invalid tree OID')
                    if typ=='blob':found[oid]=typ
            if len(found)>4096:raise ValueError('object request count limit')
            if found:
                batch=git('cat-file','--batch-check',stdin=('\n'.join(sorted(found))+'\n').encode())
                if batch.returncode:raise ValueError('object presence probe failed')
                lines=batch.stdout.decode().splitlines()
                if len(lines)!=len(found):raise ValueError('truncated object presence evidence')
                for oid,line in zip(sorted(found),lines):
                    if line==oid+' missing':missing.append({'oid':oid,'type':'blob','type_basis':'existing_commit_tree_entry','presence':'missing'})
                    elif not re.fullmatch(oid+r' blob [0-9]+',line):raise ValueError('object presence/type contradiction')
            if not missing:raise ValueError('objects exist yet fingerprint is marked missing')
            need={'action':'review_exact_blob_oid_acquisition','object_oids':[m['oid'] for m in missing],'source_url':None,'depth':None,'max_objects':4096,'max_total_bytes':16777216,'timeout_seconds':20,'network_authorized':False}
        counts[kind]+=1
        items.append({'input_sha256':hashes,'commit_oid':r['oid'],'parents':parents,'paths_known':r['path_evidence_complete'],'fingerprint_commit_oid':f['commit_oid'],'fingerprint_null_reason':reason,'acquisition_reason':kind,'missing_objects':missing if missing else None,'unknown_reason':unknown,'minimum_followup_requirement':need,'review_status':'unreviewed','carry_decision':'undetermined'})
    if seen!=sorted(records):raise ValueError('fingerprint record coverage/order drift')
    expected_counts={'shallow_boundary':counts['shallow_boundary'],'paths_unknown':0,'zero_parents':0,'merge_commit':0,'parent_unavailable':0,'objects_unavailable':counts['missing_local_object'],'empty_patch':0,'evidence_limit':0}
    if fp['success_count']!=0 or fp['null_reason_counts']!=expected_counts:raise ValueError('fingerprint summary/reason contradiction')
    return canonical({'schema_version':'wayne.missing-object-acquisition.v1','input_sha256':hashes,'items':items,'reason_counts':counts,'history_complete':False,'upstream_membership_verified':False,'carry_strategy_reviewed':False,'eligible':False,'hardware_tested':False})


def validate(raw,*args):
    if len(raw)>16*1024*1024:raise ValueError('manifest size limit')
    data=json.loads(raw.decode('utf-8'),object_pairs_hook=pairs,parse_constant=reject_constant);expected=json.loads(build(*args))
    if type(data) is not dict or set(data)!=set(expected) or canonical({k:data[k] for k in expected})!=canonical(expected):raise ValueError('unknown fields/reason/hash/OID/order/presence drift')
    return canonical(expected)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('repo',type=Path);p.add_argument('inventory',type=Path);p.add_argument('queue',type=Path);p.add_argument('fingerprints',type=Path);p.add_argument('--hashes',type=Path,required=True);p.add_argument('--output',type=Path);p.add_argument('--validate',type=Path);a=p.parse_args()
    try:
        hashes=json.loads(a.hashes.read_text(),object_pairs_hook=pairs,parse_constant=reject_constant)
        args=(a.repo,a.inventory.read_bytes(),a.queue.read_bytes(),a.fingerprints.read_bytes(),hashes)
        raw=validate(a.validate.read_bytes(),*args) if a.validate else build(*args);_write_payload(raw,a.output)
        if a.output is None:sys.stdout.buffer.write(raw)
    except (ValueError,OSError,subprocess.SubprocessError,TypeError) as e:sys.stderr.write('REJECT: '+str(e)+'\n')
    return 2
if __name__=='__main__':raise SystemExit(main())
