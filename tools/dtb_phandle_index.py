"""Unique phandle declarations only; no reference or board semantics."""
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping
import struct
from read_dtb_identity import read_tree


def valid_query(value):
    if type(value) is not int or not 0 < value < 0xffffffff:
        raise ValueError('phandle query must be a non-reserved uint32')


@dataclass(frozen=True)
class PhandleIndex:
    source_sha256: str
    targets: Mapping[int, str]

    def resolve(self, value):
        """One bounded map lookup; no traversal or reference decoding."""
        valid_query(value)
        try:
            return self.targets[value]
        except KeyError:
            raise ValueError('phandle target missing: 0x%08x' % value) from None


def build_phandle_index(blob):
    """Validate the entire immutable snapshot before publishing any index."""
    tree = read_tree(blob)
    targets = {}
    for path, node in tree['nodes'].items():
        declarations = []
        for name in ('phandle', 'linux,phandle'):
            prop = node['properties'].get(name)
            if prop is None:
                continue
            context = '%s:%s at offset %d' % (path, name, prop['value_offset'])
            if prop['length'] != 4:
                raise ValueError('phandle length must be exactly four bytes: ' + context)
            value = struct.unpack('>I', bytes.fromhex(prop['hex']))[0]
            if value in (0, 0xffffffff):
                raise ValueError('reserved phandle: ' + context)
            declarations.append(value)
        if not declarations:
            continue
        if len(set(declarations)) != 1:
            raise ValueError('conflicting phandle aliases: ' + path)
        value = declarations[0]
        if value in targets:
            raise ValueError('duplicate phandle across nodes: %s and %s' % (targets[value], path))
        targets[value] = path
    return PhandleIndex(tree['sha256'], MappingProxyType(targets))
