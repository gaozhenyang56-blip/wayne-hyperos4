"""Generic explicit memory-region consumers; no subsystem or status interpretation."""
from dataclasses import dataclass
from typing import Optional
from read_dtb_identity import read_tree, MAX_REFERENCE_EDGES
from dtb_phandle_index import _index_tree
from dtb_reserved_memory import _decode_reserved_tree

MAX_CONSUMERS = 65536


@dataclass(frozen=True)
class OptionalProperty:
    name: str
    presence: str
    structure_offset: Optional[int]
    value_offset: Optional[int]
    raw: Optional[bytes]
    strings: tuple


@dataclass(frozen=True)
class ConsumerEvidence:
    source_sha256: str
    source_path: str
    memory_region_structure_offset: int
    memory_region_value_offset: int
    memory_region_raw: bytes
    targets: tuple
    optional_properties: tuple


def _optional(properties, name, path):
    prop = properties.get(name)
    if prop is None:
        return OptionalProperty(name, 'absent', None, None, None, ())
    raw = bytes.fromhex(prop['hex'])
    if not raw or not raw.endswith(b'\0'):
        raise ValueError(path + ':' + name + ' missing terminal NUL')
    parts = raw[:-1].split(b'\0')
    if any(not p for p in parts) or (name == 'status' and len(parts) != 1):
        raise ValueError(path + ':' + name + ' empty element or invalid string count')
    strings = tuple(p.decode('ascii') for p in parts)
    return OptionalProperty(name, 'present', prop['structure_offset'], prop['value_offset'], raw, strings)


def collect_consumer_evidence(blob):
    """One snapshot; ordered immutable records returned only after every consumer passes."""
    tree = read_tree(blob)
    index = _index_tree(tree)
    consumers = [node for node in tree['nodes'].values() if 'memory-region' in node['properties']]
    if len(consumers) > MAX_CONSUMERS:
        raise ValueError('consumer count limit exceeded')
    total = 0
    for node in consumers:
        length = node['properties']['memory-region']['length']
        if not length or length % 4:
            raise ValueError(node['path'] + ':memory-region empty or malformed')
        total += length // 4
        if total > MAX_REFERENCE_EDGES:
            raise ValueError('aggregate consumer reference edge limit exceeded')
    results = []; cache = {}
    for node in consumers:
        props = node['properties']; path = node['path']; prop = props['memory-region']
        optional = tuple(_optional(props, name, path) for name in ('compatible', 'status', 'firmware-name'))
        targets = _decode_reserved_tree(tree, path, index=index, cache=cache)
        results.append(ConsumerEvidence(tree['sha256'], path, prop['structure_offset'], prop['value_offset'], bytes.fromhex(prop['hex']), targets, optional))
    return tuple(results)
