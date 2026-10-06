# 小米 6X（wayne）HyperOS 4 移植调查工程

状态：**移植未完成，未生成卡刷包或线刷包。** 已实际获取并分析下述镜像，不将供体原包或仅修改版本号的文件称为移植 ROM。用户指定 4.19 内核、不进行真机测试；本工程按这个约束调查。

## 当前供体选择

| 候选 | 硬件／内核 | 核验状态 | 用途 |
| --- | --- | --- | --- |
| Redmi Note 11 spes | Snapdragon 680；包内 boot 确认 4.19.325 | OS4／Android 17 为发布者声明，system 待核验；OTA metadata 沿用 Android 13 | 首选候选 |
| Mi8937（santoni/ugg/land） | Snapdragon 430/435 等；包内 boot 确认 4.19.325 | 完整 ZIP CRC 检查通过；内部系统版本待核验 | 旧平台补丁参考及备选 |
| Redmi Note 12 4G tapas/topaz | Snapdragon 685；官方内核源码 5.15 | 找到 OS4 社区包链接 | 次级候选 |
| Redmi Note 7 lavender | Snapdragon 660，与 6X 同 SoC | 本次未找到可核验的 OS4 包 | 有来源再评估 |

详见 [供体比较](docs/donors.md) 与 [操作记录](docs/worklog.md)。供体 boot、vendor、固件不能直接刷入 6X。

## 已取得的材料

| 材料 | 实际核验 | 本地位置 |
| --- | --- | --- |
| 小米 15 `OS4.0.0.8.XOCCNXM` 原包 | 官方 CDN 实际响应；Android 17、SDK 37；payload 元数据哈希及分区操作/完整分区 SHA-256 | `research/donor-dada-os4/` |
| HyperOS 4 `system.img`、`system_ext.img`、`init_boot.img` | 分区大小和 SHA-256 与 payload 清单一致；system、system_ext 的 EROFS 检查及解包成功 | 同上 |
| wayne Miku UI Android 15 底包 | OTA 中 `pre-device=wayne`，SDK 35，BLOCK OTA，retrofit 动态分区 | `research/base-miku-a15/` |
| 底包 boot.img、vendor 数据 | ZIP 条目 CRC 核验；vendor 由完整 block OTA 重建并通过 EROFS 检查 | 同上 |
| 底包内核 | 从 boot 内核二进制解压得到 `4.19.315-Miku-Vampire_v2-g3a74d7` | `research/base-miku-a15/kernel-version.txt` |
| 6X 原厂 MIUI 12 Android 9 | 原包目录、OTA 元数据、安装脚本已核验；仅作为固件来源参考，未作为 Android 17 的 vendor 底包 | `research/stock-wayne/` |
| wayne 设备树、内核配置、vendor 构建文件 | 固定提交；内核源码与 vendor 为部分检出 | `sources/`、`sources.lock.json` |

小米 15 和 wayne 底包使用 HTTP Range 获取所需条目和 payload 分区，没有下载这两个完整 ZIP。其他候选包获取状态见日志。未验证整包 SHA-256 或小米 OTA 签名。内核 4.19.315 是所下载参考底包的版本，不代表已取得用户手机当前内核的配置或二进制。

## 为什么先分析小米 15

该包是查到且能够实际获取的高通 HyperOS 4 完整 OTA；其系统分区用于检查框架和运行库。选择它不意味着其 SoC、驱动、启动镜像与 6X 兼容。后续依照用户要求检索更接近的设备，现改以 Redmi Note 11（spes）的 4.19 社区移植包为首选候选，小米 15 留作官方框架对照。

查询的公开 ROM 数据库在此次查询中没有返回 Android 16 版 HyperOS 4；搜索到的小米 13 `OS4.*.PRE` 信息是 Android 17 内部测试记录，没有据此取得可用原包。此结论仅覆盖本次检索，不能证明所有渠道都没有其他包。

## 静态检查发现的问题

1. **FCM 不匹配。** 已解出的 wayne vendor manifest 声明 `target-level=5`。供体 system 包含 7、8、202404、202504、202604 矩阵，缺少 5。现有等级 7 的内核条目是 5.10.107/5.15.41。不能直接将 vendor 等级改成 7 并宣称兼容；需要恢复旧接口支持、逐项核对 HAL 和内核要求。
2. **启动布局不同。** 参考 boot 为 header v1，内核及 ramdisk 同处 boot；供体 init_boot 为 header v4，并有独立 vendor_boot。供体 boot 分区镜像 96 MiB，而参考设备树的 boot 上限是 64 MiB。需要以 6X 内核、DTB、cmdline、挂载布局重新构建启动镜像。
3. **未裁剪组合超过参考分区组。** 供体 system、system_ext、product、mi_ext 加参考 vendor 共 6,514,757,632 字节，参考底包组上限 6,241,120,256 字节，超出 273,637,376 字节（约 261 MiB）。这只是镜像大小比较，未计重打包变化、额外分区和必要余量；真实手机分区几何未验证。需要裁剪并重新生成镜像及 logical 分区布局。
4. **旧 HAL 的运行时兼容未验证。** 已检查相机和显示 HAL 的 DT_NEEDED；直接依赖库文件在当前 vendor/system/system_ext 组合中能找到。尚未验证导出符号和 linker namespace，因此不能宣称相机或显示能工作。
5. **SELinux 仅完成映射存在性检查。** 参考 vendor policy 为 202404，供体包含对应 mapping。组合策略未编译，其他厂商扩展域、init 服务、APEX、BPF、加密兼容尚未解决。

以上否定的是未经适配的直接替换方案，**不构成“4.19 必然不能移植 HyperOS 4”的证明**。当前不足以交付完成的实验刷机包。

## 实際方案与下一步工作

目标路线是以 wayne 4.19 + retrofit 动态分区底包的内核、vendor、fstab、设备 init 配置为基础，适配 HyperOS 4 系统框架。需要先完成 FCM/旧 HIDL 兼容层及 linker/SELinux 检查，再构建 boot 和适配后的 system/system_ext/product/mi_ext。保留 6X 自身硬件固件；供体 bootloader、modem、tz 等不是这个移植方案的可用部件。

公开的一键移植工具不能直接处理这一组合。`toraidl/hyperos_port` 文档面向 Android 13 底包移植 Android 14；`luxured-duchamp/hosport` 文档面向 Android 15 底包、Android 16 HyperOS 3，并声明 5.10+ GKI 平台支持。本次只参考其流程，没有执行其打包脚本或据此宣称支持 6X。

## 可复现操作

Python 3.11+；`pip install -r requirements.txt`。HTTP 检查、payload 提取、block OTA 转换与 boot 检查脚本不调用 fastboot/adb、不操作手机分区。

```bash
python3 tools/inspect_ota.py 'https://cdnorg.d.miui.com/OS4.0.0.8.XOCCNXM/dada-ota_full-OS4.0.0.8.XOCCNXM-user-17.0-f6a0447d15.zip' research/donor-dada-os4
python3 tools/extract_payload_partition.py research/donor-dada-os4 system research/donor-dada-os4/system.img
python3 tools/extract_payload_partition.py research/donor-dada-os4 system_ext research/donor-dada-os4/system_ext.img
python3 tools/extract_payload_partition.py research/donor-dada-os4 init_boot research/donor-dada-os4/init_boot.img
python3 tools/inspect_ota.py 'https://downloads.sourceforge.net/project/divarelease/wayne_Vampire_v0.6.0/MikuUI-Vampire_v2-wayne-25020901-OFFICIAL.zip' research/base-miku-a15 --extract-entry boot.img --extract-entry vendor.new.dat.br --extract-entry vendor.transfer.list
python3 tools/convert_block_ota.py research/base-miku-a15/vendor.new.dat.br research/base-miku-a15/vendor.transfer.list 209600512 research/base-miku-a15/vendor.img
python3 tools/unpack_boot.py research/base-miku-a15/boot.img research/base-miku-a15
python3 tools/unpack_boot.py research/donor-dada-os4/init_boot.img research/donor-dada-os4
```

用 `fsck.erofs --extract=<目录> <镜像>` 分别解出 system、system_ext、vendor。环境里使用 Debian erofs-utils 1.8.6，位于 `tools/local/usr/bin/`，下载包保留在同目录；只解出用户空间工具，没有安装系统包。随后运行 `python3 tools/audit_pair.py` 重新计算 `audit.json`。

公开仓库保存脚本、来源记录、检查报告和操作日志。大型镜像与解包目录不提交到 Git；最终产物通过 Releases 或分卷资产发布，并在 `artifacts/` 记录大小、SHA-256、构建提交和验证范围。当前没有最终 ROM，也没有已发布的研究备份包。

## 来源

- [HyperOS 官方页面](https://hyperos.mi.com/)
- [供体下载索引](https://miuirom.org/updates/hyperos-4)（使用其中链接取得 CDN 内实际元数据，技术结论以下载数据为准）
- [公开 ROM 数据库](https://roms.xiaomi-miui.gr/)
- [Miku UI 发布者的 wayne 动态分区说明](https://github.com/Diva-Room/DivaRelease/blob/wayne_nndp/README.md)
- [Miku UI wayne Android 15 发布文件](https://sourceforge.net/projects/divarelease/files/wayne_Vampire_v0.6.0/)
- [wayne 设备树](https://github.com/Diva-Room/Miku_device_xiaomi_wayne/tree/Vampire_v2)
- [wayne 内核](https://github.com/Diva-Room/Miku_kernel_xiaomi_wayne/tree/Vampire_v2)
- [wayne vendor 构建文件](https://github.com/Diva-Room/Miku_vendor_xiaomi_wayne/tree/Vampire_v2)
- [Android VINTF 匹配规则](https://source.android.com/docs/core/architecture/vintf/match-rules)
- [早期 HyperOS 移植工程](https://github.com/toraidl/hyperos_port)
- [HyperOS 3 Android 16 移植工程](https://github.com/luxured-duchamp/hosport)
