#!/usr/bin/env python3
"""One isolated exact-blob attempt; no source integration or authentication claim."""
import hashlib,json,os,re,signal,subprocess,time
from pathlib import Path
from check_source_update import pairs,reject_constant
from shallow_patch_inventory import canonical
URL='https://github.com/sdm660-mainline/linux.git'
LIMIT=16*1024*1024
REASONS=('success','server_rejected','timeout','auth_required','filter_unsupported','bot_challenge','response_anomaly','volume_limit','type_error','oid_mismatch','local_tool_error')


def selection(raw,expected):
    if len(raw)>16*1024*1024 or not re.fullmatch('[0-9a-f]{64}',expected) or hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('manifest binding drift')
    data=json.loads(raw.decode('utf-8'),object_pairs_hook=pairs,parse_constant=reject_constant)
    if data.get('schema_version')!='wayne.missing-object-acquisition.v1':raise ValueError('manifest schema')
    objects=[]
    for item in data['items']:
        for obj in item['missing_objects'] or []:
            if obj['type']!='blob' or obj['presence']!='missing' or not re.fullmatch('[0-9a-f]{40}',obj['oid']):raise ValueError('invalid selected object')
            objects.append(obj['oid'])
    ordered=sorted(set(objects))
    if not ordered:raise ValueError('no missing blobs')
    return ordered[0]


def verify_blob(repo,oid):
    env=dict(os.environ,GIT_NO_LAZY_FETCH='1',GIT_TERMINAL_PROMPT='0')
    def git(*a):return subprocess.run(['git','-c','protocol.allow=never','-C',str(repo),*a],capture_output=True,env=env,timeout=5)
    r=git('cat-file','-t',oid)
    if r.returncode:return None,'response_anomaly'
    if r.stdout!=b'blob\n':return None,'type_error'
    size=git('cat-file','-s',oid)
    if size.returncode or not size.stdout.strip().isdigit():return None,'response_anomaly'
    count=int(size.stdout)
    if count>LIMIT:return None,'volume_limit'
    blob=git('cat-file','blob',oid)
    if blob.returncode or len(blob.stdout)!=count:return None,'response_anomaly'
    actual=hashlib.sha1(b'blob '+str(count).encode()+b'\0'+blob.stdout).hexdigest()
    if actual!=oid:return None,'oid_mismatch'
    return {'type':'blob','bytes':count,'actual_oid':actual,'content_sha256':hashlib.sha256(blob.stdout).hexdigest()},'success'


def attempt(repo,url,oid,manifest_sha,timeout=60,synthetic=False):
    if not synthetic and (url!=URL or timeout!=60):raise ValueError('remote/timeout policy drift')
    if not re.fullmatch('[0-9a-f]{40}',oid) or not re.fullmatch('[0-9a-f]{64}',manifest_sha):raise ValueError('invalid OID/hash')
    repo=Path(repo);repo.mkdir(parents=True,exist_ok=False)
    subprocess.run(['git','init','--bare','-q',str(repo)],check=True)
    cmd=['git','-c','gc.auto=0','-c','pack.threads=1','-c','http.followRedirects=false','-C',str(repo),'fetch','--no-tags','--no-recurse-submodules','--no-write-fetch-head',url,oid]
    env=dict(os.environ,GIT_TERMINAL_PROMPT='0',GIT_NO_LAZY_FETCH='1',GIT_LFS_SKIP_SMUDGE='1')
    reason=None;meta=None
    with (repo/'probe.stdout').open('wb') as out,(repo/'probe.stderr').open('wb') as err:
        process=subprocess.Popen(cmd,stdout=out,stderr=err,env=env,start_new_session=True);deadline=time.monotonic()+timeout
        while process.poll() is None:
            error=(repo/'probe.stderr').read_bytes().lower()
            size=sum(p.stat().st_size for p in (repo/'objects').rglob('*') if p.is_file())
            if time.monotonic()>=deadline:reason='timeout'
            elif size>LIMIT:reason='volume_limit'
            elif len(error)>1024*1024:reason='response_anomaly'
            elif any(x in error for x in (b'captcha',b'bot check',b'verify you are human')):reason='bot_challenge'
            elif any(x in error for x in (b'could not read username',b'authentication failed',b'username for')):reason='auth_required'
            elif b'filtering not recognized' in error or b'filtering not supported' in error:reason='filter_unsupported'
            if reason:
                try:os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                break
            time.sleep(.05)
        code=process.wait()
    final_error=(repo/'probe.stderr').read_bytes().lower()
    final_size=sum(p.stat().st_size for p in (repo/'objects').rglob('*') if p.is_file())
    if reason is None and final_size>LIMIT:reason='volume_limit'
    if reason is None and any(x in final_error for x in (b'captcha',b'bot check',b'verify you are human')):reason='bot_challenge'
    if reason is None and any(x in final_error for x in (b'could not read username',b'authentication failed',b'username for')):reason='auth_required'
    if reason is None and (b'filtering not recognized' in final_error or b'filtering not supported' in final_error):reason='filter_unsupported'
    if reason is None:
        if code:reason='server_rejected'
        else:
            meta,reason=verify_blob(repo,oid)
            env['GIT_NO_LAZY_FETCH']='1'
            objects=subprocess.run(['git','-c','protocol.allow=never','-C',str(repo),'cat-file','--batch-all-objects','--batch-check=%(objectname)'],capture_output=True,env=env,timeout=5)
            if reason=='success' and (objects.returncode or objects.stdout.splitlines()!=[oid.encode()]):reason='response_anomaly';meta=None
    if reason!='success':meta=None
    result={'schema_version':'wayne.single-blob-probe.v1','evidence_scope':'synthetic' if synthetic else 'actual_remote_probe','manifest_sha256':manifest_sha,'source_url':url if not synthetic else 'synthetic-local-git-service','selection_index':0,'selected_oid':oid,'request_method':'single_exact_oid_fetch_no_fallback','command':[s if s not in (str(repo),url) else '<isolated-object-db>' if s==str(repo) else URL if not synthetic else '<synthetic-local-service>' for s in cmd],'hard_timeout_seconds':timeout,'byte_limit':LIMIT,'exit_code':code,'result':reason,'object':meta,'stdout_sha256':hashlib.sha256((repo/'probe.stdout').read_bytes()).hexdigest(),'stderr_sha256':hashlib.sha256((repo/'probe.stderr').read_bytes()).hexdigest(),'history_complete':False,'upstream_membership_verified':False,'carry_strategy_reviewed':False,'eligible':False,'hardware_tested':False}
    return canonical(result)


def validate(raw,manifest,manifest_sha,repo):
    if len(raw)>65536:raise ValueError('probe evidence size limit')
    d=json.loads(raw.decode('utf-8'),object_pairs_hook=pairs,parse_constant=reject_constant)
    keys={'schema_version','evidence_scope','manifest_sha256','source_url','selection_index','selected_oid','request_method','command','hard_timeout_seconds','byte_limit','exit_code','result','object','stdout_sha256','stderr_sha256','history_complete','upstream_membership_verified','carry_strategy_reviewed','eligible','hardware_tested'}
    if type(d) is not dict or set(d)!=keys or d['schema_version']!='wayne.single-blob-probe.v1':raise ValueError('unknown fields/schema')
    chosen=selection(manifest,manifest_sha)
    if d['manifest_sha256']!=manifest_sha or d['selected_oid']!=chosen or d['selection_index']!=0 or d['source_url']!=URL or d['evidence_scope']!='actual_remote_probe':raise ValueError('selection/URL/hash/scope drift')
    if d['result'] not in REASONS or type(d['exit_code']) is not int or d['hard_timeout_seconds']!=60 or d['byte_limit']!=LIMIT or d['request_method']!='single_exact_oid_fetch_no_fallback':raise ValueError('result/policy drift')
    expected=['git','-c','gc.auto=0','-c','pack.threads=1','-c','http.followRedirects=false','-C','<isolated-object-db>','fetch','--no-tags','--no-recurse-submodules','--no-write-fetch-head',URL,chosen]
    if d['command']!=expected or any(d[k] is not False for k in ('history_complete','upstream_membership_verified','carry_strategy_reviewed','eligible','hardware_tested')):raise ValueError('unsafe command/claims')
    for k in ('stdout_sha256','stderr_sha256'):
        if not isinstance(d[k],str) or not re.fullmatch('[0-9a-f]{64}',d[k]):raise ValueError('bad response hash')
    for filename,key in (('probe.stdout','stdout_sha256'),('probe.stderr','stderr_sha256')):
        evidence=Path(repo)/filename
        if evidence.exists() and hashlib.sha256(evidence.read_bytes()).hexdigest()!=d[key]:raise ValueError('response evidence hash drift')
    if d['result']=='success':
        actual,reason=verify_blob(repo,chosen)
        if d['exit_code']!=0 or reason!='success' or canonical(d['object'])!=canonical(actual):raise ValueError('successful object/type/OID/hash mismatch')
    elif d['object'] is not None:raise ValueError('failure carries object metadata')
    return canonical(d)
