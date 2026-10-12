#!/usr/bin/env python3
"""Deterministic unreviewed mechanical signals; never keep/drop or upstream decisions."""
import argparse,hashlib,json,re,sys
from pathlib import Path
from shallow_patch_inventory import canonical,safe_path,CURRENT
from check_source_update import pairs,reject_constant
from export_dtb_consumers import _write_payload
CLASSES=('wayne_explicit','sdm660_explicit','qualcomm_generic','android_generic','jasmine_only','no_target_signal')
ROOT_KEYS={'schema_version','current_commit','shallow_boundaries','records','clue_rule_version','shallow_boundary','history_complete','upstream_membership_verified','carry_strategy_reviewed','eligible','hardware_tested'}
REC_KEYS={'oid','parents','author_date','subject','changed_paths','path_evidence_complete','shallow_boundary_commit','clues','wayne_target_verified','commit_object_sha256','record_sha256'}


def oid(value):
    if not isinstance(value,str) or not re.fullmatch('[0-9a-f]{40}',value):raise ValueError('strict OID required')


def sha(value):
    if not isinstance(value,str) or not re.fullmatch('[0-9a-f]{64}',value):raise ValueError('strict SHA256 required')


def generate(raw,expected_sha):
    sha(expected_sha)
    if len(raw)>16*1024*1024 or hashlib.sha256(raw).hexdigest()!=expected_sha:raise ValueError('inventory hash mismatch/size')
    data=json.loads(raw.decode('utf-8'),object_pairs_hook=pairs,parse_constant=reject_constant)
    if type(data) is not dict or set(data)!=ROOT_KEYS or data['schema_version']!='wayne.shallow-patch-inventory.v1':raise ValueError('inventory schema/unknown field')
    oid(data['current_commit'])
    if data['clue_rule_version']!='literal-subject-path-component-v1':raise ValueError('unknown source clue rule')
    if data['shallow_boundary'] is not True or any(data[k] is not False for k in ('history_complete','upstream_membership_verified','carry_strategy_reviewed','eligible','hardware_tested')):raise ValueError('unsafe inventory claims')
    if type(data['records']) is not list or not 1<=len(data['records'])<=4096:raise ValueError('record count')
    if type(data['shallow_boundaries']) is not list or not data['shallow_boundaries']:raise ValueError('missing boundaries')
    for boundary in data['shallow_boundaries']:oid(boundary)
    if data['shallow_boundaries']!=sorted(set(data['shallow_boundaries'])):raise ValueError('boundary order/duplicate')
    records=data['records'];ids=[]
    for record in records:
        if type(record) is not dict or set(record)!=REC_KEYS:raise ValueError('unknown record field')
        oid(record['oid']);ids.append(record['oid']);sha(record['record_sha256']);sha(record['commit_object_sha256'])
        author=record['author_date']
        if type(author) is not dict or set(author)!={'unix_seconds','timezone'} or type(author['unix_seconds']) is not int or not isinstance(author['timezone'],str) or not re.fullmatch('[+-][0-9]{4}',author['timezone']):raise ValueError('unknown/invalid author fields')
        if type(record['clues']) is not list or any(c not in ('wayne','sdm660','qualcomm','android','jasmine_reference') for c in record['clues']):raise ValueError('invalid source clues')
        body={k:v for k,v in record.items() if k!='record_sha256'}
        if hashlib.sha256(canonical(body)).hexdigest()!=record['record_sha256']:raise ValueError('record hash mismatch')
    if ids!=sorted(set(ids)):raise ValueError('record order/duplicate OID')
    if data['current_commit'] not in ids:raise ValueError('current OID absent')
    visible=set(ids);items=[];counts={k:0 for k in CLASSES}
    for r in records:
        if type(r['parents']) is not list:raise ValueError('parents must be list')
        seen=set()
        for parent in r['parents']:
            if type(parent) is not dict or set(parent)!={'oid','inside_visible_graph','object_available'}:raise ValueError('unknown parent field')
            oid(parent['oid'])
            if parent['oid'] in seen or parent['oid']==r['oid'] or type(parent['inside_visible_graph']) is not bool or type(parent['object_available']) is not bool or parent['inside_visible_graph']!=(parent['oid'] in visible):raise ValueError('parent contradiction')
            seen.add(parent['oid'])
        if type(r['path_evidence_complete']) is not bool or type(r['shallow_boundary_commit']) is not bool or r['shallow_boundary_commit']!=(r['oid'] in data['shallow_boundaries']):raise ValueError('boundary/path flag mismatch')
        known=r['path_evidence_complete'];paths=r['changed_paths']
        if known:
            if r['shallow_boundary_commit'] or any(not p['inside_visible_graph'] or not p['object_available'] for p in r['parents']) or type(paths) is not list or paths!=sorted(set(paths)):raise ValueError('unproven paths')
            for path in paths:
                if not isinstance(path,str):raise ValueError('nonstring path')
                safe_path(path)
        elif paths is not None:raise ValueError('unknown paths must be null')
        if not isinstance(r['subject'],str) or r['wayne_target_verified'] is not False:raise ValueError('invalid subject/target claim')
        signals=[]
        for token in ('wayne','sdm660','qualcomm','qcom','android','jasmine'):
            pattern=r'(?<![a-z0-9])'+token+r'(?![a-z0-9])'
            if re.search(pattern,r['subject'].lower()):signals.append({'token':token,'source':'subject','text':r['subject'],'path_component':None})
            for path in paths or []:
                for component in path.split('/'):
                    if re.search(pattern,component.lower()):signals.append({'token':token,'source':'path','text':path,'path_component':component})
        signals.sort(key=lambda s:(s['token'],s['source'],s['text'],s['path_component'] or ''))
        tokens={s['token'] for s in signals};classes=[]
        for token,label in (('wayne','wayne_explicit'),('sdm660','sdm660_explicit'),('qualcomm','qualcomm_generic'),('android','android_generic')):
            if token in tokens or (token=='qualcomm' and 'qcom' in tokens):classes.append(label)
        if not classes:classes=['jasmine_only' if 'jasmine' in tokens else 'no_target_signal']
        sources={s['source'] for s in signals};strength='path_and_subject' if sources=={'subject','path'} else 'path_only' if sources=={'path'} else 'subject_only' if sources=={'subject'} else 'none'
        for c in classes:counts[c]+=1
        items.append({'inventory_sha256':expected_sha,'commit_oid':r['oid'],'parents':r['parents'],'paths_known':known,'classes':classes,'signal_sources':signals,'evidence_strength':strength,'review_status':'unreviewed','carry_decision':'undetermined','upstream_membership_verified':False})
    strength_order={'path_and_subject':0,'path_only':1,'subject_only':2,'none':3}
    items.sort(key=lambda i:(strength_order[i['evidence_strength']],tuple(CLASSES.index(c) for c in i['classes']),i['commit_oid']))
    return canonical({'schema_version':'wayne.shallow-review-queue.v1','inventory_sha256':expected_sha,'rule_version':'literal-signal-strength-v1','class_counts':counts,'items':items,'history_complete':False,'carry_strategy_reviewed':False,'eligible':False,'hardware_tested':False})


def validate(raw,inventory_raw,expected_sha):
    if len(raw)>16*1024*1024:raise ValueError('queue too large')
    data=json.loads(raw.decode('utf-8'),object_pairs_hook=pairs,parse_constant=reject_constant);expected=json.loads(generate(inventory_raw,expected_sha))
    if type(data) is not dict or set(data)!=set(expected) or canonical({k:data[k] for k in expected})!=canonical(expected):raise ValueError('queue fields/signal/hash/enum/order drift')
    return canonical(expected)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('inventory',type=Path);p.add_argument('--sha256',required=True);p.add_argument('--validate',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    try:
        with a.inventory.open('rb') as f:raw=f.read(16*1024*1024+1)
        payload=validate(a.validate.read_bytes(),raw,a.sha256) if a.validate else generate(raw,a.sha256)
        _write_payload(payload,a.output)
        if a.output is None:sys.stdout.buffer.write(payload)
    except (ValueError,OSError,TypeError) as e:sys.stderr.write('REJECT: '+str(e)+'\n')
    return 2
if __name__=='__main__':raise SystemExit(main())
