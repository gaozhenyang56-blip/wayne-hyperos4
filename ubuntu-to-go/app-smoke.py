import json, os, pathlib, signal, subprocess, tempfile, time
out=pathlib.Path.home()/'app-test-results';out.mkdir(exist_ok=True)
results={'cli':{},'gui':{}}
for name,cmd in {'python':['python3','--version'],'node':['node','--version'],'npm':['npm','--version'],'git':['git','--version'],'g++':['g++','--version'],'java':['java','-version'],'codex':['codex','--version'],'vscode':['code','--version'],'vscode_extensions':['code','--list-extensions']}.items():
 try:
  p=subprocess.run(cmd,capture_output=True,text=True,timeout=25)
  results['cli'][name]={'returncode':p.returncode,'output':(p.stdout+p.stderr)[:3000]}
 except Exception as e:results['cli'][name]={'error':str(e)}
dev=pathlib.Path(tempfile.mkdtemp(prefix='dev-smoke-'))
(dev/'hello.c').write_text('#include <stdio.h>\nint main(void){puts("C_OK");return 0;}\n')
(dev/'hello.cpp').write_text('#include <iostream>\nint main(){std::cout<<"CPP_OK";return 0;}\n')
(dev/'Hello.java').write_text('class Hello {public static void main(String[] a){System.out.println("JAVA_OK");}}')
for name,cmd in {'c_compile':['gcc',str(dev/'hello.c'),'-o',str(dev/'hello-c')],'cpp_compile':['g++',str(dev/'hello.cpp'),'-o',str(dev/'hello-cpp')],'java_compile':['javac',str(dev/'Hello.java')],'python_venv':['python3','-m','venv',str(dev/'venv')],'node_execution':['node','-e','console.log("NODE_OK")']}.items():
 p=subprocess.run(cmd,capture_output=True,text=True,timeout=30)
 results['cli'][name]={'returncode':p.returncode,'output':p.stdout+p.stderr}
for name,cmd in {'c_execution':[str(dev/'hello-c')],'cpp_execution':[str(dev/'hello-cpp')],'java_execution':['java','-cp',str(dev),'Hello'],'venv_pip':[str(dev/'venv/bin/python'),'-m','pip','--version']}.items():
 try:
  p=subprocess.run(cmd,capture_output=True,text=True,timeout=30)
  results['cli'][name]={'returncode':p.returncode,'output':p.stdout+p.stderr}
 except Exception as e:results['cli'][name]={'error':str(e)}
for name,cmd in {'qq':['qq'],'firefox':['firefox','about:blank'],'libreoffice':['libreoffice','--writer','--norestore'],'vlc':['vlc'],'clash-verge':['clash-verge'],'chatgpt':['chatgpt'],'vscode':['code','--new-window']}.items():
 try:
  f=open(out/(name+'.log'),'w');p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
  time.sleep(8)
  results['gui'][name]={'startup_returncode':p.poll(),'processes':subprocess.check_output(['ps','-u',str(os.getuid()),'-o','pid,comm,args'],text=True)}
  if name!='vscode':
   try:os.killpg(p.pid,signal.SIGTERM)
   except ProcessLookupError:pass
 except Exception as e:results['gui'][name]={'error':str(e)}
for name,result in results['gui'].items():
 p=out/(name+'.log')
 if p.exists():result['log_tail']=p.read_text(errors='replace')[-4000:]
results['processes']=subprocess.check_output(['ps','-u',str(os.getuid()),'-o','pid,comm,args'],text=True)
(out/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
