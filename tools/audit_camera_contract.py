#!/usr/bin/env python3
"""Selected camera evidence gate. Properties are not ABI or hardware proof."""
import argparse
import hashlib
import json
import pathlib


def assess_inventory(paths):
    groups={'camera_hal':[], 'camera_config':[]}
    for path in paths:
        p=pathlib.PurePosixPath(path);name=p.name
        if name.startswith('camera.') and name.endswith('.so') and 'hw' in p.parts:
            groups['camera_hal'].append(path)
        if name.endswith('.xml') and (name.startswith('camera') or 'camera' in p.parts):
            groups['camera_config'].append(path)
    missing=[key for key,value in groups.items() if not value]
    return {'selected_inventory':groups,'missing_evidence_categories':missing,
            'evidence_gate_rejected':bool(missing),'contract_verified':False,
            'hardware_tested':False,'camera_verified':False,'recording_verified':False,
            'scope':'Filename presence only, not HAL version, XML semantics, ioctl or media graph. Alternate naming requires inventory review.'}


def collect_text(root,manifest):
    rows=[]
    for item in manifest['extracted']:
        path=item['path'];data=(root/path).read_bytes()
        if hashlib.sha256(data).hexdigest()!=item['sha256']:raise ValueError('Sample hash changed: '+path)
        if path not in ('build.prop','etc/init/hw/init.qcom.rc'):continue
        lines=[{'line':n,'text':line} for n,line in enumerate(data.decode(errors='replace').splitlines(),1)
               if any(word in line for word in ('camera','/dev/media','/dev/video','v4l-subdev'))]
        rows.append({'path':path,'sha256':item['sha256'],'lines':lines})
    return rows


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('vendor',type=pathlib.Path);p.add_argument('manifest',type=pathlib.Path);p.add_argument('output',type=pathlib.Path)
    args=p.parse_args();manifest=json.loads(args.manifest.read_text())
    text=collect_text(args.vendor,manifest)
    report={'sample_role':'Non-Miku wayne comparison only; current user vendor unknown',
            'inventory':assess_inventory([x['path'] for x in manifest['extracted']]),'text_evidence':text,
            'absence_meaning':'Not selected/extracted, not absent from full vendor or proof of unavailable hardware',
            'device_node_requirements':'Not established without HAL/configuration/runtime evidence'}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report['inventory'],indent=2))
    if report['inventory']['evidence_gate_rejected']:raise SystemExit(2)

if __name__=='__main__':main()
