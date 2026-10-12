"""Fixed next-four isolated probes; stop on first failure or cumulative verified payload cap."""
import hashlib,json,re
from pathlib import Path
from check_source_update import pairs,reject_constant
from shallow_patch_inventory import canonical
from single_object_probe import attempt,verify_blob,selection,URL,REASONS,LIMIT
CAP=2*1024*1024


def plan(manifest,msha,previous,psha,synthetic=False):
    first=selection(manifest,msha)
    if not re.fullmatch('[0-9a-f]{64}',psha) or hashlib.sha256(previous).hexdigest()!=psha:raise ValueError('single-probe binding drift')
    p=json.loads(previous.decode(),object_pairs_hook=pairs,parse_constant=reject_constant)
    if p.get('schema_version')!='wayne.single-blob-probe.v1' or p['result']!='success' or p['selected_oid']!=first or p['manifest_sha256']!=msha or p['object']['type']!='blob' or p['object']['actual_oid']!=first:raise ValueError('previous verified probe mismatch')
    expected_url='synthetic-local-git-service' if synthetic else URL
    if p['source_url']!=expected_url or p['evidence_scope']!=('synthetic' if synthetic else 'actual_remote_probe'):raise ValueError('source/scope drift')
    obj=p['object']
    if set(obj)!={'type','bytes','actual_oid','content_sha256'} or type(obj['bytes']) is not int or obj['bytes']<0 or not re.fullmatch('[0-9a-f]{64}',obj['content_sha256']):raise ValueError('previous object metadata')
    m=json.loads(manifest);oids=sorted({o['oid'] for i in m['items'] for o in i['missing_objects'] or [] if o['oid']!=first})
    if len(oids)<4:raise ValueError('fewer than four next objects')
    return oids[:4],obj['bytes']


def run(manifest,msha,previous,psha,root,synthetic=False,url=None,timeout=60):
    oids,initial=plan(manifest,msha,previous,psha,synthetic)
    if not synthetic and (url not in (None,URL) or timeout!=60):raise ValueError('remote/timeout drift')
    root=Path(root);root.mkdir(parents=True,exist_ok=False)
    items=[];total=initial;batch=0;requests=0;stop=None
    for pos,oid in enumerate(oids):
        if stop is None and total>=CAP:stop='payload_limit'
        if stop:
            items.append({'position':pos,'oid':oid,'request_count':0,'result':'not_attempted','object':None,'probe':None});continue
        repo=root/str(pos)
        raw=attempt(repo,url if synthetic else URL,oid,msha,timeout=timeout,synthetic=synthetic)
        child=json.loads(raw);requests+=1
        items.append({'position':pos,'oid':oid,'request_count':1,'result':child['result'],'object':child['object'],'probe':child})
        if child['result']!='success':stop='object_failure'
        else:batch+=child['object']['bytes'];total+=child['object']['bytes']
    return canonical({'schema_version':'wayne.four-blob-batch.v1','evidence_scope':'synthetic' if synthetic else 'actual_remote_probe','manifest_sha256':msha,'single_probe_sha256':psha,'source_url':'synthetic-local-git-service' if synthetic else URL,'selected_oids':oids,'initial_verified_payload_bytes':initial,'payload_limit_bytes':CAP,'batch_verified_payload_bytes':batch,'cumulative_verified_payload_bytes':total,'request_count':requests,'stop_reason':stop or 'completed','items':items,'history_complete':False,'upstream_membership_verified':False,'carry_strategy_reviewed':False,'eligible':False,'hardware_tested':False})


def validate(raw,manifest,msha,previous,psha,root,synthetic=False):
    if len(raw)>262144:raise ValueError('batch evidence size limit')
    d=json.loads(raw.decode(),object_pairs_hook=pairs,parse_constant=reject_constant)
    keys={'schema_version','evidence_scope','manifest_sha256','single_probe_sha256','source_url','selected_oids','initial_verified_payload_bytes','payload_limit_bytes','batch_verified_payload_bytes','cumulative_verified_payload_bytes','request_count','stop_reason','items','history_complete','upstream_membership_verified','carry_strategy_reviewed','eligible','hardware_tested'}
    oids,initial=plan(manifest,msha,previous,psha,synthetic)
    if type(d) is not dict or set(d)!=keys or d['schema_version']!='wayne.four-blob-batch.v1':raise ValueError('unknown fields/schema')
    if d['manifest_sha256']!=msha or d['single_probe_sha256']!=psha or d['selected_oids']!=oids or d['source_url']!=('synthetic-local-git-service' if synthetic else URL) or d['evidence_scope']!=('synthetic' if synthetic else 'actual_remote_probe'):raise ValueError('binding/selection/source/scope drift')
    if d['payload_limit_bytes']!=CAP or d['initial_verified_payload_bytes']!=initial or len(d['items'])!=4 or any(d[k] is not False for k in ('history_complete','upstream_membership_verified','carry_strategy_reviewed','eligible','hardware_tested')):raise ValueError('limit/claims drift')
    for field in ('initial_verified_payload_bytes','payload_limit_bytes','batch_verified_payload_bytes','cumulative_verified_payload_bytes','request_count'):
        if type(d[field]) is not int or d[field]<0:raise ValueError('nonnegative integer counter required')
    total=initial;batch=requests=0;stop=None
    for pos,(item,oid) in enumerate(zip(d['items'],oids)):
        if type(item) is not dict or set(item)!={'position','oid','request_count','result','object','probe'} or type(item['position']) is not int or item['position']!=pos or item['oid']!=oid:raise ValueError('duplicate/OID/order/item fields drift')
        if stop is None and total>=CAP:stop='payload_limit'
        if stop:
            if type(item['request_count']) is not int or item['request_count']!=0 or item['result']!='not_attempted' or item['object'] is not None or item['probe'] is not None:raise ValueError('request/metadata after stop')
            continue
        if type(item['request_count']) is not int or item['request_count']!=1 or item['result'] not in REASONS or type(item['probe']) is not dict:raise ValueError('invalid attempted result')
        child=item['probe'];requests+=1
        childkeys={'schema_version','evidence_scope','manifest_sha256','source_url','selection_index','selected_oid','request_method','command','hard_timeout_seconds','byte_limit','exit_code','result','object','stdout_sha256','stderr_sha256','history_complete','upstream_membership_verified','carry_strategy_reviewed','eligible','hardware_tested'}
        if set(child)!=childkeys or child['schema_version']!='wayne.single-blob-probe.v1' or child['selected_oid']!=oid or child['manifest_sha256']!=msha or child['result']!=item['result'] or canonical(child['object'])!=canonical(item['object']):raise ValueError('child evidence binding drift')
        expected_cmd=['git','-c','gc.auto=0','-c','pack.threads=1','-c','http.followRedirects=false','-C','<isolated-object-db>','fetch','--no-tags','--no-recurse-submodules','--no-write-fetch-head','<synthetic-local-service>' if synthetic else URL,oid]
        if child['command']!=expected_cmd or child['source_url']!=d['source_url'] or child['evidence_scope']!=d['evidence_scope'] or (not synthetic and child['hard_timeout_seconds']!=60):raise ValueError('request policy drift')
        if type(child['selection_index']) is not int or child['selection_index']!=0 or child['request_method']!='single_exact_oid_fetch_no_fallback' or child['byte_limit']!=LIMIT or type(child['exit_code']) is not int or any(child[k] is not False for k in ('history_complete','upstream_membership_verified','carry_strategy_reviewed','eligible','hardware_tested')):raise ValueError('child policy/claims drift')
        for field in ('stdout_sha256','stderr_sha256'):
            if not isinstance(child[field],str) or not re.fullmatch('[0-9a-f]{64}',child[field]):raise ValueError('child hash malformed')
            file=Path(root)/str(pos)/('probe.stdout' if field=='stdout_sha256' else 'probe.stderr')
            if file.exists() and hashlib.sha256(file.read_bytes()).hexdigest()!=child[field]:raise ValueError('response hash drift')
        if item['result']=='success':
            actual,reason=verify_blob(Path(root)/str(pos),oid)
            if child['exit_code']!=0 or reason!='success' or canonical(item['object'])!=canonical(actual):raise ValueError('successful object/type/OID/hash mismatch')
            batch+=actual['bytes'];total+=actual['bytes']
        else:
            if item['object'] is not None:raise ValueError('failed item carries metadata')
            stop='object_failure'
    if d['request_count']!=requests or d['batch_verified_payload_bytes']!=batch or d['cumulative_verified_payload_bytes']!=total or d['stop_reason']!=(stop or 'completed'):raise ValueError('payload/count/stop contradiction')
    return canonical(d)
