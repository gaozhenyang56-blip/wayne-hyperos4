"""Strict ls-remote metadata pinning only, never update eligibility."""
import hashlib,json,re
from check_source_update import pairs,reject_constant

URL='https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git'
CURRENT='6a4e475000ecc7e864911959a1984a0664088464'
COMMAND=['git','ls-remote','--tags',URL,'refs/tags/v6.6.*']


def refs(raw):
    if not isinstance(raw,bytes) or not raw or len(raw)>1024*1024 or not raw.endswith(b'\n'):raise ValueError('empty/oversize/incomplete ref output')
    result={}
    for line in raw.decode('ascii').splitlines():
        m=re.fullmatch(r'([0-9a-f]{40})\t(refs/[A-Za-z0-9/._^{}-]+)',line)
        if not m or m[2] in result:raise ValueError('malformed/duplicate/conflicting ref')
        result[m[2]]=m[1]
    return result


def candidate(raw,url=URL,exit_code=0,complete=True):
    if url!=URL or type(exit_code) is not int or exit_code!=0 or complete is not True:raise ValueError('remote failure/incomplete query/URL drift')
    entries=refs(raw);tags={}
    for ref in entries:
        m=re.fullmatch(r'refs/tags/v6\.6\.(0|[1-9][0-9]*)(\^\{\})?',ref)
        if not m:raise ValueError('non-strict v6.6.N tag')
        if len(m[1])>9:raise ValueError('version number outside bounds')
        tags[int(m[1])]='v6.6.'+m[1]
    tag=tags[max(tags)];ref='refs/tags/'+tag
    if ref not in entries or ref+'^{}' not in entries:raise ValueError('highest tag lacks annotated/peeled pair; no lightweight fallback')
    if entries[ref]==entries[ref+'^{}']:raise ValueError('invalid annotated object/peeled equality')
    return {'schema_version':'wayne.candidate-metadata.v1','source_url':URL,'query_command':COMMAND,'current_commit':CURRENT,'candidate_tag':tag,'tag_object':entries[ref],'peeled_commit':entries[ref+'^{}'],'query_stdout_sha256':hashlib.sha256(raw).hexdigest(),'update_status':'blocked','gaps':['complete fork/candidate histories absent','merge-base and bidirectional counts unverified','trusted upstream membership not locally verified','non-upstream SDM660/wayne patch inventory and carry policy unreviewed'],'build_gate_authorization':False,'hardware_tested':False}


def canonical(data):return (json.dumps(data,ensure_ascii=False,allow_nan=False,separators=(',',':'))+'\n').encode()


def validate_metadata(metadata,raw):
    if len(metadata)>65536:raise ValueError('metadata too large')
    data=json.loads(metadata.decode('utf-8'),object_pairs_hook=pairs,parse_constant=reject_constant)
    if type(data) is not dict or set(data)!=set(candidate(raw)):raise ValueError('unknown/missing metadata fields')
    expected=candidate(raw)
    if canonical({key:data[key] for key in expected})!=canonical(expected):raise ValueError('metadata URL/tag/commit/hash/schema binding drift')
    return canonical(candidate(raw))


if __name__=='__main__':
    import argparse,sys
    from pathlib import Path
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('metadata',type=Path);p.add_argument('query_stdout',type=Path);a=p.parse_args()
    try:
        with a.metadata.open('rb') as stream:metadata=stream.read(65537)
        with a.query_stdout.open('rb') as stream:raw=stream.read(1024*1024+1)
        sys.stdout.buffer.write(validate_metadata(metadata,raw))
    except (ValueError,OSError) as error:sys.stderr.write('REJECT: '+str(error)+'\n')
    raise SystemExit(2) # metadata never authorizes an update
