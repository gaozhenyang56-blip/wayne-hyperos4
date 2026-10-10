#!/usr/bin/env python3
"""Audit stored evidence without promoting defconfigs to hardware capability."""
import datetime
import hashlib
import json
import pathlib
from static_wayne_layout import static_fstab

ROOT=pathlib.Path(__file__).resolve().parent.parent
OUT=ROOT/'research/fbe-vold-stage'


def witness(path,tokens):
    data=path.read_bytes()
    return {'path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(data).hexdigest(),
            'lines':[{'line':i,'text':line} for i,line in enumerate(data.decode().splitlines(),1)
                     if any(token in line for token in tokens)]}


def main():
    OUT.mkdir(exist_ok=True)
    old=ROOT/'research/base-miku-a15'
    donor=ROOT/'research/candidates/mi8937-os4'
    source=(old/'ramdisk/fstab.qcom').read_text()
    converted=static_fstab(source)
    data_rows=[r.split() for r in converted.splitlines() if r.strip() and not r.startswith('#') and r.split()[1]=='/data']
    assert all('/metadata' not in r[4] for r in data_rows)
    config_meta=json.loads((old/'kernel-config.json').read_text())
    config_data=(old/'kernel.config').read_bytes()
    assert hashlib.sha256(config_data).hexdigest()==config_meta['config_sha256']
    assert config_meta['actual_build_configuration'] is False
    report66=ROOT/'artifacts/kernel-6.6-allocator-probe.json'
    kernel66=json.loads(report66.read_text())
    assert 'FS_ENCRYPTION' in kernel66['android_config_prerequisites_verified']
    config_tokens=['CONFIG_FS_ENCRYPTION','CONFIG_EXT4_ENCRYPTION','CONFIG_F2FS_FS_ENCRYPTION',
                   'CONFIG_CRYPTO_DEV_QCOM_ICE','CONFIG_BLK_INLINE_ENCRYPTION','CONFIG_DM_DEFAULT_KEY',
                   'CONFIG_EXT4_FS=','CONFIG_F2FS_FS=']
    inputs=[witness(old/'kernel.config',config_tokens),witness(old/'kernel-config.json',['actual_build','warning']),
            witness(ROOT/'config/kernel-6.6-android.fragment',config_tokens),
            witness(ROOT/'research/gpu-allocator-stage/kernel-uapi/sdm660_defconfig',config_tokens),
            witness(report66,['FS_ENCRYPTION','config','hardware_tested'])]
    for path in [old/'ramdisk/fstab.qcom',ROOT/'research/static-wayne/android_device_xiaomi_wayne-rootdir_etc_fstab.qcom',
                 ROOT/'research/gpu-allocator-stage/lineage-wayne/selected-vendor/etc/fstab.qcom']:
        inputs.append(witness(path,['/data','/metadata','fileencryption','encryptable','keydirectory']))
    inputs.extend([witness(donor/'system/system/etc/init/vold.rc',['service vold','--','class core','user root']),
                   witness(donor/'system/system/etc/init/hw/init.rc',['/metadata','checkpoint','start vold']),
                   witness(old/'vendor/etc/vintf/manifest.xml',['keymaster','IKeymasterDevice'])])
    report={'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'target':'China wayne/SDM660, original static layout; no jasmine or Miku baseline',
        'sources_role':'fixed wayne config + non-Miku reference + historical artifact inputs ONLY; not current user vendor',
        'inputs':inputs,'preserved_data_rows':data_rows,
        'kernel_419':{'source_kind':'embedded historical defconfig','actual_build_configuration':False,
                      'ice_config_declaration':'CONFIG_CRYPTO_DEV_QCOM_ICE=y','hardware_ice_verified':False},
        'kernel_66':{'fs_encryption_compile_prerequisite_verified':True,
                     'full_generated_config_available_locally':False,'ice_inline_crypto_dm_default_key_verified':False,
                     'fstab_ice_parsing_verified':False,'hardware_ice_verified':False},
        'metadata':{'fstab_keydirectory_dependency_present':False,'data_metadata_encryption_flag_present':False,
                    'donor_init_metadata_paths_present':True,'persistent_storage_verified':False},
        'vold':{'rc_arguments_are_security_contexts_not_cipher_selection':True,
                'matching_vold_fs_mgr_source_available':False,'keymaster_tee_integration_verified':False},
        'fix':'refuse explicit keydirectory rooted at /metadata when static conversion removes that mount; do not rewrite key paths',
        'remaining':['current userdata FDE/FBE mode and fscrypt policy','matched vold/fs_mgr legacy ice parser',
                     'actual 4.19 build config and full 6.6 crypto configuration','persistent metadata/APEX/checkpoint design',
                     'current keymaster/TEE, ICE device-tree/runtime evidence and SELinux'],
        'configuration_consistency_verified':False,'decryption_verified':False,
        'hardware_tested':False,'bootable_verified':False,'new_image_created':False}
    (OUT/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Stored crypto evidence audited; ICE/decryption and current vendor consistency remain unverified.')


if __name__=='__main__':main()
