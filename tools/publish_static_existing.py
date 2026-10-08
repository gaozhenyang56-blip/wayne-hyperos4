#!/usr/bin/env python3
"""Recover a verified, already-uploaded static release without rebuilding images."""
import argparse
import ast
import hashlib
import json
import pathlib
import subprocess
import tempfile
import urllib.request
from package_static_candidate import check_reports

ROOT=pathlib.Path(__file__).resolve().parent.parent
REPO='gaozhenyang56-blip/wayne-hyperos4'
TAG='offline-static-20261009'

def api(path):
    return json.loads(subprocess.check_output(['gh','api','repos/'+REPO+'/'+path],text=True))

def source(commit,path):
    return urllib.request.urlopen('https://raw.githubusercontent.com/'+REPO+'/'+commit+'/'+path,timeout=60).read()

def expected_assets(candidate,generator):
    manifest=candidate['manifest']
    literals=[ast.literal_eval(n.value) for n in ast.walk(ast.parse(generator))
              if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='instructions' for t in n.targets)]
    if len(literals)!=1:raise ValueError('Expected one installation instruction literal')
    small={'manifest.json':(json.dumps(manifest,indent=2)+'\n').encode(),
           'INSTALL.txt':literals[0].encode(),
           'SHA256SUMS':''.join(v['sha256']+'  '+n+'\n' for n,v in candidate['parts'].items()).encode()}
    expected={**candidate['parts'],**{n:{'size':len(v),'sha256':hashlib.sha256(v).hexdigest()} for n,v in small.items()}}
    if len(expected)!=5:raise ValueError('Expected two ZIP parts and three small attachments')
    return expected

def validate_assets(release,expected):
    actual={a['name']:a for a in release['assets']}
    if len(actual)!=5 or set(actual)!=set(expected):raise ValueError('Release asset inventory mismatch')
    for name,record in expected.items():
        asset=actual[name]
        if asset['state']!='uploaded' or asset['size']!=record['size'] or asset.get('digest')!='sha256:'+record['sha256']:
            raise ValueError('Existing asset size/digest mismatch: '+name)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--publish',action='store_true');a=p.parse_args()
    head=api('commits/main')['sha']
    candidate=json.loads(source(head,'artifacts/static-candidate-package.json'));manifest=candidate['manifest']
    if manifest['device']!='wayne' or manifest['layout']!='stock-size-static' or manifest['requires_miku_installed']:
        raise ValueError('Wrong target layout or installation prerequisite')
    if not manifest['preserve_partition_table'] or manifest['hardware_tested']:raise ValueError('Invalid experimental scope')
    archive=json.loads(source(head,'research/static-wayne/archive-check.json'))
    if not archive['success'] or not archive['image_hashes_match_manifest']:raise ValueError('Archive readback failed')
    inputs=json.loads(source(head,'research/static-wayne/build-input.json'))
    if inputs['source_commit']!=manifest['build_commit'] or inputs['images']!={n:r['sha256'] for n,r in manifest['images'].items()}:
        raise ValueError('Image build provenance mismatch')
    with tempfile.TemporaryDirectory() as directory:
        root=pathlib.Path(directory);folder=root/'research/static-wayne';folder.mkdir(parents=True)
        for name in ('image-check.json','boot-check.json','system-content-check.json','system-metadata-check.json',
                     'vendor-content-check.json','vendor-metadata-check.json','native-versions.json','vintf-check.json'):
            (folder/name).write_bytes(source(head,'research/static-wayne/'+name))
        reports=check_reports(root)
        if reports['boot-check.json']['sha256']!=manifest['images']['boot.img']['sha256']:raise ValueError('Boot report mismatch')
    expected=expected_assets(candidate,source(manifest['build_commit'],'tools/package_static_candidate.py').decode())
    matching=[r for r in api('releases?per_page=100') if r['tag_name']==TAG]
    if len(matching)!=1:raise ValueError('Expected one existing release')
    release=matching[0];validate_assets(release,expected)
    print(json.dumps({'all_five_uploaded_assets_verified':True,'draft':release['draft'],
                      'build_commit':manifest['build_commit'],'assets':expected},indent=2))
    if not a.publish:return
    subprocess.run(['gh','release','edit',TAG,'--repo',REPO,'--draft=false','--prerelease','--latest=false',
                    '--target',manifest['build_commit']],check=True)
    release=api('releases/tags/'+TAG);validate_assets(release,expected)
    if release['draft'] or not release['prerelease'] or not release['html_url'].endswith('/'+TAG):
        raise ValueError('Expected public experimental release with canonical URL')
    ref=api('git/ref/tags/'+TAG)['object']
    if ref['type']=='tag':ref=api('git/tags/'+ref['sha'])['object']
    if ref['sha']!=manifest['build_commit']:raise ValueError('Published tag points at wrong source')
    report={'url':release['html_url'],'tag':TAG,'draft':False,'prerelease':True,
            'build_commit':manifest['build_commit'],'workflow_commit':inputs['workflow_commit'],
            'assets_verified':True,'assets':expected,'layout':'stock-size-static',
            'requires_miku_installed':False,'hardware_tested':False,
            'publication_method':'recover-verified-existing-assets','verification_commit':head,
            'full_build_workflow_run_id':37817225905}
    (ROOT/'artifacts/static-release-publication.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Published verified static experiment:',release['html_url'])

if __name__=='__main__':main()
