"""Read-only review of verified isolated blobs; no path/commit/carry inference."""
import hashlib,json,os,re,subprocess
from pathlib import Path
from shallow_patch_inventory import canonical
from check_source_update import pairs,reject_constant
from single_object_probe import validate as single_validate
from next_three_blob_probe import validate as chain_validate
ROOT=Path(__file__).resolve().parents[1]


def compose(bindings,objects):
    if set(bindings)!={'manifest','single','batch1','batch2'} or any(not isinstance(h,str) or not re.fullmatch('[0-9a-f]{64}',h) for h in bindings.values()):raise ValueError('invalid chain bindings')
    if len(objects)!=8:raise ValueError('eight objects required')
    oids=[o['oid'] for o in objects]
    if oids!=sorted(set(oids)):raise ValueError('duplicate/global order drift')
    items=[]
    for pos,o in enumerate(objects):
        if set(o)!={'oid','type','bytes','content_sha256','isolation_slot','bare','isolated_oid_only','main_present','fork_present'} or not re.fullmatch('[0-9a-f]{40}',o['oid']) or o['type']!='blob' or type(o['bytes']) is not int or o['bytes']<0 or not re.fullmatch('[0-9a-f]{64}',o['content_sha256']):raise ValueError('invalid verified facts')
        if o['main_present'] is not False or o['fork_present'] is not False or o['bare'] is not True or o['isolated_oid_only'] is not True:raise ValueError('main/fork pollution or isolation boundary violation')
        if o['isolation_slot']!=('single:0' if pos==0 else 'batch1:'+str(pos-1) if pos<5 else 'batch2:'+str(pos-5)):raise ValueError('isolation slot order drift')
        items.append({'global_index':pos,'verified_facts':o,'precise_path':None,'precise_commit':None,'candidate_history':None,'relationship_status':'unresolved','read_only_audit_candidate':True,'history_audit_ready':False,'source_lock_input':False,'blockers':['exact_path_commit_binding_unresolved','candidate_history_unavailable','history_incomplete','upstream_and_carry_unreviewed']})
    return canonical({'schema_version':'wayne.isolated-eight-blob-review.v1','input_sha256':bindings,'objects':items,'verified_payload_bytes':sum(o['bytes'] for o in objects),'history_complete':False,'upstream_membership_verified':False,'carry_strategy_reviewed':False,'eligible':False,'build_gate_authorization':False,'hardware_tested':False})


def validate(raw,expected):
    if len(raw)>65536:raise ValueError('review size limit')
    d=json.loads(raw.decode('utf-8'),object_pairs_hook=pairs,parse_constant=reject_constant);e=json.loads(expected)
    if type(d) is not dict or set(d)!=set(e) or canonical({k:d[k] for k in e})!=expected:raise ValueError('unknown fields/OID/hash/chain/scope/order/claims drift')
    return expected


def audit(root=ROOT):
    root=Path(root)
    def read(stage,file='batch.json'):return (root/'research'/stage/file).read_bytes()
    def digest(stage,key):return json.loads(read(stage,'checkpoint.json'))[key]
    m=read('missing-object-stage','manifest.json');ms=digest('missing-object-stage','manifest_sha256')
    s=read('single-object-stage','probe.json');ss=digest('single-object-stage','probe_sha256');b=read('four-blob-stage');bs=digest('four-blob-stage','batch_sha256');n=read('next-three-blob-stage');ns=digest('next-three-blob-stage','batch_sha256')
    if any(hashlib.sha256(raw).hexdigest()!=sha for raw,sha in ((m,ms),(s,ss),(b,bs),(n,ns))):raise ValueError('saved evidence hash drift')
    single_root=root/'downloads/single-blob-probe-20c9575';first_root=root/'downloads/four-blob-probe-b299a3c';second_root=root/'downloads/next-three-blob-probe-cee01fc'
    single_validate(s,m,ms,single_root);chain_validate(n,m,ms,s,ss,b,bs,first_root,second_root)
    sj,bj,nj=json.loads(s),json.loads(b),json.loads(n)['batch']
    entries=[(sj['selected_oid'],sj['object'],single_root,'single:0')]+[(i['oid'],i['object'],first_root/str(p),'batch1:'+str(p)) for p,i in enumerate(bj['items'])]+[(i['oid'],i['object'],second_root/str(p),'batch2:'+str(p)) for p,i in enumerate(nj['items'])]
    wanted=sorted({o['oid'] for i in json.loads(m)['items'] for o in i['missing_objects'] or []})[:8]
    if [i[0] for i in entries]!=wanted:raise ValueError('manifest first-eight binding drift')
    env=dict(os.environ,GIT_NO_LAZY_FETCH='1',GIT_TERMINAL_PROMPT='0')
    def git(repo,*args,stdin=None):
        r=subprocess.run(['git','-c','protocol.allow=never','-C',str(repo),*args],input=stdin,capture_output=True,env=env,timeout=5)
        if r.returncode:raise ValueError('local isolation/object evidence unavailable')
        return r.stdout
    def presence(repo):
        raw=git(repo,'cat-file','--batch-check',stdin=('\n'.join(wanted)+'\n').encode());lines=raw.decode().splitlines()
        if len(lines)!=8:raise ValueError('presence probe truncated')
        return {oid:line!=oid+' missing' for oid,line in zip(wanted,lines)}
    main=presence(root);fork=presence(root/'downloads/history-probe-73e35d6/fork');facts=[]
    for oid,obj,repo,slot in entries:
        if not repo.resolve().is_relative_to((root/'downloads').resolve()):raise ValueError('isolation directory escapes')
        bare=git(repo,'rev-parse','--is-bare-repository')==b'true\n';only=git(repo,'cat-file','--batch-all-objects','--batch-check=%(objectname)').splitlines()==[oid.encode()]
        facts.append({'oid':oid,**{k:obj[k] for k in ('type','bytes','content_sha256')},'isolation_slot':slot,'bare':bare,'isolated_oid_only':only,'main_present':main[oid],'fork_present':fork[oid]})
    return compose({'manifest':ms,'single':ss,'batch1':bs,'batch2':ns},facts)
