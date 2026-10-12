#!/usr/bin/env python3
"""Offline relationship audit. This first stage cannot authorize a source update."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
SCHEMA='wayne.source-update-request.v1'
KEYS={'schema_version','current_url','candidate_url','current_commit','candidate_commit','upstream_base_commit','patch_policy','evidence_sha256'}


def pairs(items):
    result={}
    for key,value in items:
        if key in result:raise ValueError('duplicate key')
        result[key]=value
    return result


def reject_constant(value):raise ValueError('nonfinite JSON')


def parse(raw,lock):
    if len(raw)>65536:raise ValueError('request too large')
    data=json.loads(raw.decode('utf-8'),object_pairs_hook=pairs,parse_constant=reject_constant)
    if type(data) is not dict or set(data)!=KEYS or data['schema_version']!=SCHEMA:raise ValueError('unknown/missing fields or schema')
    if data['current_url']!=lock['repository'] or data['current_commit']!=lock['commit']:raise ValueError('current source drift')
    if data['candidate_url'] not in (lock['repository'],'https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git'):raise ValueError('candidate URL drift')
    for key in ('current_commit','candidate_commit','upstream_base_commit'):
        if data[key] is None and key!='current_commit':continue
        if not isinstance(data[key],str) or not re.fullmatch('[0-9a-f]{40}',data[key]):raise ValueError('invalid commit: '+key)
    if data['patch_policy'] not in ('unverified','preserve_current_ancestry'):raise ValueError('unknown patch policy')
    hashes=data['evidence_sha256']
    if type(hashes) is not dict or not set(hashes)<= {'current_makefile','candidate_makefile','relation'}:raise ValueError('unknown evidence field')
    for value in hashes.values():
        if not isinstance(value,str) or not re.fullmatch('[0-9a-f]{64}',value):raise ValueError('invalid evidence hash')
    return data


def assess(raw,repo,lock):
    request=parse(raw,lock)
    report={'schema_version':'wayne.source-update-report.v1','current_commit':request['current_commit'],'candidate_commit':request['candidate_commit'],'current_url':request['current_url'],'candidate_url':request['candidate_url'],'status':'blocked','gaps':[],'evidence':[],'relationship':None,'patch_policy':request['patch_policy'],'non_upstream_patch_classification':'unverified','build_gate_authorization':False,'hardware_tested':False}
    def git(*args):
        result=subprocess.run(['git','-C',str(repo),*args],capture_output=True,timeout=10)
        if result.returncode:raise ValueError('git evidence unavailable: '+' '.join(args[:2]))
        return result.stdout
    def evidence(name,args,output):
        digest=hashlib.sha256(output).hexdigest()
        report['evidence'].append({'name':name,'command':['git','-C','<repo>',*args],'sha256':digest,'output':output.decode('utf-8')})
        expected=request['evidence_sha256'].get(name)
        if expected is None:report['gaps'].append('missing expected evidence hash: '+name)
        elif expected!=digest:raise ValueError('evidence hash mismatch: '+name)
    try:
        if git('rev-parse','--is-shallow-repository').strip()!=b'false':raise ValueError('shallow history')
        if git('config','--get','remote.origin.url').decode().strip()!=request['current_url']:raise ValueError('local origin URL drift')
        for key in ('current_commit','candidate_commit','upstream_base_commit'):
            if request[key] is None:raise ValueError('unpinned '+key)
            git('cat-file','-e',request[key]+'^{commit}')
        for label,key in (('current_makefile','current_commit'),('candidate_makefile','candidate_commit')):
            args=['show',request[key]+':Makefile'];output=git(*args);evidence(label,args,output)
            version={}
            for symbol in ('VERSION','PATCHLEVEL','SUBLEVEL'):
                found=re.findall(r'^'+symbol+r'\s*=\s*(\d+)\s*$',output.decode(),re.M)
                if len(found)!=1:raise ValueError('ambiguous Makefile version')
                version[symbol]=int(found[0])
            report[label+'_version']=version
        current,candidate,base=(request[k] for k in ('current_commit','candidate_commit','upstream_base_commit'))
        common=git('merge-base',current,candidate).decode().strip()
        counts=git('rev-list','--left-right','--count',current+'...'+candidate).decode().split()
        commits=git('rev-list',base+'..'+current).decode().splitlines()
        def ancestor(a,b):
            r=subprocess.run(['git','-C',str(repo),'merge-base','--is-ancestor',a,b],capture_output=True,timeout=10)
            if r.returncode not in (0,1):raise ValueError('incomplete ancestor proof')
            return r.returncode==0
        relation={'merge_base':common,'current_only':int(counts[0]),'candidate_only':int(counts[1]),'current_ancestor_candidate':ancestor(current,candidate),'base_ancestor_current':ancestor(base,current),'commits_after_declared_upstream_base':commits}
        output=(json.dumps(relation,separators=(',',':'))+'\n').encode();evidence('relation',['merge-base/rev-list','<fixed-commits>'],output);report['relationship']=relation
        if not relation['current_ancestor_candidate']:report['gaps'].append('non-fast-forward; current commits not proven retained')
        if not relation['base_ancestor_current']:report['gaps'].append('declared base is not an ancestor')
        if request['patch_policy']=='unverified':report['gaps'].append('patch carry policy missing')
    except (OSError,ValueError,subprocess.SubprocessError) as error:
        report['gaps'].append(str(error))
    report['gaps'].append('trusted upstream membership/SDM660 patch inventory and carry review not established; this first-stage tool never emits eligible')
    return (json.dumps(report,ensure_ascii=False,allow_nan=False,separators=(',',':'))+'\n').encode()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('request',type=Path);p.add_argument('repo',type=Path);a=p.parse_args()
    try:
        lock=json.loads((ROOT/'config/kernel-6.6-experiment.json').read_text())
        with a.request.open('rb') as stream:raw=stream.read(65537)
        sys.stdout.buffer.write(assess(raw,a.repo,lock));return 2
    except (ValueError,OSError) as error:sys.stderr.write('REJECT: '+str(error)+'\n');return 2

if __name__=='__main__':raise SystemExit(main())
