"""Bounded offline snapshot witnesses, never unique-origin or target certification."""
import hashlib,json,os,subprocess
from pathlib import Path
from isolated_blob_review import audit as review_audit,validate as review_validate
from shallow_patch_inventory import canonical,safe_path
from check_source_update import pairs,reject_constant
ROOT=Path(__file__).resolve().parents[1]


def audit(root=ROOT):
    root=Path(root);commands=[]
    def read(path):return (root/path).read_bytes()
    review=read('research/isolated-blob-review-stage/review.json')
    review_validate(review,review_audit(root))
    selected=next(i for i in json.loads(review)['objects'] if i['relationship_status']=='unresolved')
    oid=selected['verified_facts']['oid']
    manifest=read('research/missing-object-stage/manifest.json')
    inventory=read('research/shallow-inventory-stage/inventory.json')
    old=json.loads(read('research/isolated-blob-review-stage/checkpoint.json'))
    for p in old['preservation']:
        if hashlib.sha256(read(p['path'])).hexdigest()!=p['sha256']:raise ValueError('baseline evidence drift')
    repo=root/'downloads/history-probe-73e35d6/fork'
    env=dict(os.environ,GIT_NO_LAZY_FETCH='1',GIT_TERMINAL_PROMPT='0',GIT_NO_REPLACE_OBJECTS='1')
    def git(*args):
        cmd=['git','-c','protocol.allow=never',*args];commands.append(cmd)
        r=subprocess.run(cmd[:3]+['-C',str(repo)]+cmd[3:],capture_output=True,env=env,timeout=5)
        if r.returncode:raise ValueError('local Git evidence unavailable')
        return r.stdout
    url=git('remote','get-url','origin').decode().strip()
    locked=json.loads(read('config/kernel-6.6-experiment.json'))
    if url!=locked['repository'] or url!='https://github.com/sdm660-mainline/linux.git':raise ValueError('fixed remote drift')
    current='6a4e475000ecc7e864911959a1984a0664088464'
    if json.loads(inventory)['current_commit']!=current:raise ValueError('current commit drift')
    refs=git('for-each-ref','--format=%(objectname) %(refname)').decode().splitlines()
    fetched=git('rev-parse','--verify','FETCH_HEAD^{commit}').decode().strip()
    if fetched!=current or locked['commit']!=current:raise ValueError('fixed fetched commit drift')
    contexts=[i for i in json.loads(manifest)['items'] if any(o['oid']==oid for o in i['missing_objects'] or [])]
    if len(contexts)!=1:raise ValueError('ambiguous acquisition context; stop bounded audit')
    context=contexts[0];record=next(i for i in json.loads(inventory)['records'] if i['oid']==context['commit_oid'])
    if not record['path_evidence_complete'] or len(record['parents'])!=1:raise ValueError('context not fully visible single-parent')
    commits=[record['oid'],record['parents'][0]['oid']];paths=record['changed_paths']
    witnesses=[];examined=[]
    def object_bytes(kind,oid):
        raw=git('cat-file',kind,oid)
        if hashlib.sha1((kind+' '+str(len(raw))+'\0').encode()+raw).hexdigest()!=oid:raise ValueError('Git object OID mismatch')
        return raw
    for commit in commits:
        raw=object_bytes('commit',commit);header=raw.split(b'\n\n',1)[0].splitlines()
        trees=[x[5:].decode() for x in header if x.startswith(b'tree ')]
        if len(trees)!=1:raise ValueError('ambiguous commit root tree')
        if commit==record['oid'] and [x[7:].decode() for x in header if x.startswith(b'parent ')]!=[commits[1]]:raise ValueError('parent/commit mismatch')
        entries=git('ls-tree','-r','-z',commit,'--',*paths).split(b'\0');matches=[]
        for entry in filter(None,entries):
            meta,path=entry.split(b'\t',1);mode,kind,target=meta.decode().split();path=path.decode('utf-8');safe_path(path)
            if target!=oid:continue
            if kind!='blob':raise ValueError('selected object is not blob entry')
            tree=trees[0];chain=[]
            parts=path.split('/')
            for pos,part in enumerate(parts):
                tree_raw=object_bytes('tree',tree)
                row=git('ls-tree','-z',tree,'--',part).split(b'\0')
                rows=[x for x in row if x]
                if len(rows)!=1:raise ValueError('nonunique tree component')
                m,n=rows[0].split(b'\t',1);em,ek,eo=m.decode().split()
                if n.decode()!=part or (ek!='tree' if pos<len(parts)-1 else ek!='blob' or eo!=oid):raise ValueError('tree chain mismatch')
                chain.append({'tree_oid':tree,'tree_object_sha256':hashlib.sha256(tree_raw).hexdigest(),'entry_name':part,'mode':em,'type':ek,'entry_oid':eo});tree=eo
            matches.append(path)
            witnesses.append({'snapshot_commit':commit,'commit_object_sha256':hashlib.sha256(raw).hexdigest(),'root_tree':trees[0],'path':path,'tree_chain':chain})
        examined.append({'commit':commit,'paths':paths,'matching_paths':matches})
    return canonical({'schema_version':'wayne.isolated-blob-snapshot-attribution.v1','input_sha256':{'review':hashlib.sha256(review).hexdigest(),'manifest':hashlib.sha256(manifest).hexdigest(),'inventory':hashlib.sha256(inventory).hexdigest()},'selected':selected['verified_facts'],'fixed_fork_url':url,'fixed_current_commit':current,'visible_refs':refs,'fetch_head_commit':fetched,'scope':'single_acquisition_context_current_and_parent_changed_paths_only','examined':examined,'snapshot_witnesses':witnesses,'commands':commands,'git_environment':{k:env[k] for k in ('GIT_NO_LAZY_FETCH','GIT_TERMINAL_PROMPT','GIT_NO_REPLACE_OBJECTS')},'network_requests':0,'relationship_status':'unresolved','unique_introducing_commit':None,'candidate_history':None,'blockers':['unique_origin_not_proven_in_shallow_history','official_candidate_history_unavailable','snapshot_relation_is_not_wayne_target_evidence'],'history_complete':False,'upstream_membership_verified':False,'carry_strategy_reviewed':False,'eligible':False,'source_lock_input':False,'build_gate_authorization':False,'hardware_tested':False})


def validate(raw,expected):
    if len(raw)>1048576:raise ValueError('report too large')
    d=json.loads(raw.decode('utf-8'),object_pairs_hook=pairs,parse_constant=reject_constant)
    if canonical(d)!=expected:raise ValueError('unknown fields/order/OID/chain/tree/qualification drift')
    return expected

if __name__=='__main__':
    import argparse
    from export_dtb_consumers import _write_payload
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);p.add_argument('--check',type=Path);a=p.parse_args()
    payload=audit()
    if a.check:validate(a.check.read_bytes(),payload)
    elif a.output:_write_payload(payload,a.output)
    else:print(payload.decode(),end='')
