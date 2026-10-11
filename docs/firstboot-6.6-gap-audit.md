# wayne独立6.6首启差距短审计

时间：2026-10-11T03:18:53.972629-07:00；基线bb6dba9。目标国行小米6X（wayne/SDM660），原始静态分区；4.19保留，6.6为独立实验。jasmine、动态分区或Miku UI不是目标基线。

做了什么：检查工作区、diff与最近结果，核对既有6.6构建/源DT、静态boot报告、vendor ABI和固件交付记录。选择“真实wayne板级DT未适配”作为当前首启准备最高优先阻塞项，补齐直接jasmine继承拒绝及源DTS/已编DTB/真实参考来源记录的哈希绑定检查，不修改DTS/配置或打包。

发生了什么：两项正反例通过，当前实验按预期退出2：config/sdm660-xiaomi-wayne-6.6.dts直接include sdm660-xiaomi-jasmine.dts，仅改model/compatible；构建报告明确board_identity_validation_scope只到compatible标签且继承细节未核实。把板名改成wayne和compiled=true不能证明板级配置。正例使用模拟原生DTS和哈希关联记录，只通过来源门禁，不证明DT语义、板级硬件或启动。检查仅识别直接jasmine include，不递归解析完整DTS/DTB；引用哈希声明仍须核对实际参考文件，不能替代真实证据。

| 首启差距 | 现有证据与下一门槛 |
| --- | --- |
| 板级DT（本轮优先） | 现有49,676字节DTB仅编译成功，compatible不能证明供电、时钟、PMIC、存储、reserved-memory或remoteproc等绑定。需真实国行DTB及来源，对照完整include闭包；不猜寄存器、中断或地址 |
| arm64配置 | 6.6固定源6a4e475、arm64 sdm660_defconfig及Android fragment，报告记录生成.config哈希和必要选项；并非当前设备验证。历史4.19为嵌入perf defconfig，不是实际生成.config或用户当前ROM基线，不能直接当完整对照配置 |
| 静态boot链 | 前阶段已核对static_cmdline/fstab和拒绝异常header，保留成果。本地非Miku参考boot是header0，历史实验boot是header1；两者都不是用户当前boot参数，不据此选目标header。GPT真实容量、地址/page、DTB/DTBO交付、ramdisk/init、签名/AVB与bootloader约束仍需当前材料；不直接把Image.gz和独立DTB塞进旧boot |
| vendor ABI | 6.6报告KGSL/ION/MSM-FB均未提供，当前用户vendor未知；参考旧图形包已被拒绝。受限system-heap适配器不补足旧ABI。早期SELinux、FBE/vold/ICE及显示/相机/音频等风险保留，不能用编译通过代替vendor兼容 |
| 固件/remoteproc | modules_built=false、早期模块/固件交付未集成，不等于内建驱动不存在；需真实DT、remoteproc/subsystem启动、固件清单与挂载/ramdisk加载链路。不能套用jasmine固件或reserved-memory布局 |

[审计结果](../research/firstboot-6.6-stage/audit.json)记录直接继承和拒绝原因；[断点](../research/firstboot-6.6-stage/checkpoint.json)保存两项测试和八项原有文件未变哈希。[时间戳日志](operations/firstboot-6.6-2026-10-11.md)保存原始结果。复现`python3 tools/verify_6_6_firstboot_stage.py`；单独`python3 tools/audit_6_6_firstboot.py`对当前实验预期退出2。本轮为独立离线门禁，尚未接入构建/打包流程，不宣称现有工具已自动阻止所有打包路径。

下一断点：先取得真实当前国行wayne DTB、分区/boot参数及vendor来源，再做板级差异表；有确切来源与绑定证据后才小范围修订独立6.6 DTS。先完成板级证据门禁，再评估boot打包；其余阻塞并未解除。

以下只读采集命令尚未执行，无权限/不存在应保留原始错误，不猜容量或boot块设备：

```sh
adb shell getprop > wayne-current-properties.txt
adb shell 'cat /proc/cmdline; cat /proc/partitions; find /dev/block -type l' > wayne-static-boot-layout.txt
adb shell 'zcat /proc/config.gz; cat /proc/modules' > wayne-current-kernel-config.txt
adb pull /sys/firmware/fdt wayne-current-fdt.dtb
adb shell 'ls -l /sys/class/remoteproc; find /vendor /odm -type f' > wayne-firmware-vendor-inventory.txt
adb shell 'mount; ls -lZ /dev/block /sys/class/block' > wayne-mount-block-evidence.txt
adb shell dmesg > wayne-current-boot-kernel.txt
adb shell logcat -b all -d > wayne-current-boot-logcat.txt
```

根据实际分区链接和权限在现有可读恢复环境取得当前boot镜像、GPT清单及vendor/init/fstab/固件交付材料，保存SHA256与来源；使用现有unpack_boot工具只读解析header/page/地址/ramdisk/DTB/DTBO/签名，不指定未经证实的块设备。FDT也可能不含全部overlay应用信息，需实际boot/DTBO与live设备树对应。以上均未采集或执行，不刷写、不重启测试、不请求远端长编译。

4.19方案、6.6实验和既有静态实验包保留；未覆盖、回退、改分区、下载大源码/供体、重编或生成刷机包。无真机测试，不宣称可启动或硬件验证；编译/静态检查只作为离线证据。实时额度不可读取，89%/93%仅为用户快照，不声称精确控制。本轮同步后立即暂停。
