#!/usr/bin/env python3
"""Fail closed on incomplete selected audio evidence; never infer hardware absence."""
import argparse
import hashlib
import json
import pathlib


def assess_inventory(paths):
    groups={'audio_hal':[], 'mixer_paths':[], 'audio_platform_info':[]}
    for path in paths:
        name=pathlib.PurePosixPath(path).name
        if name.startswith('audio.primary.') and name.endswith('.so'):groups['audio_hal'].append(path)
        if name.startswith('mixer_paths') and name.endswith('.xml'):groups['mixer_paths'].append(path)
        if name.startswith('audio_platform_info') and name.endswith('.xml'):groups['audio_platform_info'].append(path)
    missing=[key for key,value in groups.items() if not value]
    return {'selected_inventory':groups,'missing_evidence_categories':missing,
            'evidence_gate_rejected':bool(missing),'contract_verified':False,
            'hardware_tested':False,'audio_verified':False,'calls_verified':False,
            'scope':'Selected-file presence only, not ELF/XML semantics, ALSA mapping, HAL version or runtime compatibility'}


def collect_text(root,manifest):
    rows=[]
    for item in manifest['extracted']:
        path=item['path'];data=(root/path).read_bytes()
        if hashlib.sha256(data).hexdigest()!=item['sha256']:raise ValueError('Sample hash changed: '+path)
        if path not in ('build.prop','etc/init/hw/init.qcom.rc'):continue
        lines=[{'line':number,'text':line} for number,line in enumerate(data.decode(errors='replace').splitlines(),1)
               if any(word in line for word in ('audio','/dev/snd','/proc/asound','/sys/kernel/wdsp','/sys/kernel/wcd'))]
        rows.append({'path':path,'sha256':item['sha256'],'lines':lines})
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('vendor',type=pathlib.Path);parser.add_argument('manifest',type=pathlib.Path)
    parser.add_argument('output',type=pathlib.Path);args=parser.parse_args()
    manifest=json.loads(args.manifest.read_text())
    text=collect_text(args.vendor,manifest)
    report={'sample_role':'Non-Miku wayne comparison only; current user vendor unknown',
            'inventory':assess_inventory([item['path'] for item in manifest['extracted']]),'text_evidence':text,
            'absence_meaning':'Not selected/extracted; not proof of absent files in full vendor or unavailable hardware'}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report['inventory'],indent=2))
    if report['inventory']['evidence_gate_rejected']:raise SystemExit(2)

if __name__=='__main__':main()
