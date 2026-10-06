#!/usr/bin/env python3
"""Compile donor platform CIL with the wayne vendor policy for offline checking."""
import argparse
import hashlib
import json
import pathlib
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('system_root', type=pathlib.Path)
    parser.add_argument('vendor_root', type=pathlib.Path)
    parser.add_argument('output', type=pathlib.Path)
    parser.add_argument('--secilc', default='tools/local/usr/bin/secilc')
    parser.add_argument('--runtime-mode', action='store_true',
                        help='Use Android init runtime -N option; does not pass strict neverallow checking')
    args = parser.parse_args()
    version = (args.vendor_root/'etc/selinux/plat_sepolicy_vers.txt').read_text().strip()
    inputs = []
    for partition, prefix in [('system','plat'),('system_ext','system_ext'),('product','product')]:
        folder = args.system_root/partition/'etc/selinux'
        policy = folder/(prefix+'_sepolicy.cil')
        if policy.exists():
            inputs.append(policy)
        mapping = folder/'mapping'/(version+'.cil')
        if not mapping.exists():
            raise ValueError('Missing mapping '+str(mapping))
        inputs.append(mapping)
        compat = folder/'mapping'/(version+'.compat.cil')
        if compat.exists():
            inputs.append(compat)
    for name in ['plat_pub_versioned.cil','vendor_sepolicy.cil']:
        inputs.append(args.vendor_root/'etc/selinux'/name)
    args.output.mkdir(parents=True,exist_ok=True)
    command = [args.secilc,'-m','-M','true','-G','-c','30',
               '-o',str(args.output/'policy.bin'),'-f',str(args.output/'file_contexts.generated')]
    if args.runtime_mode:
        command.append('-N')
    command.extend(str(p) for p in inputs)
    result = subprocess.run(command, capture_output=True, text=True)
    (args.output/'compiler.log').write_text(result.stdout+result.stderr)
    report = {'vendor_policy_version':version,'policy_binary_version':30,
              'command':command,'exit_code':result.returncode,
              'neverallow_check_disabled':args.runtime_mode,
              'inputs':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
              'success':result.returncode==0}
    (args.output/'policy-check.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'success':report['success'],'exit_code':result.returncode}))
    raise SystemExit(result.returncode)


if __name__=='__main__':
    main()
