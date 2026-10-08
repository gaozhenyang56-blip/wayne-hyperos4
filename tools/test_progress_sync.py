#!/usr/bin/env python3
"""Reproduce a main-branch update between fetch and push in real local clones."""
import os
import pathlib
import subprocess
import tempfile
import ci_build_candidate as ci


def git(folder,*args):
    return subprocess.check_output(['git','-C',str(folder),*args],stderr=subprocess.STDOUT).decode()


def main():
    old_cwd=pathlib.Path.cwd()
    original_run=ci.run
    with tempfile.TemporaryDirectory(prefix='wayne-progress-race-') as directory:
        root=pathlib.Path(directory)
        origin=root/'origin.git'
        subprocess.run(['git','init','--bare','--initial-branch=main',str(origin)],check=True,stdout=subprocess.DEVNULL)
        clones=[]
        for name in ('runner','editor'):
            clone=root/name
            subprocess.run(['git','clone',str(origin),str(clone)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            git(clone,'config','user.name','Progress fixture')
            git(clone,'config','user.email','fixture@example.invalid')
            clones.append(clone)
        runner,editor=clones
        (runner/'cloud.md').write_text('cloud initial\n')
        git(runner,'add','cloud.md');git(runner,'commit','-m','initial');git(runner,'push','origin','main')
        git(editor,'pull','origin','main')
        (runner/'cloud.md').write_text('cloud initial\ncloud complete\n')
        git(runner,'add','cloud.md');git(runner,'commit','-m','cloud update')
        races=[]
        def racing_run(*args,**kwargs):
            original_run(*args,**kwargs)
            if args[:2]==('git','rebase') and not races:
                (editor/'editor.md').write_text('timestamped editor update\n')
                git(editor,'add','editor.md');git(editor,'commit','-m','concurrent MD update')
                git(editor,'push','origin','main')
                races.append(True)
        ci.run=racing_run
        os.chdir(runner)
        try:
            ci.push_progress()
            assert races==[True]
            assert git(origin,'show','main:cloud.md')=='cloud initial\ncloud complete\n'
            assert git(origin,'show','main:editor.md')=='timestamped editor update\n'
            assert git(origin,'rev-list','--count','main').strip()=='3'
            # A non-racing repeat must also succeed without extra commits.
            ci.run=original_run
            ci.push_progress()
            assert git(origin,'rev-list','--count','main').strip()=='3'
        finally:
            ci.run=original_run
            os.chdir(old_cwd)
    print('PASS: rejected concurrent push recovered; both updates retained; repeat is idempotent.')


if __name__=='__main__':main()
