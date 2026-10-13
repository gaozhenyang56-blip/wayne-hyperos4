"""Offline snapshot-path triage; target linkage remains evidence-limited."""
import hashlib,json,os,subprocess
from pathlib import Path
from isolated_blob_review import audit as review_audit
from isolated_third_parent_probe import audit as third_audit
from isolated_blob_attribution import validate,ROOT
from shallow_patch_inventory import canonical,safe_path
from export_dtb_consumers import _write_payload
FOREIGN={'arch/arm64/boot/dts/qcom/sm8450-sony-xperia-nagara.dtsi','arch/arm64/boot/dts/qcom/sm8450.dtsi','arch/arm64/boot/dts/qcom/sdm845.dtsi','arch/arm64/boot/dts/qcom/msm8996-xiaomi-common.dtsi','arch/arm64/boot/dts/qcom/sdm636-xiaomi-tulip.dts'}
PM='arch/arm64/boot/dts/qcom/pm660.dtsi'


def audit(root=ROOT):
    root=Path(root);read=lambda p:(root/p).read_bytes();review=read('research/isolated-blob-review-stage/review.json');validate(review,review_audit(root))
    third=read('research/isolated-third-parent-stage/evidence.json')
    if hashlib.sha256(third).hexdigest()!=json.loads(read('research/isolated-third-parent-stage/checkpoint.json'))['evidence_sha256']:raise ValueError('third-layer hash drift')
    validate(third,third_audit(root))
    manifest=read('research/missing-object-stage/manifest.json');inventory=read('research/shallow-inventory-stage/inventory.json');inv=json.loads(inventory);index={r['oid']:r for r in inv['records']}
    env=dict(os.environ,GIT_NO_LAZY_FETCH='1',GIT_TERMINAL_PROMPT='0',GIT_NO_REPLACE_OBJECTS='1',GIT_LITERAL_PATHSPECS='1');commands=[];cache={}
    def git(*args):
        cmd=['git','-c','protocol.allow=never',*args]
        if tuple(args) not in cache:
            commands.append(cmd);r=subprocess.run(cmd[:3]+['-C',str(root/'downloads/history-probe-73e35d6/fork')]+cmd[3:],env=env,capture_output=True,timeout=5)
            if r.returncode or len(r.stdout)>4194304:raise ValueError('bounded local metadata unavailable')
            cache[tuple(args)]=r.stdout
        return cache[tuple(args)]
    def obj(kind,oid):
        raw=git('cat-file',kind,oid)
        if hashlib.sha1((kind+' '+str(len(raw))+'\0').encode()+raw).hexdigest()!=oid:raise ValueError('object hash drift')
        return raw
    facts=[i['verified_facts'] for i in json.loads(review)['objects']];wanted={f['oid'] for f in facts};found={oid:{} for oid in wanted}
    for item in json.loads(manifest)['items']:
        matching=wanted & {o['oid'] for o in item['missing_objects'] or []}
        if not matching:continue
        r=index[item['commit_oid']]
        if not r['path_evidence_complete'] or len(r['parents'])!=1:raise ValueError('ambiguous inventory context')
        for commit in [r['oid'],r['parents'][0]['oid']]:
            cr=obj('commit',commit)
            if hashlib.sha256(cr).hexdigest()!=index[commit]['commit_object_sha256']:raise ValueError('inventory commit hash drift')
            root_trees=[line[5:].decode() for line in cr.split(b'\n\n',1)[0].splitlines() if line.startswith(b'tree ')]
            if len(root_trees)!=1:raise ValueError('root tree ambiguous')
            for entry in filter(None,git('ls-tree','-r','-z',commit,'--',*r['changed_paths']).split(b'\0')):
                meta,p=entry.split(b'\t',1);mode,kind,oid=meta.decode().split();path=p.decode();safe_path(path)
                if oid not in matching:continue
                if kind!='blob':raise ValueError('selected OID not blob entry')
                tree=root_trees[0];chain=[];parts=path.split('/')
                for n,part in enumerate(parts):
                    tr=obj('tree',tree);rows=[x for x in git('ls-tree','-z',tree,'--',part).split(b'\0') if x]
                    if len(rows)!=1:raise ValueError('nonunique path component')
                    m,name=rows[0].split(b'\t',1);em,ek,eo=m.decode().split()
                    if name.decode()!=part or (ek!='tree' if n<len(parts)-1 else ek!='blob' or eo!=oid):raise ValueError('tree relation drift')
                    chain.append({'tree_oid':tree,'tree_sha256':hashlib.sha256(tr).hexdigest(),'entry_name':part,'mode':em,'type':ek,'entry_oid':eo});tree=eo
                found[oid][(commit,path)]={'snapshot_commit':commit,'path':path,'commit_sha256':hashlib.sha256(cr).hexdigest(),'root_tree':root_trees[0],'tree_chain':chain}
    experimental_paths=['config/sdm660-xiaomi-wayne-6.6.dts','research/higher-kernel/6.6/arch/arm64/boot/dts/qcom/sdm660-xiaomi-jasmine.dts'];dep=[]
    for p,token in zip(experimental_paths,('#include "sdm660-xiaomi-jasmine.dts"','#include "pm660.dtsi"')):
        raw=read(p);lines=[n+1 for n,s in enumerate(raw.decode().splitlines()) if s.strip()==token]
        if len(lines)!=1:raise ValueError('experimental include evidence drift')
        dep.append({'path':p,'sha256':hashlib.sha256(raw).hexdigest(),'line':lines[0],'text':token,'evidence_scope':'unverified_jasmine_inherited_experiment_only'})
    items=[]
    for i,f in enumerate(facts):
        witnesses=[found[f['oid']][k] for k in sorted(found[f['oid']])];paths=sorted({w['path'] for w in witnesses});first=i==0;pm=paths==[PM];foreign=bool(paths) and all(p in FOREIGN for p in paths)
        bucket='other_soc_or_device_path' if foreign else 'insufficient_target_evidence'
        rank=3 if first else 0 if pm else 2 if foreign else 1
        items.append({'global_index':i,'verified_facts':f,'snapshot_path_witnesses':witnesses,'classification':bucket,'target_relevance_supported':False,'potential_link':'unverified_experimental_include_dependency' if pm else 'foreign_path_occurrence_only' if foreign else 'generic_kernel_path_no_device_link','dependency_evidence':dep if pm else [],'source_status':'snapshot_occurrence_only_not_unique_origin','next_step_kind':'stop_first_blob_parent_tracking' if first else 'verify_independent_wayne_pmic_link' if pm else 'generic_relevance_gap_review' if not foreign else 'defer_foreign_path','expected_information_gain':'one_new_target_link_if_real_evidence_available' if pm else 'target_link_unknown_no_gain_estimate','estimated_gain_numeric':None,'cost_basis':{'network_requests_this_stage':0,'existing_blob_bytes_to_read':f['bytes'],'future_device_evidence_available':False,'future_runtime_estimate':None},'priority_key':[rank,f['bytes'],f['oid']],'history_complete':False,'upstream_membership_verified':False,'carry_strategy_reviewed':False,'eligible':False})
    queue=sorted(items,key=lambda x:x['priority_key']);candidate=queue[0]
    if candidate['potential_link']!='unverified_experimental_include_dependency':raise ValueError('insufficient basis for single conditional target')
    target={'oid':candidate['verified_facts']['oid'],'path':PM,'status':'conditional_evidence_review_only_not_device_adaptation','blocked_reason':'actual_wayne_board_evidence_missing','scope':'independent_wayne_pmic_dependency_evidence_not_parent_history','minimum_evidence':['verified_existing_pm660_blob_and_snapshot_chain','actual_wayne_DTB_or_authenticated_board_source_with_explicit_pmic_relationship','existing_fail_fast_identity_and_source_evidence_checks'],'stop_conditions':['no_actual_wayne_board_evidence_keep_unresolved','jasmine_only_or_foreign_source_do_not_substitute','ambiguous_pmic_relationship_stop','no_network_or_history_expansion_without_separate_scope'],'network_request_planned':False,'executed_this_stage':False}
    return canonical({'schema_version':'wayne.isolated-eight-blob-triage.v1','input_sha256':{k:hashlib.sha256(v).hexdigest() for k,v in [('review',review),('third_parent',third),('manifest',manifest),('inventory',inventory)]},'rule_version':'explicit_snapshot_paths_experiment_dependency_then_generic_then_foreign_then_stopped_first_v1','ranking_scope':'conditional_offline_review_priority_not_hardware_relevance_or_numeric_gain','items':items,'priority_oids':[x['verified_facts']['oid'] for x in queue],'selected_next_target':target,'classification_counts':{k:sum(i['classification']==k for i in items) for k in ('target_relevance_supported','other_soc_or_device_path','insufficient_target_evidence')},'first_blob_parent_tracking_stopped':True,'fourth_layer_requested':False,'network_requests':0,'commands':commands,'history_complete':False,'upstream_membership_verified':False,'carry_strategy_reviewed':False,'eligible':False,'hardware_tested':False,'build_gate_authorization':False,'source_lock_input':False})

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);p.add_argument('--check',type=Path);a=p.parse_args();raw=audit()
    if a.check:validate(a.check.read_bytes(),raw)
    elif a.output:_write_payload(raw,a.output)
    else:print(raw.decode(),end='')
