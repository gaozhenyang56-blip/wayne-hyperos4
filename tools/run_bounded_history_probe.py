#!/usr/bin/env python3
"""One fixed bounded metadata fetch per remote; no checkout or retries."""
import datetime,hashlib,json,os,signal,subprocess,time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'research/history-probe-stage'
LAB=ROOT/'downloads/history-probe-73e35d6'
LIMIT=16*1024*1024
DEPTH=64
SOURCES={'fork':('https://github.com/sdm660-mainline/linux.git','6a4e475000ecc7e864911959a1984a0664088464'),'official':('https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git','refs/tags/v6.6.158')}

def run(name,source):
 url,ref=source;repo=LAB/name;repo.mkdir(parents=True,exist_ok=False)
 subprocess.run(['git','init','--bare','-q',str(repo)],check=True)
 subprocess.run(['git','-C',str(repo),'remote','add','origin',url],check=True)
 cmd=['git','-c','gc.auto=0','-c','pack.threads=1','-C',str(repo),'fetch','--no-tags','--no-recurse-submodules','--filter=blob:none','--depth='+str(DEPTH),'origin',ref]
 display=[x if x!=str(repo) else '<isolated-bare-'+name+'>' for x in cmd]
 start=datetime.datetime.now(datetime.timezone.utc).isoformat();reason=None
 env=dict(os.environ,GIT_TERMINAL_PROMPT='0',GIT_NO_LAZY_FETCH='1',GIT_CONFIG_COUNT='1',GIT_CONFIG_KEY_0='http.followRedirects',GIT_CONFIG_VALUE_0='false')
 with (OUT/(name+'.stdout')).open('wb') as stdout,(OUT/(name+'.stderr')).open('wb') as stderr:
  process=subprocess.Popen(cmd,stdout=stdout,stderr=stderr,env=env,start_new_session=True);deadline=time.monotonic()+20
  while process.poll() is None:
   size=sum(p.stat().st_size for p in (repo/'objects').rglob('*') if p.is_file())
   errors=(OUT/(name+'.stderr')).read_bytes()
   if time.monotonic()>deadline:reason='20-second timeout'
   elif size>LIMIT:reason='object/pack byte cap exceeded'
   elif len(errors)>1024*1024:reason='diagnostic cap exceeded'
   elif b'filtering not recognized' in errors.lower() or b'filtering not supported' in errors.lower():reason='server filter unsupported'
   elif b'captcha' in errors.lower() or b'bot check' in errors.lower():reason='bot challenge; no interaction'
   if reason:
    try:os.killpg(process.pid,signal.SIGKILL)
    except ProcessLookupError:pass
    break
   time.sleep(.1)
  code=process.wait()
 files=[]
 for p in sorted((repo/'objects').rglob('*')):
  if p.is_file():files.append({'path':str(p.relative_to(repo)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
 total=sum(p['bytes'] for p in files)
 if total>LIMIT:reason='object/pack byte cap exceeded'
 def git(*args):
  r=subprocess.run(['git','-C',str(repo),*args],capture_output=True,env=env,timeout=5)
  return {'command':['git','-C','<isolated-bare-'+name+'>',*args],'exit_code':r.returncode,'stdout':r.stdout.decode(errors='replace'),'stdout_sha256':hashlib.sha256(r.stdout).hexdigest()}
 result={'schema_version':'wayne.history-fetch.v1','source_url':url,'command':display,'exit_code':code,'depth':DEPTH,'byte_limit':LIMIT,'object_bytes':total,'files':files,'ref':git('rev-parse','FETCH_HEAD^{commit}'),'shallow':(repo/'shallow').read_text().splitlines() if (repo/'shallow').exists() else [],'blocked_reason':reason,'relationship_status':'undetermined','update_status':'blocked'}
 (OUT/(name+'-fetch.json')).write_text(json.dumps(result,separators=(',',':'))+'\n')
 (OUT/(name+'-run.json')).write_text(json.dumps({'started_utc':start,'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'stdout_sha256':hashlib.sha256((OUT/(name+'.stdout')).read_bytes()).hexdigest(),'stderr_sha256':hashlib.sha256((OUT/(name+'.stderr')).read_bytes()).hexdigest()},indent=2)+'\n')
 print(name,code,reason,total,flush=True)

def main():
 OUT.mkdir(parents=True,exist_ok=True)
 if LAB.exists():raise SystemExit('Refuse another remote batch: isolated probe directory already exists')
 with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(lambda item:run(*item),SOURCES.items()))

if __name__=='__main__':main()
