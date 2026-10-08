#!/usr/bin/env python3
"""Validate ELF version checks against independently compiled positive/negative DSOs."""
import pathlib
import subprocess
import tempfile

from audit_native_versions import inspect, supplies


def main():
    with tempfile.TemporaryDirectory(prefix='wayne-version-fixtures-') as temporary:
        folder = pathlib.Path(temporary)
        source = folder/'provider.c'
        source.write_text('int demo(void) { return 42; }\n')
        providers = {}
        for version in ['V1', 'V2', None]:
            directory = folder/(version or 'plain')
            directory.mkdir()
            path = directory/'libfixture.so'
            command = ['cc', '-shared', '-fPIC', str(source), '-Wl,-soname,libfixture.so', '-o', str(path)]
            if version:
                script = directory/'versions.map'
                script.write_text(version + ' { global: demo; local: *; };\n')
                command.append('-Wl,--version-script=' + str(script))
            subprocess.run(command, check=True)
            providers[version] = inspect(path)

        consumer = folder/'consumer.c'
        consumer.write_text('extern int demo(void); int entry(void) { return demo(); }\n')
        consumer_so = folder/'consumer.so'
        subprocess.run(['cc', '-shared', '-fPIC', str(consumer), '-L'+str(folder/'V1'),
                        '-lfixture', '-o', str(consumer_so)], check=True)
        imported = inspect(consumer_so)
        assert ('demo', 'V1') in imported['required'], 'Consumer version requirement was lost'
        assert ('libfixture.so', 'V1') in imported['version_needs'], 'Version provider requirement was lost'
        assert supplies(providers['V1'], 'demo', 'V1'), 'Matching version rejected'
        assert not supplies(providers['V2'], 'demo', 'V1'), 'Wrong explicitly versioned export accepted'
        assert supplies(providers[None], 'demo', 'V1'), 'Android global version fallback rejected'
        assert not supplies(providers['V1'], 'missing_symbol', 'V1'), 'Missing symbol accepted'
        assert supplies(providers['V1'], 'demo', ''), 'Default version cannot satisfy unversioned import'

        hidden_source = folder/'nondefault.c'
        hidden_source.write_text('int internal(void) { return 7; }\n__asm__(".symver internal,demo@V1");\n')
        script = folder/'nondefault.map'
        script.write_text('V1 { global: demo; local: *; };\n')
        path = folder/'nondefault.so'
        subprocess.run(['cc', '-shared', '-fPIC', str(hidden_source),
                        '-Wl,--version-script='+str(script), '-o', str(path)], check=True)
        nondefault = inspect(path)
        assert supplies(nondefault, 'demo', 'V1'), 'Exact nondefault version rejected'
        assert not supplies(nondefault, 'demo', ''), 'Hidden nondefault version accepted as unversioned'
    print('PASS: versioned consumer, matching/wrong/missing export, global fallback, default/nondefault visibility')


if __name__ == '__main__':
    main()
