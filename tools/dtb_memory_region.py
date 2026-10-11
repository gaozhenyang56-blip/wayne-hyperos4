"""Decode only memory-region pure phandle lists; no memory or device semantics."""
from dataclasses import dataclass
import struct
from read_dtb_identity import read_tree, MAX_REFERENCE_EDGES
from dtb_phandle_index import _index_tree


@dataclass(frozen=True)
class ReferenceEdge:
    source_sha256: str
    source_path: str
    property_name: str
    cell_index: int
    value_offset: int
    phandle: int
    target_path: str


def decode_memory_region(blob, source_path, property_name='memory-region'):
    """All-or-nothing tuple for one explicitly requested list, bounded to 65536 edges."""
    if property_name != 'memory-region':
        raise ValueError('unsupported reference property: ' + str(property_name))
    tree = read_tree(blob)
    index = _index_tree(tree)
    if not isinstance(source_path, str) or source_path not in tree['nodes']:
        raise ValueError('source node missing or noncanonical: ' + str(source_path))
    prop = tree['nodes'][source_path]['properties'].get(property_name)
    if prop is None:
        raise ValueError('memory-region property missing: ' + source_path)
    length = prop['length']
    if not length or length % 4 or length // 4 > MAX_REFERENCE_EDGES:
        raise ValueError('memory-region empty, malformed length or edge limit exceeded: ' + source_path)
    payload = bytes.fromhex(prop['hex'])
    edges = []
    for cell_index, (value,) in enumerate(struct.iter_unpack('>I', payload)):
        offset = prop['value_offset'] + cell_index * 4
        try:
            target = index.resolve(value)
        except ValueError as error:
            raise ValueError('%s:memory-region cell=%d offset=%d: %s' % (source_path, cell_index, offset, error)) from None
        edges.append(ReferenceEdge(index.source_sha256, source_path, property_name, cell_index, offset, value, target))
    return tuple(edges)
