"""Conservative offline commit graph probe; shallow or missing graphs never decide ancestry."""
import hashlib,json,os,re,subprocess
from pathlib import Path
from check_source_update import pairs,reject_constant
URL='https://github.com/sdm660-mainline/linux.git'


def probe(repo,current,candidate):
    for value in (current,candidate):
        if not isinstance(value,str) or not re.fullmatch('[0-9a-f]{40}',value):raise ValueError('strict commit required')
    result={'schema_version':'wayne.history-relation.v1','current_commit':current,'candidate_commit':candidate,'status':'undetermined','relationship':None,'evidence':[],'gaps':[],'update_status':'blocked','build_gate_authorization':False,'hardware_tested':False}
    env=dict(os.environ,GIT_NO_LAZY_FETCH='1',GIT_TERMINAL_PROMPT='0')
    def git(*args):
        r=subprocess.run(['git','-C',str(repo),*args],capture_output=True,env=env,timeout=5)
        result['evidence'].append({'command':['git','-C','<repo>',*args],'exit_code':r.returncode,'stdout':r.stdout.decode(errors='replace'),'stdout_sha256':hashlib.sha256(r.stdout).hexdigest()})
        if r.returncode:raise ValueError('command unavailable/graph incomplete: '+' '.join(args[:2]))
        return r.stdout.decode().strip()
    try:
        for oid in (current,candidate):git('rev-parse','--verify',oid+'^{commit}')
        shallow=git('rev-parse','--is-shallow-repository')
        if shallow!='false':raise ValueError('shallow boundary: full relationship/counters undetermined')
        git('rev-list','--missing=error',current,candidate)
        common=git('merge-base',current,candidate)
        counts=git('rev-list','--left-right','--count',current+'...'+candidate).split()
        if not re.fullmatch('[0-9a-f]{40}',common) or len(counts)!=2 or any(not v.isdigit() for v in counts):raise ValueError('malformed graph command output')
        result['relationship']={'merge_base':common,'current_ancestor_candidate':common==current,'candidate_ancestor_current':common==candidate,'current_only':int(counts[0]),'candidate_only':int(counts[1])};result['status']='relation_observed'
    except (ValueError,OSError,subprocess.SubprocessError) as error:result['gaps'].append(str(error))
    result['gaps'].append('trusted upstream members and non-upstream patch carry policy unreviewed')
    return (json.dumps(result,ensure_ascii=False,allow_nan=False,separators=(',',':'))+'\n').encode()


def validate_fetch(raw,repo,url,ref):
    if len(raw)>1024*1024:raise ValueError('fetch report too large')
    data=json.loads(raw.decode('utf-8'),object_pairs_hook=pairs,parse_constant=reject_constant)
    keys={'schema_version','source_url','command','exit_code','depth','byte_limit','object_bytes','files','ref','shallow','blocked_reason','relationship_status','update_status'}
    if type(data) is not dict or set(data)!=keys or data['schema_version']!='wayne.history-fetch.v1' or data['source_url']!=url:raise ValueError('schema/URL drift')
    expected=['git','-c','gc.auto=0','-c','pack.threads=1','-C','<isolated-bare-'+('fork' if url==URL else 'official')+'>','fetch','--no-tags','--no-recurse-submodules','--filter=blob:none','--depth=64','origin',ref]
    if data['command']!=expected or data['depth']!=64 or data['byte_limit']!=16*1024*1024:raise ValueError('fetch policy drift')
    if type(data['files']) is not list:raise ValueError('files required')
    if type(data['exit_code']) is not int or type(data['object_bytes']) is not int or data['object_bytes']<0 or data['update_status']!='blocked' or data['relationship_status']!='undetermined':raise ValueError('invalid fetch status/count')
    if type(data['shallow']) is not list or any(not isinstance(v,str) or not re.fullmatch('[0-9a-f]{40}',v) for v in data['shallow']):raise ValueError('invalid shallow boundaries')
    refdata=data['ref']
    if type(refdata) is not dict or set(refdata)!={'command','exit_code','stdout','stdout_sha256'} or type(refdata['exit_code']) is not int or not isinstance(refdata['stdout'],str) or hashlib.sha256(refdata['stdout'].encode()).hexdigest()!=refdata['stdout_sha256']:raise ValueError('invalid ref evidence')
    root=Path(repo).resolve();seen=set();total=0
    for file in data['files']:
        if type(file) is not dict or set(file)!={'path','bytes','sha256'}:raise ValueError('unknown file evidence')
        path=(root/file['path']).resolve()
        if file['path'] in seen or not path.is_relative_to(root/'objects') or not path.is_file():raise ValueError('missing/escaping/duplicate object file')
        seen.add(file['path']);blob=path.read_bytes();total+=len(blob)
        if type(file['bytes']) is not int or len(blob)!=file['bytes'] or not isinstance(file['sha256'],str) or not re.fullmatch('[0-9a-f]{64}',file['sha256']) or hashlib.sha256(blob).hexdigest()!=file['sha256']:raise ValueError('object size/hash drift')
    if total!=data['object_bytes'] or total>data['byte_limit']:raise ValueError('object limit/accounting mismatch')
    return data # Byte report validated, not fetch success or source authenticity.
