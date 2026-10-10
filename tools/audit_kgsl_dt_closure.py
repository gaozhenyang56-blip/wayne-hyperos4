#!/usr/bin/env python3
"""Textual include closure only: no CPP/DTC, bindings or hardware validation."""
import datetime
import hashlib
import json
import pathlib
import posixpath
import re
from audit_graphics_contract import assess

ROOT=pathlib.Path(__file__).resolve().parent.parent
OUT=ROOT/'research/kgsl-dt-stage'


def closure(entry,files):
    visited=set();missing=set();witnesses=[];cycles=[];requests=[]
    def visit(path,stack):
        if path in stack:
            cycles.append(path);return
        if path in visited:return
        if path not in files:
            missing.add(path);return
        visited.add(path)
        # Ignore comments so a commented include/node is not treated as active.
        text=re.sub(r'/\*.*?\*/|//[^\n]*','',files[path],flags=re.S)
        for line_number,line in enumerate(text.splitlines(),1):
            if re.search(r'kgsl|gpu@|gpu\s*[:{]|clocks\s*=|power-domains\s*=|[\w-]+-supply\s*=|iommus\s*=',line):
                witnesses.append({'source':path,'comment_stripped_line':line_number,'text':line.strip()})
        for match in re.finditer(r'^\s*#include\s*["<]([^">]+)[">]',text,re.M):
            child=posixpath.normpath(posixpath.join(posixpath.dirname(path),match.group(1)))
            if child not in files:
                requests.append({'including_source':path,'include_token':match.group(1),
                                 'relative_candidate':child,'compiler_include_search_roots_verified':False})
            visit(child,stack+[path])
    visit(entry,[])
    kgsl_seen=any('kgsl' in row['text'] for row in witnesses)
    return {'entry':entry,'visited':sorted(visited),'missing_includes':sorted(missing),'cycles':cycles,
            'textual_closure_complete':not missing and not cycles,
            'kgsl_text_seen':kgsl_seen,
            'kgsl_absence_proven':False,
            'kgsl_presence_scope':'text witness only' if kgsl_seen else 'not seen; absence not proven',
            'unresolved_include_requests':requests,
            'missing_paths_scope':'relative lookup candidates only, not proven original include-search locations',
            'unscoped_property_witnesses':witnesses,
            'gpu_node_property_ownership_verified':False,'cpp_dtc_or_phandle_resolution_performed':False}


def main():
    OUT.mkdir(exist_ok=True)
    base=ROOT/'research/allocator-implementation'
    registry=[]
    for name in ['dts-sources.json','dtsi-sources.json','common-dtsi-source.json']:
        value=json.loads((base/name).read_text());registry.extend(value if isinstance(value,list) else [value])
    files={};sources=[]
    for row in registry:
        logical=row['url'].split(row['commit']+'/',1)[1]
        path=base/pathlib.PurePosixPath(logical).name
        data=path.read_bytes()
        assert hashlib.sha256(data).hexdigest()==row['sha256']
        # Jasmine source exists as comparison evidence, never as target input.
        if 'jasmine' not in path.name:files[logical]=data.decode()
        sources.append({**row,'local_path':str(path.relative_to(ROOT)),
                        'used_as_downstream_wayne_input':'jasmine' not in path.name})
    downstream=closure('arch/arm/boot/dts/qcom/sdm660-mtp-wayne.dts',files)
    scaffold=ROOT/'config/sdm660-xiaomi-wayne-6.6.dts'
    mainline=closure('arch/arm64/boot/dts/qcom/sdm660-xiaomi-wayne.dts',
                     {'arch/arm64/boot/dts/qcom/sdm660-xiaomi-wayne.dts':scaffold.read_text()})
    sample=json.loads((ROOT/'research/gpu-allocator-stage/graphics-contract.json').read_text())
    profile=json.loads((ROOT/'config/kernel-6.6-graphics-profile.json').read_text())
    contract=assess(sample['graphics_files'],profile)
    assert contract['legacy_pairing_rejected']
    report={'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'target':'China wayne/SDM660, stock static partitions; not jasmine or Miku baseline',
        'sources':sources,'downstream_wayne':downstream,'mainline_scaffold':mainline,
        'scaffold_sha256':hashlib.sha256(scaffold.read_bytes()).hexdigest(),
        'mainline_wayne_board_validated':False,'current_user_dtb_vendor_logs_available':False,
        'vendor_source_role':'non-Miku wayne comparison sample only; not current user vendor',
        'vendor_contract':contract,
        'remaining':['actual wayne GPU node and full matching include closure',
                     'regulator/clock/power-domain phandles and provider nodes',
                     'IOMMU attachment/context and matching bindings',
                     'matched kernel driver/ioctl ABI; a DT node cannot provide KGSL ioctls',
                     'firmware request names from matched driver/logs, not guesses',
                     'runtime node labels, GPU initialization and display integration'],
        'hardware_values_applied':False,'kernel_compiled':False,'new_boot_created':False,
        'gpu_verified':False,'display_verified':False,'bootable_verified':False,'hardware_tested':False}
    (OUT/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Incomplete include closures recorded; no KGSL absence/hardware verdict; legacy vendor pairing rejected.')


if __name__=='__main__':main()
