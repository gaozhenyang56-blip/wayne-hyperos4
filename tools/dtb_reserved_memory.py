"""Decode referenced direct reserved-memory children only; no address qualification."""
from dataclasses import dataclass
import struct
from read_dtb_identity import read_tree
from dtb_memory_region import ReferenceEdge, _decode_tree


@dataclass(frozen=True)
class ReservedTarget:
    edge: ReferenceEdge
    address_cells: int
    size_cells: int
    reg: tuple
    reg_offsets: tuple
    no_map: bool
    reusable: bool


def decode_reserved_memory(blob, source_path):
    """All-or-nothing frozen evidence on the same validated immutable byte snapshot."""
    return _decode_reserved_tree(read_tree(blob), source_path)


def _decode_reserved_tree(tree, source_path, index=None, cache=None):
    edges = _decode_tree(tree, source_path, index=index)
    parent = tree['nodes'].get('/reserved-memory')
    if parent is None:
        raise ValueError('/reserved-memory missing')
    props = parent['properties']
    def cells(name):
        prop = props.get(name)
        if prop is None or prop['length'] != 4:
            raise ValueError('/reserved-memory:' + name + ' must be one explicit BE32 cell')
        value = struct.unpack('>I', bytes.fromhex(prop['hex']))[0]
        if value not in (1, 2):
            raise ValueError('/reserved-memory:' + name + ' unsupported width')
        return value
    ac, sc = cells('#address-cells'), cells('#size-cells')
    if 'ranges' not in props or props['ranges']['length'] != 0:
        raise ValueError('/reserved-memory:ranges must exist and be empty')
    stride = (ac + sc) * 4
    cache = {} if cache is None else cache
    results = []
    for edge in edges:
        path = edge.target_path
        if path.rsplit('/', 1)[0] != '/reserved-memory':
            raise ValueError('target must be a direct /reserved-memory child: ' + path)
        if path not in cache:
            properties = tree['nodes'][path]['properties']
            reg = properties.get('reg')
            if reg is None or not reg['length'] or reg['length'] % stride:
                raise ValueError(path + ':reg missing/empty/malformed tuple length')
            flags = []
            for name in ('no-map', 'reusable'):
                prop = properties.get(name)
                if prop is not None and prop['length'] != 0:
                    raise ValueError(path + ':' + name + ' must be a zero-length boolean')
                flags.append(prop is not None)
            if all(flags):
                raise ValueError(path + ':no-map/reusable conflict')
            payload = bytes.fromhex(reg['hex']); values = []; offsets = []
            for pos in range(0, len(payload), stride):
                boundary = pos + ac * 4
                address = int.from_bytes(payload[pos:boundary], 'big')
                size = int.from_bytes(payload[boundary:pos + stride], 'big')
                values.append((address, size))
                offsets.append((reg['value_offset'] + pos, reg['value_offset'] + boundary))
            cache[path] = (tuple(values), tuple(offsets), *flags)
        values, offsets, no_map, reusable = cache[path]
        results.append(ReservedTarget(edge, ac, sc, values, offsets, no_map, reusable))
    return tuple(results)
