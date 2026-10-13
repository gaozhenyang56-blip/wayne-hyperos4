"""One more explicit parent only; reuse an isolated instance of the v1 request engine."""
import hashlib,importlib.util,json,re
from pathlib import Path
import isolated_parent_commit_probe as prior
from isolated_blob_attribution import validate,ROOT
from shallow_patch_inventory import canonical
from export_dtb_consumers import _write_payload
SLOT='downloads/next-parent-probe-7ed2ee3'


def context(root=ROOT):
    root=Path(root);stage=root/'research/isolated-parent-stage'
    raw=(stage/'evidence.json').read_bytes();sha=hashlib.sha256(raw).hexdigest()
    if sha!=json.loads((stage/'checkpoint.json').read_bytes())['evidence_sha256']:raise ValueError('previous evidence hash drift')
    validate(raw,prior.audit(root));d=json.loads(raw);child=d['parent_snapshot']
    if child is None or d['stop_reason']!='same_blob_in_parent':raise ValueError('previous parent not a verified continuation')
    cr=prior.local(root/prior.SLOT,'cat-file','commit',child['commit_oid'])
    actual=hashlib.sha1(b'commit '+str(len(cr)).encode()+b'\0'+cr).hexdigest()
    parents=[line[7:].decode() for line in cr.split(b'\n\n',1)[0].splitlines() if line.startswith(b'parent ')]
    if actual!=child['commit_oid'] or hashlib.sha256(cr).hexdigest()!=child['commit_object_sha256'] or parents!=child['parents'] or len(parents)!=1 or not re.fullmatch('[0-9a-f]{40}',parents[0]):raise ValueError('not a unique exact parent')
    oid=parents[0]
    # Only the single directly recorded parent is queried, offline, for presence.
    for repo in (root,root/'downloads/history-probe-73e35d6/fork',root/prior.SLOT):
        if prior.local(repo,'cat-file','--batch-check',stdin=(oid+'\n').encode())!=(oid+' missing\n').encode():raise ValueError('parent already present or main/old isolation pollution')
    return d,sha,oid


def engine(root=ROOT):
    root=Path(root);previous,sha,parent=context(root)
    spec=importlib.util.spec_from_file_location('_one_explicit_next_parent_engine',Path(prior.__file__))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    # Separate module instance: do not mutate the old verifier or old evidence.
    module.PARENT=parent;module.CHILD=previous['parent_snapshot']['commit_oid'];module.SLOT=SLOT
    def prepare(task_root=ROOT):
        d,digest,oid=context(task_root)
        if oid!=parent or digest!=sha:raise ValueError('context changed')
        return {'selected':d['selected_blob'],'path':d['path'],'snapshots':[d['parent_snapshot']]},digest
    module.prepare=prepare
    return module,previous,sha,parent


def attempt(root=ROOT):
    module,_,_,_=engine(root)
    return module.attempt(root)


def audit(root=ROOT):
    module,previous,sha,parent=engine(root);payload=module.audit(root);d=json.loads(payload)
    return canonical({'schema_version':'wayne.isolated-next-parent-boundary-evidence.v2','previous_evidence_sha256':sha,'engine_source_sha256':hashlib.sha256(Path(prior.__file__).read_bytes()).hexdigest(),'scope':'one_direct_parent_of_verified_6fbaeff_snapshot_only','derived_parent_oid':parent,'derivation_command':['git','-c','protocol.allow=never','cat-file','commit',previous['parent_snapshot']['commit_oid']],'request_engine_evidence':d,'relationship_status':'unresolved','unique_introducing_commit':None,'history_complete':False,'upstream_membership_verified':False,'carry_strategy_reviewed':False,'eligible':False,'source_lock_input':False,'build_gate_authorization':False,'hardware_tested':False})

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--attempt',action='store_true');p.add_argument('--output',type=Path);p.add_argument('--check',type=Path);a=p.parse_args()
    if a.attempt:attempt()
    raw=audit()
    if a.check:validate(a.check.read_bytes(),raw)
    elif a.output:_write_payload(raw,a.output)
    else:print(raw.decode(),end='')
