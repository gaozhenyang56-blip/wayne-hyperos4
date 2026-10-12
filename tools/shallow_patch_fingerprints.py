#!/usr/bin/env python3
"""Local single-parent content fingerprints only; no provenance or carry decisions."""
import argparse,hashlib,json,os,re,subprocess,sys
from pathlib import Path
from shallow_patch_inventory import canonical
from shallow_review_queue import validate as validate_queue
from check_source_update import pairs,reject_constant
from export_dtb_consumers import _write_payload
OPTIONS=['--no-ext-diff','--no-textconv','--no-renames','--diff-algorithm=myers','--no-indent-heuristic','--no-color','--no-relative','--src-prefix=a/','--dst-prefix=b/','--unified=3','--submodule=short']
REASONS=('shallow_boundary','paths_unknown','zero_parents','merge_commit','parent_unavailable','objects_unavailable','empty_patch','evidence_limit')


def fingerprint(repo,oid,parent):
    env=dict(os.environ,GIT_NO_LAZY_FETCH='1',GIT_TERMINAL_PROMPT='0',LC_ALL='C')
    def git(args,stdin=None):return subprocess.run(['git','-c','protocol.allow=never','-c','core.quotePath=true','-C',str(repo),*args],input=stdin,capture_output=True,env=env,timeout=5)
    for commit in (oid,parent):
        r=git(['cat-file','-e',commit+'^{commit}'])
        if r.returncode:return None,'objects_unavailable'
    r=git(['diff',*OPTIONS,'--binary','--full-index',parent,oid,'--'])
    if r.returncode:return None,'objects_unavailable'
    diff=r.stdout
    if len(diff)>4*1024*1024:return None,'evidence_limit'
    if not diff:return None,'empty_patch'
    pid=git(['patch-id','--stable'],diff)
    if pid.returncode or not re.fullmatch(rb'[0-9a-f]{40} [0-9a-f]{40}\n',pid.stdout):raise ValueError('malformed patch-id')
    stat=git(['diff',*[o for o in OPTIONS if not o.startswith('--unified=')],'--numstat','-z',parent,oid,'--'])
    if stat.returncode:return None,'objects_unavailable'
    if len(stat.stdout)>4*1024*1024:return None,'evidence_limit'
    adds=deletes=binaries=files=0
    if stat.stdout and not stat.stdout.endswith(b'\0'):raise ValueError('truncated numstat')
    for entry in stat.stdout.split(b'\0'):
        if not entry:continue
        a,d,path=entry.split(b'\t',2);files+=1
        if a==d==b'-':binaries+=1
        elif a.isdigit() and d.isdigit():adds+=int(a);deletes+=int(d)
        else:raise ValueError('malformed numstat')
    return {'patch_id':pid.stdout[:40].decode(),'diff_sha256':hashlib.sha256(diff).hexdigest(),'files_changed':files,'insertions':adds,'deletions':deletes,'binary_files':binaries,'text_counts_only':True},None


def generate(inventory_raw,queue_raw,inventory_sha,queue_sha,repo):
    if not re.fullmatch('[0-9a-f]{64}',queue_sha) or hashlib.sha256(queue_raw).hexdigest()!=queue_sha:raise ValueError('queue binding hash mismatch')
    validate_queue(queue_raw,inventory_raw,inventory_sha)
    inv=json.loads(inventory_raw);queue=json.loads(queue_raw);items=[];counts={r:0 for r in REASONS};success=0
    for rec in inv['records']:
        parents=rec['parents'];reason=None;value=None
        if rec['shallow_boundary_commit']:reason='shallow_boundary'
        elif not parents:reason='zero_parents'
        elif len(parents)!=1:reason='merge_commit'
        elif not rec['path_evidence_complete']:reason='paths_unknown'
        elif not parents[0]['inside_visible_graph'] or not parents[0]['object_available']:reason='parent_unavailable'
        else:value,reason=fingerprint(repo,rec['oid'],parents[0]['oid'])
        if reason:counts[reason]+=1
        else:success+=1
        items.append({'inventory_sha256':inventory_sha,'review_queue_sha256':queue_sha,'commit_oid':rec['oid'],'parent_oid':parents[0]['oid'] if len(parents)==1 else None,'parents':[p['oid'] for p in parents],'patch_id':value['patch_id'] if value else None,'diff_sha256':value['diff_sha256'] if value else None,'statistics':{k:v for k,v in value.items() if k not in ('patch_id','diff_sha256')} if value else None,'null_reason':reason,'review_status':'unreviewed','carry_decision':'undetermined','upstream_membership_verified':False})
    return canonical({'schema_version':'wayne.shallow-patch-fingerprints.v1','inventory_sha256':inventory_sha,'review_queue_sha256':queue_sha,'diff_command':['git','-c','protocol.allow=never','-c','core.quotePath=true','-C','<repo>','diff',*OPTIONS,'--binary','--full-index','<parent>','<commit>','--'],'patch_id_command':['git','patch-id','--stable'],'items':items,'success_count':success,'null_reason_counts':counts,'history_complete':False,'eligible':False,'hardware_tested':False})


def validate(raw,*args):
    if len(raw)>16*1024*1024:raise ValueError('fingerprint report size limit')
    data=json.loads(raw.decode('utf-8'),object_pairs_hook=pairs,parse_constant=reject_constant);expected=json.loads(generate(*args))
    if type(data) is not dict or set(data)!=set(expected) or canonical({k:data[k] for k in expected})!=canonical(expected):raise ValueError('unknown fields/OID/hash/fingerprint/null reason/order drift')
    return canonical(expected)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('repo',type=Path);p.add_argument('inventory',type=Path);p.add_argument('queue',type=Path);p.add_argument('--inventory-sha',required=True);p.add_argument('--queue-sha',required=True);p.add_argument('--validate',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    try:
        args=(a.inventory.read_bytes(),a.queue.read_bytes(),a.inventory_sha,a.queue_sha,a.repo)
        raw=validate(a.validate.read_bytes(),*args) if a.validate else generate(*args);_write_payload(raw,a.output)
        if a.output is None:sys.stdout.buffer.write(raw)
    except (ValueError,OSError,subprocess.SubprocessError) as e:sys.stderr.write('REJECT: '+str(e)+'\n')
    return 2
if __name__=='__main__':raise SystemExit(main())
