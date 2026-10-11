"""Bounded v17 FDT reader: root identity only, no board adaptation or overlays."""
import struct

MAX_SIZE = 8 * 1024 * 1024


def read_identity(blob):
    def reject(message):
        raise ValueError('DTB: ' + message)
    if not 40 <= len(blob) <= MAX_SIZE:
        reject('size outside supported bounds')
    magic, total, off_s, off_n, off_r, version, last, cpu, size_n, size_s = struct.unpack_from('>10I', blob)
    if magic != 0xd00dfeed or total != len(blob) or version != 17 or last != 16:
        reject('magic/total/version unsupported')
    if off_s % 4 or off_r % 8 or size_s % 4:
        reject('unaligned structure/reservation')
    regions = [(0, 40), (off_s, off_s + size_s), (off_n, off_n + size_n)]
    if not size_s or not size_n or any(a < 40 or b > total for a, b in regions[1:]):
        reject('block offsets/lengths invalid')
    if off_r < 40 or off_r + 16 > total:
        reject('reservation offset invalid')
    pos = off_r
    for _ in range(4096):
        if pos + 16 > total or any(pos < b and pos + 16 > a for a, b in regions):
            reject('unterminated/overlapping reservation map')
        address, length = struct.unpack_from('>QQ', blob, pos); pos += 16
        if address == length == 0:
            break
        if not length or address + length > 2**64:
            reject('invalid reservation range')
    else:
        reject('reservation count exceeded')
    regions.append((off_r, pos))
    ordered = sorted(regions)
    if any(a[1] > b[0] for a, b in zip(ordered, ordered[1:])):
        reject('overlapping blocks')
    strings = blob[off_n:off_n + size_n]
    stream = blob[off_s:off_s + size_s]
    pos = 0; stack = []; seen_root = False; closed_root = False; props = {}; nodes = set()
    def word():
        nonlocal pos
        if pos + 4 > len(stream): reject('truncated token/header')
        value = struct.unpack_from('>I', stream, pos)[0]; pos += 4
        return value
    def align():
        nonlocal pos
        end = (pos + 3) & ~3
        if end > len(stream) or any(stream[pos:end]): reject('invalid padding')
        pos = end
    while pos < len(stream):
        token = word()
        if token == 1:
            end = stream.find(b'\0', pos)
            if end < 0: reject('unterminated node name')
            name = stream[pos:end].decode('ascii'); pos = end + 1; align()
            if not stack:
                if seen_root or name: reject('invalid/multiple root')
                seen_root = True
            else:
                if not name or '/' in name: reject('invalid child name')
                stack[-1]['child'] = True
            path = tuple(n['name'] for n in stack) + (name,)
            if path in nodes or len(stack) >= 128: reject('duplicate node/depth exceeded')
            nodes.add(path); stack.append({'name': name, 'props': set(), 'child': False})
        elif token == 2:
            if not stack: reject('unbalanced END_NODE')
            stack.pop()
            if not stack: closed_root = True
        elif token == 3:
            if not stack or stack[-1]['child']: reject('property outside node/after child')
            length = word(); offset = word()
            if offset >= len(strings) or (offset and strings[offset - 1] != 0): reject('invalid property name offset')
            end = strings.find(b'\0', offset)
            if end < 0: reject('unterminated property name')
            name = strings[offset:end].decode('ascii')
            if not name or name in stack[-1]['props']: reject('empty/duplicate property')
            stack[-1]['props'].add(name)
            if pos + length > len(stream): reject('truncated property')
            value = stream[pos:pos + length]; pos += length; align()
            if len(stack) == 1 and name in ('model', 'compatible'): props[name] = value
        elif token == 4:
            continue
        elif token == 9:
            if stack or not closed_root or pos != len(stream): reject('invalid END/trailing tokens')
            break
        else:
            reject('unknown token')
    else:
        reject('missing END')
    values = {}
    for name in ('model', 'compatible'):
        value = props.get(name, b'')
        if not value or value[-1:] != b'\0': reject('missing/unterminated identity')
        parts = value[:-1].split(b'\0')
        if any(not p for p in parts) or (name == 'model' and len(parts) != 1): reject('invalid identity string list')
        decoded = [p.decode('ascii') for p in parts]
        if any(any(ord(c) < 32 or ord(c) > 126 for c in p) for p in decoded): reject('invalid identity characters')
        values[name] = decoded[0].strip() if name == 'model' else decoded
    values['dtb_header'] = {'version': version, 'last_comp_version': last, 'totalsize': total, 'boot_cpuid_phys': cpu}
    return values
