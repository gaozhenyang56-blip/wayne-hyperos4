"""One exact depth-one, blob-filtered parent request; isolated, never a build input."""
import hashlib,json,os,re,signal,subprocess,time
from pathlib import Path
from isolated_blob_history_boundary import audit as boundary_audit,validate,ROOT
from shallow_patch_inventory import canonical
from check_source_update import pairs,reject_constant
from export_dtb_consumers import _write_payload
PARENT='6fbaeffc3a92b4a32b8e320e486cf644ff30d240'
CHILD='71c631a9fb211df4ea5a59ac68a310c5854f07f1'
URL='https://github.com/sdm660-mainline/linux.git'
SLOT='downloads/parent-commit-probe-a091e75'
LIMIT=8*1024*1024
ENV=dict(os.environ,GIT_NO_LAZY_FETCH='1',GIT_TERMINAL_PROMPT='0',GIT_NO_REPLACE_OBJECTS='1',GIT_LFS_SKIP_SMUDGE='1')
REASONS=('success','timeout','volume_limit','auth_required','bot_challenge','filter_unsupported','server_rejected','response_anomaly')

def command():
    return ['git','-c','gc.auto=0','-c','pack.threads=1','-c','http.followRedirects=false','-c','credential.helper=','-C','<isolated-object-db>','fetch','--depth=1','--filter=blob:none','--no-tags','--no-recurse-submodules','--no-write-fetch-head',URL,PARENT]

def local(repo,*args,stdin=None):
    r=subprocess.run(['git','-c','protocol.allow=never','-C',str(repo),*args],input=stdin,capture_output=True,env=ENV,timeout=5)
    if r.returncode:raise ValueError('local evidence unavailable')
    if len(r.stdout)>4*1024*1024:raise ValueError('metadata output too large')
    return r.stdout

def prepare(root=ROOT):
    root=Path(root);stage=root/'research/isolated-blob-history-boundary-stage';raw=(stage/'boundary.json').read_bytes()
    sha=json.loads((stage/'checkpoint.json').read_bytes())['boundary_sha256']
    if hashlib.sha256(raw).hexdigest()!=sha:raise ValueError('boundary hash drift')
    validate(raw,boundary_audit(root));b=json.loads(raw);s=b['snapshots'][-1]
    if b['fixed_fork_url']!=URL or s['commit_oid']!=CHILD or [p['oid'] for p in s['parents']]!=[PARENT]:raise ValueError('parent/source drift')
    for repo in (root,root/'downloads/history-probe-73e35d6/fork'):
        if local(repo,'cat-file','--batch-check',stdin=(PARENT+'\n').encode())!=(PARENT+' missing\n').encode():raise ValueError('main/fork parent pollution or pre-existing object')
    return b,sha

def reason_from_error(error):
    error=error.lower()
    if any(x in error for x in (b'captcha',b'bot check',b'verify you are human')):return 'bot_challenge'
    if any(x in error for x in (b'authentication failed',b'could not read username',b'username for')):return 'auth_required'
    if any(x in error for x in (b'filtering not recognized',b'filtering not supported')):return 'filter_unsupported'
    return None

def attempt(root=ROOT):
    root=Path(root);_,sha=prepare(root);repo=root/SLOT
    repo.mkdir(parents=True,exist_ok=False) # existing attempt is never retried
    subprocess.run(['git','init','--bare','-q',str(repo)],check=True)
    cmd=command();cmd[cmd.index('<isolated-object-db>')]=str(repo)
    why=None
    with (repo/'request.stdout').open('wb') as out,(repo/'request.stderr').open('wb') as err:
        p=subprocess.Popen(cmd,stdout=out,stderr=err,env=ENV,start_new_session=True);deadline=time.monotonic()+60
        while p.poll() is None:
            why=reason_from_error((repo/'request.stderr').read_bytes())
            size=sum(f.stat().st_size for f in (repo/'objects').rglob('*') if f.is_file())
            if time.monotonic()>=deadline:why='timeout'
            elif size>LIMIT:why='volume_limit'
            elif (repo/'request.stderr').stat().st_size+(repo/'request.stdout').stat().st_size>1048576:why='response_anomaly'
            if why:
                try:os.killpg(p.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                break
            time.sleep(.05)
        code=p.wait()
    size=sum(f.stat().st_size for f in (repo/'objects').rglob('*') if f.is_file())
    why=why or reason_from_error((repo/'request.stderr').read_bytes()) or ('volume_limit' if size>LIMIT else 'success' if code==0 else 'server_rejected')
    d={'schema_version':'wayne.isolated-parent-request.v1','boundary_sha256':sha,'source_url':URL,'requested_oid':PARENT,'request_count':1,'command':command(),'hard_timeout_seconds':60,'object_store_limit_bytes':LIMIT,'object_store_bytes':size,'exit_code':code,'result':why,'stdout_sha256':hashlib.sha256((repo/'request.stdout').read_bytes()).hexdigest(),'stderr_sha256':hashlib.sha256((repo/'request.stderr').read_bytes()).hexdigest()}
    _write_payload(canonical(d),repo/'request.json')
    return d

def audit(root=ROOT):
    root=Path(root);base,sha=prepare(root);repo=root/SLOT;raw=(repo/'request.json').read_bytes()
    request=json.loads(raw.decode(),object_pairs_hook=pairs,parse_constant=reject_constant)
    keys={'schema_version','boundary_sha256','source_url','requested_oid','request_count','command','hard_timeout_seconds','object_store_limit_bytes','object_store_bytes','exit_code','result','stdout_sha256','stderr_sha256'}
    if set(request)!=keys or request['schema_version']!='wayne.isolated-parent-request.v1' or request['boundary_sha256']!=sha or request['source_url']!=URL or request['requested_oid']!=PARENT or request['request_count']!=1 or type(request['request_count']) is not int or request['command']!=command() or request['hard_timeout_seconds']!=60 or request['object_store_limit_bytes']!=LIMIT or type(request['exit_code']) is not int or request['result'] not in REASONS:raise ValueError('request schema/policy drift')
    size=sum(f.stat().st_size for f in (repo/'objects').rglob('*') if f.is_file())
    if type(request['object_store_bytes']) is not int or request['object_store_bytes']!=size:raise ValueError('object-store bytes drift')
    for name in ('stdout','stderr'):
        if hashlib.sha256((repo/('request.'+name)).read_bytes()).hexdigest()!=request[name+'_sha256']:raise ValueError('response hash drift')
    if local(repo,'rev-parse','--is-bare-repository')!=b'true\n' or (repo/'objects/info/alternates').exists():raise ValueError('isolation violation')
    commands=[];parent=None;comparison=None;status='unresolved';stop=request['result']
    files=[{'name':f.relative_to(repo/'objects').as_posix(),'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in sorted((repo/'objects').rglob('*')) if f.is_file()]
    def git(*args):
        commands.append(['git','-c','protocol.allow=never',*args]);return local(repo,*args)
    def obj(kind,oid):
        if not re.fullmatch('[0-9a-f]{40}',oid):raise ValueError('invalid object OID')
        if git('cat-file','-t',oid)!=(kind+'\n').encode():raise ValueError('object type mismatch')
        raw=git('cat-file',kind,oid)
        if hashlib.sha1((kind+' '+str(len(raw))+'\0').encode()+raw).hexdigest()!=oid:raise ValueError('object hash mismatch')
        return raw
    if request['result']=='success':
        if request['exit_code']!=0 or size>LIMIT:raise ValueError('success contradicts exit or volume')
        all_objects=git('cat-file','--batch-all-objects','--batch-check=%(objectname) %(objecttype)').decode().splitlines()
        commits=[r.split()[0] for r in all_objects if r.split()[1]=='commit']
        if commits!=[PARENT] or any(r.split()[1] not in ('commit','tree') for r in all_objects):raise ValueError('unexpected history/blob expansion')
        if (repo/'shallow').read_text().splitlines()!=[PARENT]:raise ValueError('depth-one boundary drift')
        cr=obj('commit',PARENT);header=cr.split(b'\n\n',1)[0].splitlines();trees=[r[5:].decode() for r in header if r.startswith(b'tree ')];parents=[r[7:].decode() for r in header if r.startswith(b'parent ')]
        if len(trees)!=1:raise ValueError('root tree ambiguous')
        tree=trees[0];chain=[];entry=None;path=base['path'];absence=None
        for pos,part in enumerate(path.split('/')):
            tr=obj('tree',tree);rows=[r for r in git('ls-tree','-z',tree,'--',part).split(b'\0') if r]
            if not rows:
                absence={'tree_oid':tree,'tree_sha256':hashlib.sha256(tr).hexdigest(),'missing_component':part,'component_index':pos};break
            if len(rows)!=1:raise ValueError('duplicate path entry')
            meta,name=rows[0].split(b'\t',1);mode,kind,target=meta.decode().split()
            if name.decode()!=part or not re.fullmatch('[0-9a-f]{40}',target):raise ValueError('path/OID drift')
            chain.append({'tree_oid':tree,'tree_sha256':hashlib.sha256(tr).hexdigest(),'entry_name':part,'mode':mode,'type':kind,'entry_oid':target})
            if pos==len(path.split('/'))-1:
                if kind!='blob':raise ValueError('path type mismatch')
                entry=target
            elif kind!='tree':raise ValueError('path component not tree')
            tree=target
        parent={'commit_oid':PARENT,'type':'commit','bytes':len(cr),'commit_object_sha256':hashlib.sha256(cr).hexdigest(),'root_tree_oid':trees[0],'parents':parents,'path':path,'path_blob_oid':entry,'absence_proof':absence,'tree_chain':chain}
        comparison={'child_commit':CHILD,'parent_commit':PARENT,'child_path_blob_oid':base['selected']['oid'],'parent_path_blob_oid':entry,'same_path_object':entry==base['selected']['oid']}
        stop='same_blob_in_parent' if comparison['same_path_object'] else 'local_path_introduction_transition'
    return canonical({'schema_version':'wayne.isolated-parent-boundary-evidence.v1','boundary_sha256':sha,'request_sha256':hashlib.sha256(raw).hexdigest(),'request':request,'selected_blob':base['selected'],'path':base['path'],'child_snapshot':base['snapshots'][-1],'parent_snapshot':parent,'comparison':comparison,'object_files':files,'commands':commands,'stop_reason':stop,'relationship_status':status,'nearest_local_introduction_boundary':CHILD if stop=='local_path_introduction_transition' else None,'unique_introducing_commit':None,'history_complete':False,'upstream_membership_verified':False,'carry_strategy_reviewed':False,'eligible':False,'source_lock_input':False,'build_gate_authorization':False,'hardware_tested':False})

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--attempt',action='store_true');p.add_argument('--output',type=Path);p.add_argument('--check',type=Path);a=p.parse_args()
    if a.attempt:attempt()
    raw=audit()
    if a.check:validate(a.check.read_bytes(),raw)
    elif a.output:_write_payload(raw,a.output)
    else:print(raw.decode(),end='')
