import json, os, pathlib, subprocess, time
out=pathlib.Path.home()/'app-test-results';out.mkdir(exist_ok=True)
results={'cli':{},'gui':{}}
for name,cmd in {'python':['python3','--version'],'node':['node','--version'],'npm':['npm','--version'],'git':['git','--version'],'g++':['g++','--version'],'java':['java','-version'],'codex':['codex','--version'],'vscode':['code','--version'],'vscode_extensions':['code','--list-extensions']}.items():
 try:
  p=subprocess.run(cmd,capture_output=True,text=True,timeout=25)
  results['cli'][name]={'returncode':p.returncode,'output':(p.stdout+p.stderr)[:3000]}
 except Exception as e:results['cli'][name]={'error':str(e)}
for name,cmd in {'firefox':['firefox','about:blank'],'libreoffice':['libreoffice','--writer','--norestore'],'vlc':['vlc'],'clash-verge':['clash-verge'],'chatgpt':['chatgpt'],'vscode':['code','--new-window']}.items():
 try:
  f=open(out/(name+'.log'),'w');p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT)
  time.sleep(8)
  results['gui'][name]={'startup_returncode':p.poll()}
 except Exception as e:results['gui'][name]={'error':str(e)}
for name,result in results['gui'].items():
 p=out/(name+'.log')
 if p.exists():result['log_tail']=p.read_text(errors='replace')[-4000:]
results['processes']=subprocess.check_output(['ps','-u',str(os.getuid()),'-o','pid,comm,args'],text=True)
(out/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
