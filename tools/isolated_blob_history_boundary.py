"""Bounded existing-object ancestry evidence; no fetch or unique-origin claims."""
import hashlib,json,os,re,subprocess
from pathlib import Path
from isolated_blob_attribution import audit as attribution_audit,validate,ROOT
from shallow_patch_inventory import canonical


def audit(root=ROOT):
    root=Path(root);folder=root/'research/isolated-blob-attribution-stage'
    original=(folder/'attribution.json').read_bytes()
    if hashlib.sha256(original).hexdigest()!=json.loads((folder/'checkpoint.json').read_bytes())['attribution_sha256']:raise ValueError('attribution binding drift')
    validate(original,attribution_audit(root));base=json.loads(original)
    witnesses=base['snapshot_witnesses']
    if len(witnesses)!=1:raise ValueError('ambiguous starting snapshot')
    witness=witnesses[0];path=witness['path'];oid=base['selected']['oid']
    inventory=(root/'research/shallow-inventory-stage/inventory.json').read_bytes()
    if hashlib.sha256(inventory).hexdigest()!=base['input_sha256']['inventory']:raise ValueError('inventory drift')
    inv=json.loads(inventory);index={r['oid']:r for r in inv['records']}
    if len(index)!=len(inv['records']) or len(index)>64:raise ValueError('duplicate/over-bound inventory')
    repo=root/'downloads/history-probe-73e35d6/fork';commands=[]
    env=dict(os.environ,GIT_NO_LAZY_FETCH='1',GIT_TERMINAL_PROMPT='0',GIT_NO_REPLACE_OBJECTS='1')
    def git(*args):
        cmd=['git','-c','protocol.allow=never',*args];commands.append(cmd)
        r=subprocess.run(cmd[:3]+['-C',str(repo)]+cmd[3:],capture_output=True,env=env,timeout=5)
        if r.returncode:raise ValueError('local object metadata unavailable')
        if len(r.stdout)>2097152:raise ValueError('object metadata size bound')
        return r.stdout
    def obj(kind,oid):
        if not re.fullmatch('[0-9a-f]{40}',oid):raise ValueError('invalid OID')
        raw=git('cat-file',kind,oid)
        if hashlib.sha1((kind+' '+str(len(raw))+'\0').encode()+raw).hexdigest()!=oid:raise ValueError('object OID mismatch')
        return raw
    shallow=(repo/'shallow').read_bytes()
    if sorted(shallow.decode().splitlines())!=sorted(inv['shallow_boundaries']):raise ValueError('shallow boundaries drift')
    start=base['examined'][0]['commit'];current=start;seen=set();snapshots=[];stop=None
    while len(snapshots)<64:
        if current in seen or current not in index:raise ValueError('cycle or outside fixed visible inventory')
        seen.add(current);record=index[current];raw=obj('commit',current)
        if hashlib.sha256(raw).hexdigest()!=record['commit_object_sha256']:raise ValueError('commit/inventory hash drift')
        header=raw.split(b'\n\n',1)[0].splitlines();trees=[r[5:].decode() for r in header if r.startswith(b'tree ')];parents=[r[7:].decode() for r in header if r.startswith(b'parent ')]
        if len(trees)!=1 or parents!=[p['oid'] for p in record['parents']]:raise ValueError('commit/tree/parent relationship drift')
        tree=trees[0];chain=[];entry=None
        for pos,part in enumerate(path.split('/')):
            tr=obj('tree',tree);rows=[r for r in git('ls-tree','-z',tree,'--',part).split(b'\0') if r]
            if not rows:break
            if len(rows)!=1:raise ValueError('duplicate tree entry')
            meta,name=rows[0].split(b'\t',1);mode,kind,target=meta.decode().split()
            if name.decode()!=part:raise ValueError('tree path drift')
            chain.append({'tree_oid':tree,'tree_object_sha256':hashlib.sha256(tr).hexdigest(),'entry_name':part,'mode':mode,'type':kind,'entry_oid':target})
            if pos==len(path.split('/'))-1:
                if kind!='blob':raise ValueError('path is not blob')
                entry=target
            elif kind!='tree':raise ValueError('path parent is not tree')
            tree=target
        snapshots.append({'commit_oid':current,'commit_object_sha256':hashlib.sha256(raw).hexdigest(),'root_tree_oid':trees[0],'parents':record['parents'],'path':path,'path_blob_oid':entry,'selected_blob_present':entry==oid,'tree_chain':chain,'shallow_boundary':record['shallow_boundary_commit']})
        if record['shallow_boundary_commit']:stop='shallow_boundary';break
        if len(parents)!=1:stop='root_or_merge_ambiguity';break
        if len(snapshots)>1 and entry!=oid:stop='path_transition_not_global_unique_origin';break
        if parents[0] not in index:stop='parent_outside_visible_inventory';break
        current=parents[0]
    if stop is None:stop='commit_limit'
    edges=[]
    for child,parent in zip(snapshots,snapshots[1:]):
        if [p['oid'] for p in child['parents']]!=[parent['commit_oid']]:raise ValueError('parent edge drift')
        edges.append({'child':child['commit_oid'],'parent':parent['commit_oid'],'child_path_blob_oid':child['path_blob_oid'],'parent_path_blob_oid':parent['path_blob_oid'],'same_path_object':child['path_blob_oid']==parent['path_blob_oid']})
    last=snapshots[-1]
    return canonical({'schema_version':'wayne.isolated-blob-history-boundary.v1','input_sha256':{'attribution':hashlib.sha256(original).hexdigest(),'inventory':hashlib.sha256(inventory).hexdigest(),'review':base['input_sha256']['review'],'manifest':base['input_sha256']['manifest']},'selected':base['selected'],'fixed_fork_url':base['fixed_fork_url'],'fixed_current_commit':base['fixed_current_commit'],'path':path,'scope':'single_explicit_parent_chain_from_acquisition_context_max_64_existing_commits','snapshots':snapshots,'parent_tree_differences':edges,'shallow_file_sha256':hashlib.sha256(shallow).hexdigest(),'stop_reason':stop,'nearest_proven_ancestral_snapshot':{'commit_oid':last['commit_oid'],'selected_blob_present':last['selected_blob_present'],'shallow_boundary':last['shallow_boundary']},'unique_introducing_commit':None,'introduction_candidates':None,'candidate_unknown_reason':'earlier_than_or_at_shallow_boundary_not_enumerable' if stop=='shallow_boundary' else 'bounded_chain_insufficient_for_unique_origin','relationship_status':'unresolved','commands':commands,'network_requests':0,'history_complete':False,'upstream_membership_verified':False,'carry_strategy_reviewed':False,'eligible':False,'source_lock_input':False,'build_gate_authorization':False,'hardware_tested':False})

if __name__=='__main__':
    import argparse
    from export_dtb_consumers import _write_payload
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);p.add_argument('--check',type=Path);a=p.parse_args();raw=audit()
    if a.check:validate(a.check.read_bytes(),raw)
    elif a.output:_write_payload(raw,a.output)
    else:print(raw.decode(),end='')
