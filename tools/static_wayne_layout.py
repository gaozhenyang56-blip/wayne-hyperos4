"""Static wayne mount transformations; never resize or repurpose partitions."""

def static_fstab(source):
    output=['# wayne stock-size static layout; system/product/system_ext are merged.']
    seen=set()
    for line in source.splitlines():
        if not line.strip() or line.lstrip().startswith('#'):continue
        fields=line.split()
        if len(fields)==4 and fields[1] in ('/boot','/recovery') and fields[2]=='emmc':fields.append('defaults')
        if len(fields)!=5:raise ValueError('Unexpected fstab row: '+line)
        device,mount,fs,options,flags=fields
        if mount in ('/product','/system_ext','/metadata') or device.endswith('/rawdump'):continue
        if mount in ('/system','/vendor'):
            if fs!='erofs':continue
            device='/dev/block/bootdevice/by-name/'+mount[1:]
            flags=','.join(x for x in flags.split(',') if x!='logical')
            seen.add(mount)
        if 'logical' in flags.split(',') or 'formattable' in flags.split(','):
            raise ValueError('Unexpected logical or formattable mount')
        output.append(' '.join((device,mount,fs,options,flags)))
    if seen!={'/system','/vendor'}:raise ValueError('Expected system/vendor EROFS mounts')
    return '\n'.join(output)+'\n'


def static_cmdline(source):
    parts=source.split()
    if not any(p.startswith('androidboot.super_partition=') for p in parts):
        raise ValueError('Reference super partition cmdline missing')
    parts=[p for p in parts if not p.startswith(('androidboot.super_partition=',
               'androidboot.dynamic_partitions=','androidboot.dynamic_partitions_retrofit='))]
    parts+=['androidboot.dynamic_partitions=false','androidboot.dynamic_partitions_retrofit=false']
    return ' '.join(parts)


def static_vendor_properties(source):
    changes={'ro.boot.dynamic_partitions':'false','ro.boot.dynamic_partitions_retrofit':'false'}
    seen=set();rows=[]
    for row in source.splitlines():
        key=row.split('=',1)[0]
        if key in changes:row=key+'='+changes[key];seen.add(key)
        rows.append(row)
    if seen!=set(changes):raise ValueError('Reference dynamic properties missing')
    return '\n'.join(rows)+'\n'
