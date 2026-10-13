"""Only validates saved one-page release response; no source or network operations."""
import hashlib,json,re,subprocess,os
from pathlib import Path
from check_xiaomi_official_tags import audit as tag_audit
from isolated_blob_attribution import validate,ROOT
from check_source_update import pairs,reject_constant
from shallow_patch_inventory import canonical
from export_dtb_consumers import _write_payload
URL='https://api.github.com/repos/MiCode/Xiaomi_Kernel_OpenSource/releases?per_page=20&page=1'
CMD=['curl','--silent','--show-error','--max-time','60','--connect-timeout','15','--max-filesize','1048576','--retry','0','--proto','=https','--max-redirs','0','--header','Accept: application/vnd.github+json','--header','X-GitHub-Api-Version: 2022-11-28','--dump-header','<response.headers>','--output','<response.body>','--write-out','%{http_code}',URL]
KEYS={'schema_version','baseline_tags_sha256','url','request_count','page','per_page','hard_timeout_seconds','max_response_bytes','redirects_followed','curl_exit_code','http_status','body_sha256','headers_sha256','stderr_sha256','command'}


def compose(raw,body,headers,stderr,base_sha):
    if len(raw)>65536 or len(headers)>65536 or len(stderr)>65536 or len(body)>1048576:raise ValueError('response bound')
    r=json.loads(raw.decode(),object_pairs_hook=pairs,parse_constant=reject_constant)
    if type(r) is not dict or set(r)!=KEYS or r['schema_version']!='wayne.official-release-request.v1' or r['url']!=URL or r['command']!=CMD or r['baseline_tags_sha256']!=base_sha or not re.fullmatch('[0-9a-f]{64}',base_sha) or any(type(r[k]) is not int or r[k]!=v for k,v in [('request_count',1),('page',1),('per_page',20),('hard_timeout_seconds',60),('max_response_bytes',1048576)]) or r['redirects_followed'] is not False or type(r['curl_exit_code']) is not int or (r['http_status'] is not None and type(r['http_status']) is not int):raise ValueError('request schema/source/policy drift')
    for data,key in ((body,'body_sha256'),(headers,'headers_sha256'),(stderr,'stderr_sha256')):
        if hashlib.sha256(data).hexdigest()!=r[key]:raise ValueError('response hash drift')
    # Keep the final response block; proxy CONNECT blocks are not API evidence.
    blocks=re.split(rb'\r?\n\r?\n',headers);final=None
    for block in blocks:
        lines=block.decode('iso-8859-1').splitlines()
        if lines and re.fullmatch(r'HTTP/\S+ \d{3}(?: .*)?',lines[0]):final=lines
    if final is None or int(final[0].split()[1])!=r['http_status']:raise ValueError('HTTP status/header mismatch')
    h={}
    for line in final[1:]:
        if ':' not in line:raise ValueError('malformed HTTP header')
        key,value=line.split(':',1);key=key.casefold();h.setdefault(key,[]).append(value.strip())
    for key in ('content-length','content-type','link'):
        if len(h.get(key,[]))>1:raise ValueError('ambiguous header')
    length=h.get('content-length',[None])[0];link=h.get('link',[None])[0]
    if length is not None and (not length.isdigit() or int(length)>1048576):raise ValueError('invalid content length')
    complete=r['curl_exit_code']==0 and (length is None or int(length)==len(body))
    releases=[];candidates=[];status='unresolved';reason='http_or_transfer_failure'
    challenge=any(word in body.lower()+stderr.lower() for word in (b'captcha',b'verify you are human',b'bot check'))
    if challenge:reason='human_verification_stop'
    elif r['http_status'] in (401,403,429):reason='auth_refusal_or_rate_limit_stop'
    elif r['http_status']==200 and complete:
        if 'application/json' not in h.get('content-type',[''])[0]:raise ValueError('unexpected content type')
        releases=json.loads(body.decode('utf-8'),object_pairs_hook=pairs,parse_constant=reject_constant)
        if type(releases) is not list or len(releases)>20:raise ValueError('release page schema/limit')
        seen=set()
        for obj in releases:
            if type(obj) is not dict:raise ValueError('release object schema')
            for key in ('id','url','html_url','tag_name','target_commitish','name','body'):
                if key not in obj:raise ValueError('release field missing')
            rid=obj['id']
            if type(rid) is not int or rid<0 or rid in seen or obj['url']!='https://api.github.com/repos/MiCode/Xiaomi_Kernel_OpenSource/releases/'+str(rid) or not isinstance(obj['html_url'],str) or not obj['html_url'].startswith('https://github.com/MiCode/Xiaomi_Kernel_OpenSource/releases/tag/'):raise ValueError('duplicate/source release identity drift')
            seen.add(rid)
            if not isinstance(obj['tag_name'],str) or not obj['tag_name'] or not isinstance(obj['target_commitish'],str):raise ValueError('tag/target malformed')
            text='\n'.join(obj[k] or '' for k in ('tag_name','name','body'))
            matches=[label for label,pattern in [('wayne',r'(?<![a-z0-9])wayne(?![a-z0-9])'),('MI 6X',r'(?<![a-z0-9])mi[ _-]*6x(?![a-z0-9])'),('小米6X',r'小米\s*6x')] if re.search(pattern,text,re.I)]
            if matches:
                target=obj['target_commitish'];oid=target if re.fullmatch('[0-9a-f]{40}',target) else None
                candidates.append({'release_id':rid,'url':obj['url'],'html_url':obj['html_url'],'tag_name':obj['tag_name'],'matched_labels':matches,'target_commitish':target,'declared_commit_oid':oid,'oid_membership_verified':False,'target_is_mutable_or_unresolved':oid is None,'release_text_sha256':hashlib.sha256(text.encode()).hexdigest(),'candidate_only_not_source_or_board_authorization':True})
        reason='candidate_metadata_only_keep_unresolved' if candidates else 'no_matching_release_in_one_page'
    elif r['http_status']==200:reason='transfer_incomplete_or_truncated_stop'
    return canonical({'schema_version':'wayne.official-releases-evidence.v1','baseline_tags_sha256':base_sha,'request_sha256':hashlib.sha256(raw).hexdigest(),'request':r,'response_scope':{'page':1,'per_page':20,'returned_releases':len(releases) if complete and r['http_status']==200 and not challenge else None,'body_bytes':len(body),'content_length':int(length) if length else None,'transfer_complete':complete,'has_pagination_link':link is not None,'pagination_link':link,'additional_pages_requested':False,'attachments_downloaded':False},'device_candidates':candidates,'source_entry':None,'discovery_status':status,'reason':reason,'no_global_absence_claim':True,'target_association':'unresolved','history_complete':False,'upstream_membership_verified':False,'carry_strategy_reviewed':False,'eligible':False,'hardware_tested':False,'build_gate_authorization':False,'source_lock_input':False})


def audit(root=ROOT):
    root=Path(root);stage=root/'research/xiaomi-official-releases-stage';old=root/'research/xiaomi-official-tags-stage';base=(old/'discovery.json').read_bytes();sha=hashlib.sha256(base).hexdigest()
    if sha!=json.loads((old/'checkpoint.json').read_bytes())['discovery_sha256']:raise ValueError('baseline hash drift')
    validate(base,tag_audit(root))
    env=dict(os.environ,GIT_NO_LAZY_FETCH='1',GIT_TERMINAL_PROMPT='0')
    def git(*args,stdin=None):
        r=subprocess.run(['git','-c','protocol.allow=never','-C',str(root),*args],input=stdin,capture_output=True,env=env,timeout=5)
        if r.returncode:raise ValueError('local baseline unavailable')
        return r.stdout
    if git('show','1f2a896:research/xiaomi-official-tags-stage/discovery.json')!=base:raise ValueError('baseline commit drift')
    raw=compose((stage/'request.json').read_bytes(),(stage/'response.body').read_bytes(),(stage/'response.headers').read_bytes(),(stage/'request.stderr').read_bytes(),sha)
    oids=sorted({x['declared_commit_oid'] for x in json.loads(raw)['device_candidates'] if x['declared_commit_oid']})
    if oids and git('cat-file','--batch-check',stdin=('\n'.join(oids)+'\n').encode())!=''.join(oid+' missing\n' for oid in oids).encode():raise ValueError('source object imported into main database')
    return raw

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);p.add_argument('--check',type=Path);a=p.parse_args();raw=audit()
    if a.check:validate(a.check.read_bytes(),raw)
    elif a.output:_write_payload(raw,a.output)
    else:print(raw.decode(),end='')
