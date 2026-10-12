"""Incremental evidence envelope; reuse existing batch request/validation engine."""
import hashlib,json,re
from pathlib import Path
from check_source_update import pairs,reject_constant
from shallow_patch_inventory import canonical
from four_blob_batch_probe import plan as old_plan,validate as old_validate,_run_selected,_validate_selected
CAP=512*1024
SCHEMA='wayne.incremental-blob-batch.v1'
BATCH_SCHEMA='wayne.isolated-blob-batch.v2'


def chain_plan(manifest,msha,single,ssha,previous,bsha,previous_root,synthetic=False):
    if not isinstance(bsha,str) or not re.fullmatch('[0-9a-f]{64}',bsha) or hashlib.sha256(previous).hexdigest()!=bsha:raise ValueError('previous batch hash drift')
    old_validate(previous,manifest,msha,single,ssha,previous_root,synthetic)
    p=json.loads(previous);first_four,initial=old_plan(manifest,msha,single,ssha,synthetic)
    if p['stop_reason']!='completed' or p['request_count']!=4 or any(i['result']!='success' for i in p['items']):raise ValueError('previous four not completely verified')
    first=json.loads(single)['selected_oid'];m=json.loads(manifest)
    ordered=sorted({o['oid'] for i in m['items'] for o in i['missing_objects'] or []})
    if ordered[:5]!=[first,*first_four]:raise ValueError('previous global prefix drift')
    selected=ordered[5:8]
    if len(selected)!=3:raise ValueError('three remaining OIDs required')
    return selected,p['cumulative_verified_payload_bytes']


def _envelope(msha,ssha,bsha,batch):
    return canonical({'schema_version':SCHEMA,'manifest_sha256':msha,'single_probe_sha256':ssha,'previous_batch_sha256':bsha,'global_selection_indices':[5,6,7],'payload_threshold_basis':'this_batch_verified_payload','batch':json.loads(batch),'history_complete':False,'upstream_membership_verified':False,'carry_strategy_reviewed':False,'eligible':False,'hardware_tested':False})


def run(manifest,msha,single,ssha,previous,bsha,previous_root,root,synthetic=False,url=None,timeout=60):
    oids,initial=chain_plan(manifest,msha,single,ssha,previous,bsha,previous_root,synthetic)
    batch=_run_selected(msha,ssha,oids,initial,root,CAP,False,BATCH_SCHEMA,synthetic,url,timeout)
    return _envelope(msha,ssha,bsha,batch)


def validate(raw,manifest,msha,single,ssha,previous,bsha,previous_root,root,synthetic=False):
    if len(raw)>262144:raise ValueError('incremental evidence size limit')
    d=json.loads(raw.decode(),object_pairs_hook=pairs,parse_constant=reject_constant)
    oids,initial=chain_plan(manifest,msha,single,ssha,previous,bsha,previous_root,synthetic)
    expected_keys={'schema_version','manifest_sha256','single_probe_sha256','previous_batch_sha256','global_selection_indices','payload_threshold_basis','batch','history_complete','upstream_membership_verified','carry_strategy_reviewed','eligible','hardware_tested'}
    if type(d) is not dict or set(d)!=expected_keys:raise ValueError('unknown/absent envelope fields')
    batch=_validate_selected(canonical(d['batch']),msha,ssha,root,oids,initial,CAP,False,BATCH_SCHEMA,synthetic)
    expected=json.loads(_envelope(msha,ssha,bsha,batch))
    if canonical({k:d[k] for k in expected})!=canonical(expected):raise ValueError('chain/global order/threshold/claims drift')
    return canonical(expected)
