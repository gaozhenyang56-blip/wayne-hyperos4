"""Third single parent only; retain all prior evidence and request implementations."""
import hashlib,importlib.util,json,re
from pathlib import Path
import isolated_parent_commit_probe as original
import isolated_next_parent_probe as previous
from isolated_blob_attribution import validate,ROOT
from shallow_patch_inventory import canonical
from export_dtb_consumers import _write_payload
SLOT='downloads/third-parent-probe-f530131'


def context(root=ROOT):
    root=Path(root);stage=root/'research/isolated-next-parent-stage'
    raw=(stage/'evidence.json').read_bytes();sha=hashlib.sha256(raw).hexdigest()
    if sha!=json.loads((stage/'checkpoint.json').read_bytes())['evidence_sha256']:raise ValueError('previous evidence binding drift')
    validate(raw,previous.audit(root));d=json.loads(raw)['request_engine_evidence'];child=d['parent_snapshot']
    if child is None or d['stop_reason']!='same_blob_in_parent':raise ValueError('no verified single continuation')
    cr=original.local(root/previous.SLOT,'cat-file','commit',child['commit_oid'])
    parents=[r[7:].decode() for r in cr.split(b'\n\n',1)[0].splitlines() if r.startswith(b'parent ')]
    if hashlib.sha1(b'commit '+str(len(cr)).encode()+b'\0'+cr).hexdigest()!=child['commit_oid'] or hashlib.sha256(cr).hexdigest()!=child['commit_object_sha256'] or parents!=child['parents'] or len(parents)!=1 or not re.fullmatch('[0-9a-f]{40}',parents[0]):raise ValueError('parent derivation ambiguous or drifted')
    oid=parents[0]
    for repo in (root,root/'downloads/history-probe-73e35d6/fork',root/original.SLOT,root/previous.SLOT):
        if original.local(repo,'cat-file','--batch-check',stdin=(oid+'\n').encode())!=(oid+' missing\n').encode():raise ValueError('parent pre-existing or main/old isolation pollution')
    return d,sha,oid


def engine(root=ROOT):
    root=Path(root);d,sha,oid=context(root)
    spec=importlib.util.spec_from_file_location('_explicit_third_parent_engine',Path(original.__file__))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.PARENT=oid;module.CHILD=d['parent_snapshot']['commit_oid'];module.SLOT=SLOT
    def prepare(task_root=ROOT):
        current,digest,parent=context(task_root)
        if digest!=sha or parent!=oid:raise ValueError('changing context')
        return {'selected':current['selected_blob'],'path':current['path'],'snapshots':[current['parent_snapshot']]},digest
    module.prepare=prepare
    return module,d,sha,oid


def attempt(root=ROOT):
    module,_,_,_=engine(root);return module.attempt(root)


def audit(root=ROOT):
    module,d,sha,oid=engine(root);e=json.loads(module.audit(root))
    same=e['stop_reason']=='same_blob_in_parent'
    gain={'new_direct_edge_verified':e['parent_snapshot'] is not None,'unique_origin_resolved':False,'continued_layer_requests_recommended':False,'assessment':'third_same_blob_edge_only_marginal_information_gain_stop' if same else 'bounded_result_requires_separate_review_stop','fourth_layer_authorized':False}
    return canonical({'schema_version':'wayne.isolated-third-parent-boundary-evidence.v3','previous_evidence_sha256':sha,'engine_source_sha256':hashlib.sha256(Path(original.__file__).read_bytes()).hexdigest(),'scope':'one_direct_parent_of_verified_50ae1c_snapshot_only','derived_parent_oid':oid,'derivation_command':['git','-c','protocol.allow=never','cat-file','commit',d['parent_snapshot']['commit_oid']],'request_engine_evidence':e,'information_gain_review':gain,'relationship_status':'unresolved','unique_introducing_commit':None,'history_complete':False,'upstream_membership_verified':False,'carry_strategy_reviewed':False,'eligible':False,'source_lock_input':False,'build_gate_authorization':False,'hardware_tested':False})

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--attempt',action='store_true');p.add_argument('--output',type=Path);p.add_argument('--check',type=Path);a=p.parse_args()
    if a.attempt:attempt()
    raw=audit()
    if a.check:validate(a.check.read_bytes(),raw)
    elif a.output:_write_payload(raw,a.output)
    else:print(raw.decode(),end='')
