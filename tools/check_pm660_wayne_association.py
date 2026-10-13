"""Only selected PM660 blob versus recorded board sources; no network or other blobs."""
import hashlib,json,os,re,subprocess
from pathlib import Path
from check_source_update import pairs,reject_constant
from isolated_blob_attribution import validate,ROOT
from single_object_probe import verify_blob
from shallow_patch_inventory import canonical,safe_path
from export_dtb_consumers import _write_payload
OID='0509c0e69da28fa0693258ddc6bf249e349ba3da'
PM='arch/arm64/boot/dts/qcom/pm660.dtsi'
WAYNE='arch/arm64/boot/dts/qcom/sdm660-xiaomi-wayne.dts'


def audit(root=ROOT):
    root=Path(root);read=lambda p:(root/p).read_bytes()
    triage=read('research/isolated-blob-triage-stage/triage.json');tsha=hashlib.sha256(triage).hexdigest()
    if tsha!=json.loads(read('research/isolated-blob-triage-stage/checkpoint.json'))['triage_sha256']:raise ValueError('triage hash drift')
    t=json.loads(triage.decode(),object_pairs_hook=pairs,parse_constant=reject_constant)
    if t['selected_next_target']['oid']!=OID or t['selected_next_target']['path']!=PM:raise ValueError('selection drift')
    selected=[i for i in t['items'] if i['verified_facts']['oid']==OID]
    if len(selected)!=1:raise ValueError('selected OID duplicate/missing')
    item=selected[0];facts=item['verified_facts'];repo=root/'downloads/four-blob-probe-b299a3c/2'
    actual,why=verify_blob(repo,OID)
    if why!='success' or {k:actual[k] for k in ('type','bytes','content_sha256')}!={k:facts[k] for k in ('type','bytes','content_sha256')}:raise ValueError('selected blob type/OID/hash drift')
    env=dict(os.environ,GIT_NO_LAZY_FETCH='1',GIT_TERMINAL_PROMPT='0',GIT_NO_REPLACE_OBJECTS='1',GIT_LITERAL_PATHSPECS='1');commands=[]
    def git(r,*args,stdin=None):
        cmd=['git','-c','protocol.allow=never',*args];commands.append({'repository_scope':'selected_isolation' if r==repo else 'candidate_history' if r!=root else 'main','command':cmd})
        q=subprocess.run(cmd[:3]+['-C',str(r)]+cmd[3:],input=stdin,capture_output=True,env=env,timeout=5)
        if q.returncode or len(q.stdout)>4194304:raise ValueError('bounded local evidence missing')
        return q.stdout
    if git(repo,'rev-parse','--is-bare-repository')!=b'true\n' or (repo/'objects/info/alternates').exists() or git(repo,'cat-file','--batch-all-objects','--batch-check=%(objectname)')!= (OID+'\n').encode():raise ValueError('selected isolation drift')
    fork=root/'downloads/history-probe-73e35d6/fork'
    for r in (root,fork):
        if git(r,'cat-file','--batch-check',stdin=(OID+'\n').encode())!=(OID+' missing\n').encode():raise ValueError('main/fork blob pollution')
    witnesses=item['snapshot_path_witnesses']
    if not witnesses:raise ValueError('no selected snapshot path')
    for w in witnesses:
        if w['path']!=PM:raise ValueError('PM660 path mismatch')
        cr=git(fork,'cat-file','commit',w['snapshot_commit'])
        if hashlib.sha1(b'commit '+str(len(cr)).encode()+b'\0'+cr).hexdigest()!=w['snapshot_commit'] or hashlib.sha256(cr).hexdigest()!=w['commit_sha256']:raise ValueError('commit drift')
        trees=[l[5:].decode() for l in cr.split(b'\n\n',1)[0].splitlines() if l.startswith(b'tree ')]
        if trees!=[w['root_tree']]:raise ValueError('root tree drift')
        tree=w['root_tree'];parts=PM.split('/')
        if len(w['tree_chain'])!=len(parts):raise ValueError('tree chain length')
        for part,edge in zip(parts,w['tree_chain']):
            if edge['tree_oid']!=tree or edge['entry_name']!=part:raise ValueError('tree parent/path drift')
            raw=git(fork,'cat-file','tree',tree)
            if hashlib.sha1(b'tree '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=tree or hashlib.sha256(raw).hexdigest()!=edge['tree_sha256']:raise ValueError('tree OID/hash drift')
            row=git(fork,'ls-tree','-z',tree,'--',part)
            expect=(edge['mode']+' '+edge['type']+' '+edge['entry_oid']+'\t'+part+'\0').encode()
            if row!=expect or edge['type']!=('blob' if part==parts[-1] else 'tree'):raise ValueError('tree entry type/OID drift')
            tree=edge['entry_oid']
        if tree!=OID:raise ValueError('tree does not reach selected blob')
    sources=read('research/higher-kernel/source-evidence.json')
    for file,raw in [('research/isolated-blob-triage-stage/triage.json',triage),('research/higher-kernel/source-evidence.json',sources),('sources.lock.json',read('sources.lock.json'))]:
        if git(root,'show','1296e39:'+file)!=raw:raise ValueError('baseline source/lock/triage drift')
    s=json.loads(sources.decode(),object_pairs_hook=pairs,parse_constant=reject_constant)
    if s['repository']!='jakecommon/linux-sdm660-xiaomi-wayne' or not re.fullmatch('[0-9a-f]{40}',s['commit']):raise ValueError('recorded reference source drift')
    entries=[f for f in s['files'] if f['path']==WAYNE]
    if len(entries)!=1:raise ValueError('board reference not unique')
    entry=entries[0];board=read('research/higher-kernel/upstream/'+WAYNE)
    expected_url='https://raw.githubusercontent.com/'+s['repository']+'/'+s['commit']+'/'+WAYNE
    if entry['url']!=expected_url or entry['size']!=len(board) or hashlib.sha256(board).hexdigest()!=entry['sha256']:raise ValueError('board reference source hash/URL drift')
    includes=[]
    for n,line in enumerate(board.decode('utf-8').splitlines(),1):
        if line.lstrip().startswith('#include'):
            match=re.fullmatch(r'\s*#include\s+"([^"\n]+)"\s*',line)
            if not match:raise ValueError('unsupported include syntax')
            safe_path(match[1]);includes.append({'line':n,'directive':line,'included_relative_path':match[1]})
    if [i['included_relative_path'] for i in includes]!=['sdm660-xiaomi-jasmine.dts']:raise ValueError('recorded clone-only board reference changed; re-review needed')
    return canonical({'schema_version':'wayne.pm660-board-association.v1','input_sha256':{'triage':tsha,'source_evidence':hashlib.sha256(sources).hexdigest(),'sources_lock':hashlib.sha256(read('sources.lock.json')).hexdigest()},'selected_candidate_blob':{'oid':OID,**actual,'snapshot_path_witnesses':witnesses,'scope':'6.6_candidate_historical_snapshot_not_actual_wayne_board'},'recorded_board_reference':{'repository':s['repository'],'declared_commit':s['commit'],'url':entry['url'],'path':WAYNE,'bytes':len(board),'sha256':entry['sha256'],'computed_blob_oid':hashlib.sha1(b'blob '+str(len(board)).encode()+b'\0'+board).hexdigest(),'commit_tree_membership_verified':False,'reference_kind':'third_party_jasmine_inherited_wayne_named_source','includes':includes,'physical_source_authenticated':False},'include_chain':{'status':'not_closed','verified_real_wayne_edges':[],'reference_only_edges':includes,'breakpoint':'third_party_entry_includes_jasmine_without_independent_actual_wayne_board_evidence','do_not_join_different_repository_or_commit_files':True},'source_request_decision':{'exact_reference_source_recorded':True,'admissible_actual_wayne_board_source_established':False,'network_requests':0,'reason':'recorded_third_party_clone_reference_is_not_actual_wayne_baseline'},'target_association':'unresolved','commands':commands,'other_blobs_processed':False,'first_blob_history_resumed':False,'history_complete':False,'upstream_membership_verified':False,'carry_strategy_reviewed':False,'eligible':False,'hardware_tested':False,'build_gate_authorization':False,'source_lock_input':False})

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);p.add_argument('--check',type=Path);a=p.parse_args();raw=audit()
    if a.check:validate(a.check.read_bytes(),raw)
    elif a.output:_write_payload(raw,a.output)
    else:print(raw.decode(),end='')
