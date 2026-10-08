#!/usr/bin/env python3
"""Audit transitive ELF symbols using runtime APEX bionic, without namespace claims."""
import argparse
import datetime
import functools
import hashlib
import json
import pathlib
import re
import subprocess


@functools.lru_cache(None)
def inspect(path):
    header = path.read_bytes()[:20]
    if header[:4] != b'\x7fELF':
        raise ValueError('Not ELF: ' + str(path))
    dynamic = subprocess.check_output(['readelf', '-dW', str(path)], text=True)
    symbols = subprocess.check_output(['readelf', '--dyn-syms', '-W', str(path)], text=True)
    versions = subprocess.check_output(['readelf', '--version-info', '-W', str(path)], text=True)
    required, unversioned, versioned, global_exports = set(), set(), set(), set()
    for row in symbols.splitlines():
        match = re.match(r'^\s*\d+:\s+\S+\s+\d+\s+.+?\s+(GLOBAL|WEAK|LOCAL)\s+(\S+)\s+(\S+)\s+(\S+)', row)
        if not match:
            continue
        binding, visibility, section, raw = match.groups()
        name, separator, version = raw.replace('@@', '@').partition('@')
        if section == 'UND' and binding == 'GLOBAL':
            required.add((name, version if separator else ''))
        elif section != 'UND' and binding in ('GLOBAL', 'WEAK') and visibility in ('DEFAULT', 'PROTECTED'):
            if not separator:
                global_exports.add(name)
            if not separator or '@@' in raw:
                unversioned.add(name)
            if separator:
                versioned.add((name, version))
    definitions, needs = set(), []
    section, provider = '', None
    for row in versions.splitlines():
        if row.startswith('Version definition section'):
            section = 'definitions'
        elif row.startswith('Version needs section'):
            section = 'needs'
        elif row.startswith('Version symbols section'):
            section = 'symbols'
        name = re.search(r'\bName: (\S+)', row)
        if section == 'definitions' and name:
            definitions.add(name.group(1))
        elif section == 'needs':
            file = re.search(r'\bFile: (\S+)', row)
            if file:
                provider = file.group(1)
            if name:
                needs.append((provider, name.group(1)))
    return {'class': header[4], 'needed': re.findall(r'\(NEEDED\).*?\[(.*?)\]', dynamic),
            'required': required, 'unversioned': unversioned, 'versioned': versioned,
            'definitions': definitions, 'version_needs': needs, 'global_exports': global_exports}


def supplies(info, name, version):
    if not version:
        return name in info['unversioned']
    if version in info['definitions']:
        return (name, version) in info['versioned']
    # AOSP find_verdef_version_index returns kVersymGlobal for an absent version.
    return name in info['global_exports']


def audit(system, vendor, runtime, targets):
    libraries = {}
    for folder in [vendor, system/'system', system/'system_ext', system/'product']:
        for path in sorted(folder.rglob('*.so')):
            if path.is_symlink() or not path.is_file() or 'hwasan' in path.parts:
                continue
            with path.open('rb') as stream:
                header = stream.read(5)
            if header[:4] == b'\x7fELF':
                libraries.setdefault((header[4], path.name), []).append(path)
    for cls, directory in [(1, 'lib'), (2, 'lib64')]:
        for path in sorted((runtime/directory/'bionic').glob('*.so')):
            if inspect(path)['class'] != cls:
                raise ValueError('APEX ABI mismatch: ' + str(path))
            libraries[(cls, path.name)] = [path]
    linkers = {1: runtime/'bin/linker', 2: runtime/'bin/linker64'}
    for cls, path in linkers.items():
        if not path.is_file() or inspect(path)['class'] != cls:
            raise ValueError('Missing or wrong-ABI APEX linker: ' + str(path))

    def provider(consumer, name):
        candidates = libraries.get((inspect(consumer)['class'], name), [])
        if not candidates:
            return None
        if consumer.is_relative_to(system) or consumer.is_relative_to(runtime):
            return next((p for p in candidates if p.is_relative_to(system) or p.is_relative_to(runtime)), candidates[0])
        return candidates[0]

    @functools.lru_cache(None)
    def closure(start):
        visited, queue, missing = set(), [start], []
        while queue:
            path = queue.pop()
            if path in visited:
                continue
            visited.add(path)
            info = inspect(path)
            for name in info['needed']:
                selected = provider(path, name)
                if selected:
                    queue.append(selected)
                else:
                    missing.append({'consumer': str(path), 'library': name})
        return visited, missing

    results, all_inputs = [], set()
    for target in targets:
        root = vendor/target
        if not root.is_file():
            results.append({'target': target, 'status': 'not_present'})
            continue
        scope, missing = closure(root)
        linker = linkers[inspect(root)['class']]
        all_inputs.update(scope | {linker})
        unresolved, version_fallbacks = [], []
        for consumer in sorted(scope):
            reachable, _ = closure(consumer)
            # Process entry exports and the actual runtime linker may satisfy callbacks.
            providers = reachable | {root, linker}
            info = inspect(consumer)
            for name, version in sorted(info['required']):
                if not any(supplies(inspect(path), name, version) for path in providers):
                    unresolved.append({'consumer': str(consumer), 'symbol': name, 'version': version or None})
            for dependency, version in info['version_needs']:
                selected = provider(consumer, dependency)
                if selected and version not in inspect(selected)['definitions']:
                    version_fallbacks.append({'consumer': str(consumer), 'dependency': dependency,
                                             'requested_version': version, 'selected_provider': str(selected),
                                             'rule': 'AOSP global symbol fallback; each required symbol still checked'})
        results.append({'target': target, 'elf_class': inspect(root)['class'],
                        'inspected_libraries': len(scope), 'missing_dependency_files': missing,
                        'unresolved_required_symbols_in_selected_scope': unresolved,
                        'dependency_version_fallbacks': version_fallbacks,
                        'selected_dependency_closure': [str(p) for p in sorted(scope)],
                        'runtime_linker': str(linker)})
    return {'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'method': 'partition-aware filename inventory, actual runtime APEX bionic, per-consumer transitive scope',
            'runtime_compatibility_proven': False, 'namespace_compatibility_proven': False,
            'limitations': ['Android generated linker namespaces not evaluated',
                            'dlopen dependencies and process-wide external scopes not exhaustively modeled',
                            'Other APEX payloads not included',
                            'Partition preference may differ from actual namespace provider preference',
                            'AOSP version lookup rule is a reference; community linker patches not fully audited',
                            'Unresolved inventory symbols require investigation, not automatic binary patches'],
            'inputs': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(all_inputs)},
            'results': results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('system', type=pathlib.Path)
    parser.add_argument('vendor', type=pathlib.Path)
    parser.add_argument('runtime', type=pathlib.Path)
    parser.add_argument('output', type=pathlib.Path)
    args = parser.parse_args()
    targets = ['lib/hw/camera.sdm660.so', 'lib/hw/android.hardware.camera.provider@2.4-impl.so',
               'bin/hw/android.hardware.camera.provider@2.4-service',
               'bin/hw/android.hardware.graphics.composer@2.1-service']
    report = audit(args.system, args.vendor, args.runtime, targets)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps([{'target': r['target'], 'libraries': r.get('inspected_libraries'),
                       'missing': len(r.get('missing_dependency_files', [])),
                       'unresolved': len(r.get('unresolved_required_symbols_in_selected_scope', [])),
                       'version_fallbacks': len(r.get('dependency_version_fallbacks', []))}
                      for r in report['results']], indent=2))


if __name__ == '__main__':
    main()
