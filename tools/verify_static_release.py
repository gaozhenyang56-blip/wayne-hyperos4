import hashlib,json,pathlib,subprocess,urllib.request
repo='gaozhenyang56-blip/wayne-hyperos4';tag='offline-static-20261009'
def get_json(endpoint):return json.loads(subprocess.check_output(['gh','api','repos/'+repo+'/'+endpoint],text=True))
r=get_json('releases/tags/'+tag)
if r['draft'] or not r['prerelease']:raise ValueError('Expected public experimental prerelease')
manifest_asset=next(a for a in r['assets'] if a['name']=='manifest.json')
manifest=json.loads(urllib.request.urlopen(manifest_asset['browser_download_url']).read())
if manifest['layout']!='stock-size-static' or manifest['requires_miku_installed'] or not manifest['preserve_partition_table']:raise ValueError('Wrong user layout')
ref=get_json('git/ref/tags/'+tag)
if ref['object']['sha']!=manifest['build_commit']:raise ValueError('Tag provenance mismatch')
folder=pathlib.Path('/tmp/static-public-assets');folder.mkdir(exist_ok=True)
checks=[]
for a in r['assets']:
    if not a.get('digest','').startswith('sha256:'):raise ValueError('Missing published digest')
    row={'name':a['name'],'size':a['size'],'sha256':a['digest'].split(':')[1],'url':a['browser_download_url']}
    if a['size']<1024*1024:
        content=urllib.request.urlopen(a['browser_download_url']).read();(folder/a['name']).write_bytes(content)
        if len(content)!=a['size'] or hashlib.sha256(content).hexdigest()!=row['sha256']:raise ValueError('Anonymous asset verification failed')
        row['anonymous_download_verified']=True
    checks.append(row)
if len(checks)!=5:raise ValueError('Expected five public assets')
sums={line.split()[1]:line.split()[0] for line in (folder/'SHA256SUMS').read_text().splitlines()}
for row in checks:
    if '.zip.' in row['name'] and sums[row['name']]!=row['sha256']:raise ValueError('Parts do not match public checksum file')
report={'success':True,'release_url':r['html_url'],'tag':tag,'build_commit':manifest['build_commit'],'layout':'stock-size-static','hardware_tested':False,'anonymous_small_assets_verified':True,'assets':checks}
pathlib.Path('artifacts/static-public-release-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
