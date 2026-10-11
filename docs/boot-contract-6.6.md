# 6.6 boot镜像契约差距

时间：2026-10-11T06:58:20.665092-07:00；基线8b1a43a。仅国行wayne/SDM660原始静态分区，不以jasmine、动态分区或Miku UI为目标。

做了什么：读取最新断点、两个实际6.6构建入口、workflow和保留boot builder/报告；新增只读复核脚本tools/verify_6_6_boot_contract_stage.py，保存既有参考的哈希、头部、载荷文件位置、原始加载地址、cmdline、压缩前缀和footer观察。没有新打包入口或镜像，没有替换4.19/6.6成果。

发生了什么：最高优先缺口是实际当前wayne boot交付契约缺失。6.6只输出Image.gz与独立DTB，原builder只保留旧参考kernel载荷，不能自动接入6.6。没有发现6.6 mkbootimg/AVB打包调用，因此不虚构可接入preflight，也不为构建产物猜参数。现有DTB门禁继续阻断两个入口。

| 契约项 | 可证明的仓库材料 | 当前设备/6.6缺口 |
| --- | --- | --- |
| header/page | 非Miku wayne比较boot是v0/4096；历史静态实验是v1/4096；builder限制v1/4096 | 两者均非当前用户boot，不能据国行身份选择版本 |
| kernel/ramdisk/second/DTB | builder从参考boot提取kernel并原样保留，拒绝second和recovery DTBO；6.6输出分离Image.gz/DTB | 附加DTB、独立DTB或DTBO的实际交付及加载链未知，不能简单拼接 |
| base/offset | 原始头部可读取kernel/ramdisk/second/tags绝对地址；builder复制原头 | 绝对地址不能唯一反推mkbootimg base与各offset，未声明实际匹配 |
| cmdline | 静态入口使用static_cmdline删除super依赖并保留参考其余参数 | 实际当前cmdline、bootloader追加参数和6.6参数需求未知 |
| 压缩格式 | 6.6 make目标Image.gz；builder ramdisk明确gzip；参考前缀见断点JSON | 未验证实物bootloader接受的kernel/ramdisk格式；前缀不等于完整压缩解码 |
| 容量 | config/wayne-stock-static.json及旧builder使用64MiB boot限制，来源是设备配置 | 当前GPT容量未取得；不将配置声明当真机容量 |
| AVB/签名 | 旧builder仅拒绝尾部AVBf，没有6.6 avbtool或签名输入 | footer缺失不能证明无签名要求；vbmeta/解锁/rollback/信任链未知 |

集成点：.github/workflows/kernel-6.6-probe.yml → ci_kernel_66_probe.main/build；allocator-implementation.yml → ci_allocator_implementation.main及共用build。两者先执行现有板级门禁，只上传研究产物。保留的4.19静态链是ci_build_static.py → build_wayne_boot.py --layout stock-size-static → package_static_candidate.py；它不是6.6入口。旧ci_build_candidate.py调用builder不带静态参数会被当前目标要求拒绝，不能视为6.6通路。未修改这些入口、未重新打包。

可直接复核：

```sh
python3 tools/verify_6_6_boot_contract_stage.py
python3 tools/ci_kernel_66_probe.py --preflight
python3 tools/ci_allocator_implementation.py --preflight
```

复核复用三项门禁集成测试和一项boot头部拒绝测试，不编译、不打包；两个实际preflight预期2。五项保留材料哈希未变，详见[断点](../research/boot-contract-6.6-stage/checkpoint.json)。头部拒绝测试使用已有实验参考，非真实当前boot通过验证。

下一步只读采集命令（尚未执行；无权限须记录原始失败）：

```sh
adb shell 'cat /proc/cmdline; cat /proc/partitions; ls -l /dev/block/bootdevice/by-name' > wayne-boot-layout.txt
adb shell 'getprop ro.boot.verifiedbootstate; getprop ro.boot.vbmeta.device_state; getprop ro.boot.flash.locked; getprop ro.boot.avb_version' > wayne-boot-security-properties.txt
```

先通过实际节点清单确认boot路径和非A/B状态，再在具备只读权限的环境对确认路径执行blockdev --getsize64与完整boot读取；不写未知块设备。保存当前原件、采集来源/时间/实际命令与SHA256，再用Android工具只读解析header、完整载荷布局和AVB；不能从属性或footer单独推断签名策略。处于bootloader时可只读查询fastboot getvar product、fastboot getvar partition-size:boot和fastboot getvar unlocked，保存不支持返回；本轮不切换设备状态、不执行这些命令。

真实boot/容量/签名与真实wayne板级绑定齐全前，6.6继续阻断。SELinux、显示/GPU、相机、音频、加密、固件/remoteproc与启动等既有风险保留。不宣称可启动或硬件验证。实时额度无法读取，57%/87%仅为用户快照；保存同步后立即暂停。
