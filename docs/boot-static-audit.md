# wayne 静态启动与加密短阶段审计

时间：2026-10-09T18:54:20.493843-07:00（America/Los_Angeles）。从 `f3cb6fc` 继续，目标国行小米6X（wayne/SDM660）、原版静态分区。Miku UI与jasmine不是目标基线。历史产物来源如实保留，当前用户boot/vendor、GPT和userdata状态仍未知。

做了什么：检查Git与上轮记录，核对本地非Miku wayne参考boot、固定wayne配置以及既有静态实验boot/fstab/init/vold材料。全程只读审计原镜像，没有生成可刷包、修改userdata或编译内核。

发生了什么：发现 `static_cmdline()` 错误强制要求 `androidboot.super_partition`。非Miku wayne参考boot并无该参数，旧函数确实拒绝这个原生静态输入。修复为要求一个明确的 `androidboot.hardware=qcom` 声明，移除动态参数并统一false值；接受原生静态输入且重复执行不变。硬件声明只是转换输入校验，不能识别真实产品或证明way­ne兼容。原历史转换输出保持不变，未改动已有镜像。

正反例检查通过：4项新cmdline测试、4项已有历史转换回归；1项header测试包含7个拒绝样例（短header、缺失payload、不支持版本、异常page、second payload、recovery DTBO、异常header长度）。最小补丁在f3cb6fc独立worktree应用检查通过。

| 材料 | 审计结果 | 限制 |
| --- | --- | --- |
| 非Miku wayne参考boot | header0、4096页；cmdline无super；ramdisk有init但没有fstab.qcom | 旧4.4参考包，不能替代用户当前4.19 boot |
| 已保留静态实验boot | header1、4096页、header长度1648，second/recovery DTBO为0，无AVB footer；gzip ramdisk；SHA与原报告一致 | 历史第三方4.19来源，不是用户当前基线；bootloader接受性未知 |
| 既有fstab | system/vendor为物理by-name EROFS、first_stage_mount；无logical、rawdump或metadata挂载；data行逐项保留 | by-name别名实际可用性、EROFS内核支持和启动顺序仍需匹配当前设备 |
| init与vold | ramdisk init与既有供体摘要一致；vendor init通过mount_all读取vendor fstab；供体vold为core服务 | 运行时导入、SELinux、keymaster/TEE与新旧框架接口未知 |
| FBE/FDE | 固定wayne配置和既有实验data为fileencryption=ice；非Miku参考vendor使用encryptable=ice | 不擅自切换算法、强制加密标志或格式化data；参考差异不能证明当前解密方式 |
| metadata | 既有data无metadata_encryption/keydirectory悬空fstab引用；供体init仍创建metadata/vold、APEX、checkpoint相关路径 | 无独立metadata挂载时的持久性与服务行为未验证，不能靠mkdir就认定可用 |

现有boot构建器只支持其特定v1/4096输入，拒绝second、recovery DTBO和AVB footer，且静态目标要求显式静态模式。不能把这个工具约束当成wayne统一boot格式，更不能直接处理参考header0。6.6仍为独立编译实验，本轮没有把其DTB/内核打入boot。

容量仅引用已保存设备配置，未新增数字或推测实际GPT，保持原4.19和6.6报告及公开实验包。没有启动、解密或硬件验证。

下一步需要的只读真机证据（本轮没有执行这些命令）：

```sh
adb shell getprop ro.product.device
adb shell getprop ro.boot.hardware
adb shell getprop ro.boot.slot_suffix
adb shell getprop ro.boot.dynamic_partitions
adb shell getprop ro.crypto.state
adb shell getprop ro.crypto.type
adb shell cat /proc/cmdline
adb shell cat /proc/mounts
adb shell ls -l /dev/block/by-name /dev/block/bootdevice/by-name
adb shell cat /vendor/etc/fstab.qcom
adb shell logcat -b all -d -s vold fs_mgr init
```

若已具有root shell/Recovery，再只读检查实际物理节点容量（如 `blockdev --getsize64 /dev/block/bootdevice/by-name/boot`，system/vendor同理）、读取当前boot到主机检查header/ramdisk。先确认真实节点再读取，不能假设别名存在。不执行格式化、挂载改写、setprop或刷写，不导出加密密钥。采集输出可能含设备标识，分享前自行移除。

[审计证据与来源摘要](../research/boot-static-stage/audit.json)、[测试](../research/boot-static-stage/tests.json)、[最小配置补丁](../research/boot-static-stage/minimal-cmdline.patch)、[下一断点](../research/boot-static-stage/checkpoint.json)、[逐次带时间戳记录](operations/boot-static-audit-2026-10-09.md)。执行 `python3 tools/audit_static_boot_config.py` 可在现有本地材料上复现只读审计；定向测试为 `tools/test_static_boot_cmdline.py` 和 `tools/test_static_boot_header.py`。

本阶段保存后暂停。用户报告5小时95%、周46%，各保留约20%；工具无实时额度读取能力，不作精确剩余量声明。
