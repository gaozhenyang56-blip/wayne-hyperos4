#!/usr/bin/env python3
"""Offline visible commit/path hints only, not upstream or patch carry qualification."""
import argparse,datetime,hashlib,json,os,re,subprocess,sys
from pathlib import Path
from check_source_update import pairs,reject_constant
from export_dtb_consumers import _write_payload
CURRENT='6a4e475000ecc7e864911959a1984a0664088464'


def canonical(value):return (json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(',',':'))+'\n').encode()


def safe_path(path):
    if not path or path.startswith('/') or any(p in ('','..','.') for p in path.split('/')) or '\\' in path or '\x00' in path:raise ValueError('invalid/traversal change path')


def inventory(repo,current=CURRENT):
    if not re.fullmatch('[0-9a-f]{40}',current):raise ValueError('invalid OID')
    env=dict(os.environ,GIT_NO_LAZY_FETCH='1',GIT_TERMINAL_PROMPT='0')
    def git(*args,optional=False):
        r=subprocess.run(['git','-c','protocol.allow=never','-C',str(repo),*args],capture_output=True,env=env,timeout=5)
        if len(r.stdout)>4*1024*1024:raise ValueError('git evidence size limit')
        if r.returncode and not optional:raise ValueError('local object/tree evidence unavailable: '+args[0])
        return r
    git('rev-parse','--verify',current+'^{commit}')
    shallow_path=git('rev-parse','--git-path','shallow').stdout.decode().strip()
    path=Path(shallow_path);path=path if path.is_absolute() else Path(repo)/path
    boundaries=sorted(path.read_text().splitlines()) if path.exists() else []
    if not boundaries or any(not re.fullmatch('[0-9a-f]{40}',v) for v in boundaries):raise ValueError('explicit shallow boundary required')
    oids=sorted(git('rev-list',current).stdout.decode().splitlines())
    if len(oids)>4096 or len(set(oids))!=len(oids):raise ValueError('visible commit limit/duplicates')
    visible=set(oids);records=[]
    for oid in oids:
        raw=git('cat-file','commit',oid).stdout
        if hashlib.sha1(b'commit '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=oid:raise ValueError('commit object OID drift')
        head,body=raw.split(b'\n\n',1);parents=[];author=None
        for line in head.splitlines():
            if line.startswith(b'parent '):
                parent=line[7:].decode('ascii')
                if not re.fullmatch('[0-9a-f]{40}',parent):raise ValueError('malformed parent OID')
                parents.append({'oid':parent,'inside_visible_graph':parent in visible,'object_available':git('cat-file','-e',parent+'^{commit}',optional=True).returncode==0})
            if line.startswith(b'author '):
                m=re.search(rb' (-?[0-9]+) ([+-][0-9]{4})$',line)
                if not m:raise ValueError('invalid author date')
                author={'unix_seconds':int(m[1]),'timezone':m[2].decode()}
        if author is None:raise ValueError('author missing')
        subject=body.split(b'\n',1)[0].decode('utf-8')
        paths=None
        complete=oid not in boundaries and all(p['inside_visible_graph'] and p['object_available'] for p in parents)
        if complete:
            changed=set()
            diffs=[['diff-tree','--root','-r','--no-renames','--no-ext-diff','--no-textconv','--no-commit-id','--name-only','-z',oid]] if not parents else [['diff-tree','-r','--no-renames','--no-ext-diff','--no-textconv','--no-commit-id','--name-only','-z',p['oid'],oid] for p in parents]
            for args in diffs:
                output=git(*args).stdout
                if output and not output.endswith(b'\0'):raise ValueError('truncated changed path evidence')
                for name in output.split(b'\0'):
                    if name:
                        value=name.decode('utf-8');safe_path(value);changed.add(value)
            paths=sorted(changed)
        text=subject.lower();components={p.lower() for name in paths or [] for p in name.split('/')}
        hints=[]
        for key,word in (('wayne','wayne'),('sdm660','sdm660'),('qualcomm','qualcomm'),('android','android'),('jasmine_reference','jasmine')):
            if re.search(r'(?<![a-z0-9])'+word+r'(?![a-z0-9])',text) or any(re.search(r'(?<![a-z0-9])'+word+r'(?![a-z0-9])',p) for p in components):hints.append(key)
        if 'qcom' in components and 'qualcomm' not in hints:hints.append('qualcomm')
        record={'oid':oid,'parents':parents,'author_date':author,'subject':subject,'changed_paths':paths,'path_evidence_complete':complete,'shallow_boundary_commit':oid in boundaries,'clues':sorted(hints),'wayne_target_verified':False,'commit_object_sha256':hashlib.sha256(raw).hexdigest()}
        records.append({**record,'record_sha256':hashlib.sha256(canonical(record)).hexdigest()})
    return canonical({'schema_version':'wayne.shallow-patch-inventory.v1','current_commit':current,'shallow_boundaries':boundaries,'records':records,'clue_rule_version':'literal-subject-path-component-v1','shallow_boundary':True,'history_complete':False,'upstream_membership_verified':False,'carry_strategy_reviewed':False,'eligible':False,'hardware_tested':False})


def validate(raw,repo,current=CURRENT):
    if len(raw)>16*1024*1024:raise ValueError('inventory size limit')
    data=json.loads(raw.decode('utf-8'),object_pairs_hook=pairs,parse_constant=reject_constant)
    expected=json.loads(inventory(repo,current))
    if type(data) is not dict or set(data)!=set(expected):raise ValueError('unknown/missing inventory field')
    if canonical({key:data[key] for key in expected})!=canonical(expected):raise ValueError('record/path/hash/parent graph drift')
    return canonical(expected)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('repo',type=Path);p.add_argument('--output',type=Path);p.add_argument('--validate',type=Path);a=p.parse_args()
    try:
        payload=validate(a.validate.read_bytes(),a.repo) if a.validate else inventory(a.repo)
        _write_payload(payload,a.output)
        if a.output is None:sys.stdout.buffer.write(payload)
    except (ValueError,OSError,subprocess.SubprocessError) as e:sys.stderr.write('REJECT: '+str(e)+'\n')
    return 2 # Never update eligibility
if __name__=='__main__':raise SystemExit(main())
